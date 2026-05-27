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
    risk_for_label,
)
from agente_percepcion.memory import EventMemory, should_emit_detection
from agente_percepcion.telegram import TelegramSupervisorClient, mark_telegram_evidence
from agente_percepcion.tracking import MotionTracker


def run() -> None:
    settings = get_settings()
    print(f"Configuracion cargada desde: {settings.env_file}")
    print(f"Webhook n8n: {settings.n8n_webhook_url or 'NO CONFIGURADO'}")
    detector = YoloDetector(
        settings.model_path,
        settings.confidence,
        settings.classes,
        debug_detections=settings.debug_detections,
        debug_confidence=settings.debug_confidence,
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
    event_queue: queue.Queue[tuple[DetectionEvent, object, float] | None] = queue.Queue()
    worker = threading.Thread(
        target=_event_worker,
        args=(settings, evidence_store, telegram, n8n, store, memory, memory_lock, event_queue),
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
    ) as camera:
        while True:
            frame = camera.read()
            now = time.monotonic()
            detections = detector.detect(frame)
            detections = motion_tracker.update(detections, now)
            detections, last_danger = _stabilize_danger_detections(
                detections,
                last_danger,
                now,
                settings.danger_hold_seconds,
            )
            annotated_frame = draw_detections(frame.copy(), detections)
            for review_id in telegram.consume_review_snapshot_requests():
                image_path = _save_frame(settings.image_dir, annotated_frame)
                result = telegram.send_review_snapshot(review_id, image_path)
                if result.sent:
                    print(f"Telegram recibio captura adicional para revision: {review_id}")
                else:
                    print(f"No se pudo enviar captura adicional: {result.error}")

            for detection in detections:
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

                image_path = (
                    _save_frame(settings.image_dir, annotated_frame)
                    if settings.save_images or risk_for_label(detection.label) == "alto"
                    else None
                )
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
                            1 for item in detections if item.label == "persona"
                        ),
                    },
                    tracking=detection.tracking,
                    memoria=memory_snapshot,
                )
                analysis = analyze_event(event.to_analysis_request())
                if analysis.decision.requires_human_review and not event.imagen:
                    event = replace(event, imagen=_save_frame(settings.image_dir, annotated_frame))
                event_queue.put((event, analysis, now))

            cv2.imshow("SentinelAI - AgentePercepcion", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    event_queue.put(None)
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
    memory: EventMemory,
    memory_lock: threading.Lock,
    event_queue: queue.Queue[tuple[DetectionEvent, object, float] | None],
) -> None:
    while True:
        item = event_queue.get()
        if item is None:
            event_queue.task_done()
            break

        event, analysis, detected_monotonic = item
        try:
            event = _upload_evidence(settings, evidence_store, event)
            event = event.with_analysis(analysis)
            _send_to_telegram(settings, telegram, event)
            n8n_result = _send_to_n8n(n8n, event)
            store.save(event, n8n_result.response or event.analisis)
            with memory_lock:
                memory.remember(detected_monotonic, analysis.result.risk_level)
            print(event.to_payload())
        except Exception as exc:
            print(f"No se pudo procesar evento en segundo plano: {exc}")
        finally:
            event_queue.task_done()


def _cooldown_for_detection(settings, label: str) -> float:
    if _is_alertable_detection(label):
        return settings.dangerous_event_cooldown_seconds
    return settings.event_cooldown_seconds


def _is_alertable_detection(label: str) -> bool:
    return risk_for_label(label) == "alto"


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


if __name__ == "__main__":
    run()
