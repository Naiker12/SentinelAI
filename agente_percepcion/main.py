from __future__ import annotations

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
)
from agente_percepcion.memory import EventMemory, should_emit_detection
from agente_percepcion.telegram import TelegramSupervisorClient, mark_telegram_evidence


def run() -> None:
    settings = get_settings()
    print(f"Configuracion cargada desde: {settings.env_file}")
    print(f"Webhook n8n: {settings.n8n_webhook_url or 'NO CONFIGURADO'}")
    detector = YoloDetector(settings.model_path, settings.confidence, settings.classes)
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
    last_event_at: dict[str, float] = {}

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
            detections = detector.detect(frame)
            annotated_frame = draw_detections(frame.copy(), detections)
            now = time.monotonic()

            for detection in detections:
                if not should_emit_detection(
                    detection.label,
                    settings.camera_name,
                    last_event_at,
                    now,
                    settings.event_cooldown_seconds,
                    detection.box,
                ):
                    continue

                image_path = (
                    _save_frame(settings.image_dir, annotated_frame)
                    if settings.save_images
                    else None
                )
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
                    tracking=None,
                    memoria=memory_snapshot,
                )
                analysis = analyze_event(event.to_analysis_request())
                if analysis.decision.requires_human_review and not event.imagen:
                    event = replace(event, imagen=_save_frame(settings.image_dir, annotated_frame))
                    analysis = analyze_event(event.to_analysis_request())
                event = _upload_evidence(settings, evidence_store, event)
                event = event.with_analysis(analysis)
                _send_to_telegram(settings, telegram, event)
                n8n_result = _send_to_n8n(n8n, event)
                store.save(event, n8n_result.response or event.analisis)
                memory.remember(now, analysis.result.risk_level)
                print(event.to_payload())

            cv2.imshow("SentinelAI - AgentePercepcion", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


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
