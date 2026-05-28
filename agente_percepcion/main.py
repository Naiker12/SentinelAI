from __future__ import annotations

import queue
import threading
import time
from dataclasses import replace
from pathlib import Path

import cv2

from agente_analisis.risk_engine import analyze_event
from agente_percepcion.camera import Camera
from agente_percepcion.config import get_settings
from agente_percepcion.detector import YoloDetector, draw_detections
from agente_percepcion.events import (
    DetectionEvent,
    N8nClient,
    SupabaseEventStore,
    SupabaseEvidenceStore,
    SupabaseHumanReviewStore,
    risk_for_label,
)
from agente_percepcion.memory import EventMemory, should_emit_detection
from agente_percepcion.telegram import TelegramSupervisorClient, mark_telegram_evidence
from agente_percepcion.tracking import MotionTracker


def run() -> None:
    settings = get_settings()
    print(f"Configuracion cargada desde: {settings.env_file}")
    print(f"Webhook n8n: {settings.n8n_webhook_url or 'NO CONFIGURADO'}")
    if settings.n8n_webhook_url and "/webhook-test/" in settings.n8n_webhook_url:
        print(
            "ADVERTENCIA: la camara esta apuntando a /webhook-test/. "
            "Usa /webhook/ con el workflow activo, o define "
            "SENTINEL_ALLOW_N8N_TEST_WEBHOOK=true solo para pruebas manuales."
        )
    if settings.telegram_callback_polling:
        print(
            "Callbacks Telegram por polling Python activos. "
            "Si n8n Telegram Trigger esta activo con el mismo bot, Telegram bloqueara getUpdates."
        )
    detector = YoloDetector(
        settings.model_path,
        settings.confidence,
        settings.classes,
        dangerous_confidence=settings.dangerous_confidence,
        inference_confidence=settings.inference_confidence,
        debug_detections=settings.debug_detections,
        debug_confidence=settings.debug_confidence,
        debug_print_interval_seconds=settings.debug_print_interval_seconds,
        show_filtered_detections=settings.show_filtered_detections,
        debug_filtered_classes=settings.debug_filtered_classes,
        use_model_tracking=settings.yolo_tracking,
        tracker=settings.yolo_tracker,
    )
    store = SupabaseEventStore(
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.supabase_detection_events_table,
    )
    evidence_store = SupabaseEvidenceStore(
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.supabase_storage_bucket,
    )
    human_review_store = SupabaseHumanReviewStore(
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.supabase_human_reviews_table,
    )
    n8n = N8nClient(
        settings.n8n_webhook_url,
        allow_test_webhook=settings.allow_n8n_test_webhook,
    )
    telegram = TelegramSupervisorClient(settings.telegram_bot_token, settings.telegram_chat_id)
    memory = EventMemory()
    motion_tracker = MotionTracker(max_lost_seconds=settings.danger_hold_seconds + 1)
    memory_lock = threading.Lock()
    last_event_at: dict[str, float] = {}
    last_danger: tuple[float, Detection] | None = None
    event_queue: queue.Queue[tuple[DetectionEvent, float] | None] = queue.Queue(
        maxsize=max(1, settings.event_queue_maxsize)
    )
    worker = threading.Thread(
        target=_event_worker,
        args=(
            settings,
            evidence_store,
            telegram,
            n8n,
            store,
            human_review_store,
            memory,
            memory_lock,
            event_queue,
        ),
        daemon=True,
    )
    worker.start()
    stop_telegram_callbacks = threading.Event()
    telegram_callback_worker = None
    if settings.telegram_callback_polling:
        telegram_callback_worker = threading.Thread(
            target=telegram.poll_supervisor_callbacks,
            args=(stop_telegram_callbacks,),
            daemon=True,
        )
        telegram_callback_worker.start()

    if settings.save_images:
        settings.image_dir.mkdir(parents=True, exist_ok=True)

    with Camera(
        settings.camera_index,
        backend=settings.camera_backend,
        width=settings.camera_width,
        height=settings.camera_height,
        fps=settings.camera_fps,
        fourcc=settings.camera_fourcc,
        drop_stale_frames=settings.camera_drop_stale_frames,
    ) as camera:
        while True:
            frame = camera.read()
            now = time.monotonic()
            detections = detector.detect(frame)
            detections = motion_tracker.update(detections, now)
            accepted_detections = _accepted_detections(detections)
            filtered_detections = _filtered_detections(detections)
            accepted_detections, last_danger = _stabilize_danger_detections(
                accepted_detections,
                last_danger,
                now,
                settings.danger_hold_seconds,
            )
            annotated_frame = draw_detections(frame.copy(), [*accepted_detections, *filtered_detections])
            for review_id in telegram.consume_review_snapshot_requests():
                image_path = _save_frame(settings.image_dir, annotated_frame)
                _send_review_snapshot_async(telegram, review_id, image_path)
            for decision in telegram.consume_review_decisions():
                _record_human_review_decision_async(human_review_store, decision)

            for detection in accepted_detections:
                if not _is_alertable_detection(detection.label):
                    continue
                cooldown = _cooldown_for_detection(settings, detection.label)
                if not should_emit_detection(
                    detection.label,
                    settings.camera_name,
                    last_event_at,
                    now,
                    cooldown,
                    detection.box,
                ):
                    continue

                image_path = _save_frame(settings.image_dir, annotated_frame)
                with memory_lock:
                    memory_snapshot = memory.snapshot(now)
                event = DetectionEvent.from_detection(
                    detection,
                    camera_name=settings.camera_name,
                    image_path=image_path,
                    contexto={
                        "zona": settings.scene_zone,
                        "iluminacion": settings.scene_lighting,
                        "cantidad_personas": sum(
                            1 for item in accepted_detections if item.label == "persona"
                        ),
                    },
                    tracking=detection.tracking,
                    memoria=memory_snapshot,
                )
                _enqueue_event(event_queue, event, now)

            cv2.imshow("SentinelAI - AgentePercepcion", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    _stop_event_worker(event_queue)
    worker.join(timeout=10)
    stop_telegram_callbacks.set()
    if telegram_callback_worker:
        telegram_callback_worker.join(timeout=5)
    cv2.destroyAllWindows()


def _event_worker(
    settings,
    evidence_store: SupabaseEvidenceStore,
    telegram: TelegramSupervisorClient,
    n8n: N8nClient,
    store: SupabaseEventStore,
    human_review_store: SupabaseHumanReviewStore,
    memory: EventMemory,
    memory_lock: threading.Lock,
    event_queue: queue.Queue[tuple[DetectionEvent, float] | None],
) -> None:
    while True:
        item = event_queue.get()
        if item is None:
            event_queue.task_done()
            break

        event, detected_monotonic = item
        try:
            event = _with_historical_knn_samples(event, store)
            analysis = analyze_event(event.to_analysis_request())
            event = _upload_evidence(settings, evidence_store, event)
            event = event.with_analysis(analysis)
            _send_to_telegram(settings, telegram, event)
            n8n_result = _send_to_n8n(n8n, event)
            detection_event_row = store.save(event, n8n_result.response or event.analisis)
            _record_pending_human_review(human_review_store, event, detection_event_row)
            with memory_lock:
                memory.remember(detected_monotonic, analysis.result.risk_level)
            _print_event_summary(event)
        except Exception as exc:
            print(f"No se pudo procesar evento en segundo plano: {exc}")
        finally:
            event_queue.task_done()


def _enqueue_event(
    event_queue: queue.Queue[tuple[DetectionEvent, float] | None],
    event: DetectionEvent,
    detected_monotonic: float,
) -> None:
    try:
        event_queue.put_nowait((event, detected_monotonic))
    except queue.Full:
        print(
            "Cola de eventos llena: se descarto una evidencia para mantener la camara fluida. "
            "Sube SENTINEL_EVENT_QUEUE_MAXSIZE o revisa n8n/Supabase si pasa seguido."
        )


def _stop_event_worker(event_queue: queue.Queue[tuple[DetectionEvent, float] | None]) -> None:
    while True:
        try:
            event_queue.put_nowait(None)
            return
        except queue.Full:
            try:
                event_queue.get_nowait()
                event_queue.task_done()
            except queue.Empty:
                continue


def _send_review_snapshot_async(
    telegram: TelegramSupervisorClient,
    review_id: str,
    image_path: str,
) -> None:
    def send() -> None:
        result = telegram.send_review_snapshot(review_id, image_path)
        if result.sent:
            print(f"Telegram recibio captura adicional para revision: {review_id}")
        else:
            print(f"No se pudo enviar captura adicional: {result.error}")

    threading.Thread(target=send, daemon=True).start()


def _record_human_review_decision_async(
    human_review_store: SupabaseHumanReviewStore,
    decision: dict,
) -> None:
    def save() -> None:
        try:
            human_review_store.record_decision(decision)
            print(
                "Revision humana guardada: "
                f"{decision.get('review_id')} -> {decision.get('estado_revision')}"
            )
        except Exception as exc:
            print(f"No se pudo guardar decision humana: {exc}")

    threading.Thread(target=save, daemon=True).start()


def _cooldown_for_detection(settings, label: str) -> float:
    if _is_alertable_detection(label):
        return settings.dangerous_event_cooldown_seconds
    return settings.event_cooldown_seconds


def _is_alertable_detection(label: str) -> bool:
    return risk_for_label(label) in {"alto", "medio"}


def _accepted_detections(detections: list[Detection]) -> list[Detection]:
    return [detection for detection in detections if not detection.filtered_reason]


def _filtered_detections(detections: list[Detection]) -> list[Detection]:
    return [detection for detection in detections if detection.filtered_reason]


def _stabilize_danger_detections(
    detections: list[Detection],
    last_danger: tuple[float, Detection] | None,
    now: float,
    hold_seconds: float,
) -> tuple[list[Detection], tuple[float, Detection] | None]:
    dangerous = [item for item in detections if risk_for_label(item.label) == "alto"]
    if dangerous:
        strongest = max(dangerous, key=lambda item: item.confidence)
        return detections, (now, strongest)

    if last_danger is None:
        return detections, None

    last_seen, detection = last_danger
    if now - last_seen <= hold_seconds:
        ghost = replace(detection, confidence=max(0.01, round(detection.confidence * 0.9, 4)))
        return [*detections, ghost], last_danger

    return detections, None


def _save_frame(image_dir: Path, frame) -> str:
    image_dir.mkdir(parents=True, exist_ok=True)
    path = image_dir / f"evento_{time.time_ns()}.jpg"
    cv2.imwrite(str(path), frame)
    return str(path)


def _send_to_n8n(n8n: N8nClient, event: DetectionEvent):
    result = n8n.send(event)
    if not result.sent:
        print(f"n8n no recibio el evento: {result.error}")
        return result

    print(f"n8n respondio ({result.status_code}): {result.response}")
    return result


def _with_historical_knn_samples(
    event: DetectionEvent,
    store: SupabaseEventStore,
) -> DetectionEvent:
    memory_snapshot = dict(event.memoria or {})
    memory_snapshot["knn_samples"] = _historical_knn_samples(store)
    return replace(event, memoria=memory_snapshot)


def _print_event_summary(event: DetectionEvent) -> None:
    analysis = event.analisis or {}
    result = analysis.get("resultado", {})
    decision = analysis.get("decision", {})
    print(
        "Evento procesado: "
        f"{event.camara} {event.objeto} conf={event.confianza:.3f} "
        f"riesgo={result.get('nivel_riesgo', event.riesgo)} "
        f"score={result.get('score_riesgo', '-')} "
        f"revision={decision.get('estado_revision_humana', '-')}"
    )


def _record_pending_human_review(
    human_review_store: SupabaseHumanReviewStore,
    event: DetectionEvent,
    detection_event_row: dict | None,
) -> None:
    try:
        row = human_review_store.record_pending(event, detection_event_row)
    except Exception as exc:
        print(f"No se pudo registrar revision humana pendiente: {exc}")
        return
    if row:
        print(f"Revision humana pendiente guardada: {row.get('review_id')}")


def _upload_evidence(
    settings,
    evidence_store: SupabaseEvidenceStore,
    event: DetectionEvent,
) -> DetectionEvent:
    if not settings.upload_evidence or not event.imagen:
        return event

    image_path = Path(event.imagen)
    if not image_path.exists():
        return event

    try:
        image_url = evidence_store.upload_image(image_path, event)
        return replace(event, imagen=image_url)
    except Exception as exc:
        print(f"No se pudo subir evidencia a Supabase Storage: {exc}")
        return event


def _send_to_telegram(settings, telegram: TelegramSupervisorClient, event: DetectionEvent) -> None:
    if not settings.telegram_direct_alerts:
        return
    if not event.analisis:
        return
    decision = event.analisis.get("decision", {})
    if not decision.get("requiere_revision_humana"):
        return

    result = telegram.send_validation(event)
    mark_telegram_evidence(event, result.sent, result.error)
    if result.sent:
        print("Telegram recibio evidencia visual para revision humana.")
    else:
        print(f"Telegram no recibio evidencia visual: {result.error}")


def _historical_knn_samples(store: SupabaseEventStore, limit: int = 80) -> list[dict]:
    try:
        rows = store.latest(limit=limit)
    except Exception as exc:
        print(f"No se pudo consultar historial real para KNN: {exc}")
        return []

    samples = []
    for row in rows:
        score = row.get("score_riesgo")
        if score is None:
            level = str(row.get("nivel_riesgo") or row.get("riesgo") or "").upper()
            score = {"CRITICO": 0.95, "ALTO": 0.75, "MEDIO": 0.45, "BAJO": 0.1}.get(level)
        if score is None:
            continue
        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            continue
        context = row.get("contexto") if isinstance(row.get("contexto"), dict) else {}
        samples.append(
            {
                "objeto": row.get("objeto"),
                "confianza": row.get("confianza"),
                "hora": row.get("detected_at"),
                "contexto": context,
                "tracking": context.get("tracking") if isinstance(context.get("tracking"), dict) else {},
                "memoria": context.get("memoria") if isinstance(context.get("memoria"), dict) else {},
                "score": round(numeric_score * 100) if numeric_score <= 1 else round(numeric_score),
            }
        )
    return samples


if __name__ == "__main__":
    run()
