from __future__ import annotations

import time
from pathlib import Path

import cv2

from agente_percepcion.camera import Camera
from agente_percepcion.config import get_settings
from agente_percepcion.detector import YoloDetector, draw_detections
from agente_percepcion.events import DetectionEvent, EventStore, N8nClient


def run() -> None:
    settings = get_settings()
    detector = YoloDetector(settings.model_path, settings.confidence, settings.classes)
    store = EventStore(settings.database_path)
    n8n = N8nClient(settings.n8n_webhook_url)
    last_event_at: dict[str, float] = {}

    if settings.save_images:
        settings.image_dir.mkdir(parents=True, exist_ok=True)

    with Camera(settings.camera_index) as camera:
        while True:
            frame = camera.read()
            detections = detector.detect(frame)
            now = time.monotonic()

            for detection in detections:
                last_seen = last_event_at.get(detection.label, 0)
                if now - last_seen < settings.event_cooldown_seconds:
                    continue

                image_path = _save_frame(settings.image_dir, frame) if settings.save_images else None
                event = DetectionEvent.from_detection(
                    detection,
                    camera_name=settings.camera_name,
                    image_path=image_path,
                )
                store.save(event)
                _send_to_n8n(n8n, event)
                last_event_at[detection.label] = now
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


def _send_to_n8n(n8n: N8nClient, event: DetectionEvent) -> None:
    try:
        n8n.send(event)
    except Exception as exc:
        print(f"No se pudo enviar evento a n8n: {exc}")


if __name__ == "__main__":
    run()
