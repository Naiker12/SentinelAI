from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si"}


def _as_optional_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value)


def _classes(value: str | None) -> set[str]:
    if not value:
        return {"persona"}
    return {_normalize_class_name(item) for item in value.split(",") if item.strip()}


def _normalize_class_name(value: str) -> str:
    return "_".join(value.strip().lower().replace("-", "_").split())


@dataclass(frozen=True)
class Settings:
    env_file: Path
    camera_index: int
    camera_backend: str
    camera_name: str
    camera_width: int | None
    camera_height: int | None
    camera_fps: int | None
    camera_fourcc: str | None
    camera_drop_stale_frames: int
    model_path: str
    confidence: float
    dangerous_confidence: float
    inference_confidence: float
    debug_detections: bool
    debug_confidence: float
    show_filtered_detections: bool
    yolo_tracking: bool
    yolo_tracker: str
    classes: set[str]
    event_cooldown_seconds: float
    dangerous_event_cooldown_seconds: float
    danger_hold_seconds: float
    scene_zone: str
    scene_lighting: str
    supabase_url: str | None
    supabase_service_role_key: str | None
    supabase_detection_events_table: str
    supabase_storage_bucket: str
    upload_evidence: bool
    n8n_webhook_url: str | None
    allow_n8n_test_webhook: bool
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    telegram_direct_alerts: bool
    telegram_callback_polling: bool
    save_images: bool
    image_dir: Path


def get_settings() -> Settings:
    webhook = os.getenv("SENTINEL_N8N_WEBHOOK_URL", "").strip()
    return Settings(
        env_file=ENV_FILE,
        camera_index=int(os.getenv("SENTINEL_CAMERA_INDEX", "0")),
        camera_backend=os.getenv("SENTINEL_CAMERA_BACKEND", "auto"),
        camera_name=os.getenv("SENTINEL_CAMERA_NAME", "PC-01"),
        camera_width=_as_optional_int(os.getenv("SENTINEL_CAMERA_WIDTH")),
        camera_height=_as_optional_int(os.getenv("SENTINEL_CAMERA_HEIGHT")),
        camera_fps=_as_optional_int(os.getenv("SENTINEL_CAMERA_FPS")),
        camera_fourcc=os.getenv("SENTINEL_CAMERA_FOURCC", "MJPG").strip() or None,
        camera_drop_stale_frames=int(os.getenv("SENTINEL_CAMERA_DROP_STALE_FRAMES", "2")),
        model_path=os.getenv(
            "SENTINEL_MODEL",
            "yolo_percepcion/entrenamiento_seguridad/weights/best.pt",
        ),
        confidence=float(os.getenv("SENTINEL_CONFIDENCE", "0.25")),
        dangerous_confidence=float(os.getenv("SENTINEL_DANGEROUS_CONFIDENCE", "0.35")),
        inference_confidence=float(os.getenv("SENTINEL_INFERENCE_CONFIDENCE", "0.20")),
        debug_detections=_as_bool(os.getenv("SENTINEL_DEBUG_DETECTIONS"), default=False),
        debug_confidence=float(os.getenv("SENTINEL_DEBUG_CONFIDENCE", "0.15")),
        show_filtered_detections=_as_bool(
            os.getenv("SENTINEL_SHOW_FILTERED_DETECTIONS"),
            default=False,
        ),
        yolo_tracking=_as_bool(os.getenv("SENTINEL_YOLO_TRACKING"), default=True),
        yolo_tracker=os.getenv("SENTINEL_YOLO_TRACKER", "botsort.yaml").strip() or "botsort.yaml",
        classes=_classes(os.getenv("SENTINEL_CLASSES", "persona")),
        event_cooldown_seconds=float(os.getenv("SENTINEL_EVENT_COOLDOWN_SECONDS", "5")),
        dangerous_event_cooldown_seconds=float(
            os.getenv("SENTINEL_DANGEROUS_EVENT_COOLDOWN_SECONDS", "120")
        ),
        danger_hold_seconds=float(os.getenv("SENTINEL_DANGER_HOLD_SECONDS", "2")),
        scene_zone=os.getenv("SENTINEL_SCENE_ZONE", "sin_zona"),
        scene_lighting=os.getenv("SENTINEL_SCENE_LIGHTING", "desconocida"),
        supabase_url=os.getenv("SUPABASE_URL", "").strip() or None,
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None,
        supabase_detection_events_table=os.getenv(
            "SUPABASE_DETECTION_EVENTS_TABLE", "detection_events"
        ),
        supabase_storage_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "imagen").strip()
        or "imagen",
        upload_evidence=_as_bool(os.getenv("SENTINEL_UPLOAD_EVIDENCE"), default=True),
        n8n_webhook_url=webhook or None,
        allow_n8n_test_webhook=_as_bool(
            os.getenv("SENTINEL_ALLOW_N8N_TEST_WEBHOOK"),
            default=False,
        ),
        telegram_bot_token=os.getenv("SENTINEL_TELEGRAM_BOT_TOKEN", "").strip() or None,
        telegram_chat_id=os.getenv("SENTINEL_TELEGRAM_CHAT_ID", "").strip() or None,
        telegram_direct_alerts=_as_bool(
            os.getenv("SENTINEL_TELEGRAM_DIRECT_ALERTS"),
            default=True,
        ),
        telegram_callback_polling=_as_bool(
            os.getenv("SENTINEL_TELEGRAM_CALLBACK_POLLING"),
            default=False,
        ),
        save_images=_as_bool(os.getenv("SENTINEL_SAVE_IMAGES"), default=False),
        image_dir=Path(os.getenv("SENTINEL_IMAGE_DIR", "capturas")),
    )
