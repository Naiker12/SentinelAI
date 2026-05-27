from __future__ import annotations

import time
from pathlib import Path

import cv2

from agente_analisis.risk_engine import analyze_event
from agente_percepcion.camera import Camera
from agente_percepcion.config import get_settings
from agente_percepcion.detector import YoloDetector, draw_detections
from agente_percepcion.events import DetectionEvent, N8nClient, SupabaseEventStore
from agente_percepcion.memory import EventMemory, should_emit_detection


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
    n8n = N8nClient(settings.n8n_webhook_url)
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
            now = time.monotonic()

            for detection in detections:
                if not should_emit_detection(
                    detection.label,
                    settings.camera_name,
                    last_event_at,
                    now,
                    settings.event_cooldown_seconds,
                ):
                    continue

                image_path = _save_frame(settings.image_dir, frame) if settings.save_images else None
                memory_snapshot = memory.snapshot(now)
                event = DetectionEvent.from_detection(
                    detection,
                    camera_name=settings.camera_name,
                    image_path=image_path,
                    contexto={
                        "zona": settings.scene_zone,
                        "iluminacion": settings.scene_lighting,
                        "cantidad_personas": sum(
                            1 for item in detections if item.label == "person"
                        ),
                    },
                    tracking=None,
                    memoria=memory_snapshot,
                )
                analysis = analyze_event(event.to_analysis_request())
                event = event.with_analysis(analysis)
                n8n_result = _send_to_n8n(n8n, event)
                store.save(event, n8n_result.response or event.analisis)
                memory.remember(now, analysis.result.risk_level)
                print(event.to_payload())

            cv2.imshow("SentinelAI - AgentePercepcion", draw_detections(frame, detections))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


def _save_frame(image_dir: Path, frame) -> str:
    image_dir.mkdir(parents=True, exist_ok=True)
    path = image_dir / f"evento_{int(time.time() * 1000)}.jpg"
    cv2.imwrite(str(path), frame)
    return str(path)


def _send_to_n8n(n8n: N8nClient, event: DetectionEvent):
    result = n8n.send(event)
    if not result.sent:
        print(f"n8n no recibio el evento: {result.error}")
        return result

    print(f"n8n respondio ({result.status_code}): {result.response}")
    return result


if __name__ == "__main__":
    run()
