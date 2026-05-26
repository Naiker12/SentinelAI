from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, Query

from agente_percepcion.camera import Camera
from agente_percepcion.config import get_settings
from agente_percepcion.detector import YoloDetector
from agente_percepcion.events import DetectionEvent, N8nClient, SupabaseEventStore


settings = get_settings()
app = FastAPI(title="SentinelAI AgentePercepcion", version="0.1.0")


@lru_cache(maxsize=1)
def get_store() -> SupabaseEventStore:
    return SupabaseEventStore(
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.supabase_detection_events_table,
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "agent": "AgentePercepcion",
        "camera": settings.camera_name,
    }


@app.get("/events")
def events(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return get_store().latest(limit=limit)


@app.post("/detect-once")
def detect_once() -> dict:
    detector = YoloDetector(settings.model_path, settings.confidence, settings.classes)
    n8n = N8nClient(settings.n8n_webhook_url)

    with Camera(settings.camera_index, backend=settings.camera_backend) as camera:
        frame = camera.read()
        detections = detector.detect(frame)

    saved_events = []
    for detection in detections:
        event = DetectionEvent.from_detection(detection, camera_name=settings.camera_name)
        get_store().save(event)
        try:
            sent_to_n8n = n8n.send(event)
            n8n_error = None
        except Exception as exc:
            sent_to_n8n = False
            n8n_error = str(exc)
        saved_events.append(
            {**event.to_payload(), "sent_to_n8n": sent_to_n8n, "n8n_error": n8n_error}
        )

    return {"detections": saved_events}
