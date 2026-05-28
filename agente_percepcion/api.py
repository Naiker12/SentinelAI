from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, Query

from agente_analisis.risk_engine import analyze_event
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
    detector = YoloDetector(
        settings.model_path,
        settings.confidence,
        settings.classes,
        dangerous_confidence=settings.dangerous_confidence,
        inference_confidence=settings.inference_confidence,
        debug_detections=settings.debug_detections,
        debug_confidence=settings.debug_confidence,
        show_filtered_detections=settings.show_filtered_detections,
        debug_filtered_classes=settings.debug_filtered_classes,
        use_model_tracking=settings.yolo_tracking,
        tracker=settings.yolo_tracker,
    )
    n8n = N8nClient(
        settings.n8n_webhook_url,
        allow_test_webhook=settings.allow_n8n_test_webhook,
    )

    with Camera(
        settings.camera_index,
        backend=settings.camera_backend,
        width=settings.camera_width,
        height=settings.camera_height,
        fps=settings.camera_fps,
        fourcc=settings.camera_fourcc,
        drop_stale_frames=settings.camera_drop_stale_frames,
    ) as camera:
        frame = camera.read()
        detections = [
            detection
            for detection in detector.detect(frame)
            if not detection.filtered_reason
        ]

    saved_events = []
    for detection in detections:
        event = DetectionEvent.from_detection(
            detection,
            camera_name=settings.camera_name,
            contexto={
                "zona": settings.scene_zone,
                "iluminacion": settings.scene_lighting,
                "cantidad_personas": sum(1 for item in detections if item.label == "persona"),
            },
            tracking=detection.tracking,
            memoria={"eventos_previos_24h": 0, "alertas_previas_24h": 0},
        )
        event = event.with_analysis(analyze_event(event.to_analysis_request()))
        n8n_result = n8n.send(event)
        get_store().save(event, n8n_result.response)
        saved_events.append(
            {
                **event.to_payload(),
                "sent_to_n8n": n8n_result.sent,
                "n8n_status_code": n8n_result.status_code,
                "n8n_response": n8n_result.response,
                "n8n_error": n8n_result.error,
            }
        )

    return {"detections": saved_events}
