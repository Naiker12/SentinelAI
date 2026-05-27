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
        return {"person"}
    return {_normalize_class_name(item) for item in value.split(",") if item.strip()}


def _normalize_class_name(value: str) -> str:
    return value.strip().lower().replace("_", " ")


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
    model_path: str
    confidence: float
    classes: set[str]
    event_cooldown_seconds: float
    scene_zone: str
    scene_lighting: str
    supabase_url: str | None
    supabase_service_role_key: str | None
    supabase_detection_events_table: str
    n8n_webhook_url: str | None
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
        model_path=os.getenv("SENTINEL_MODEL", "agente_percepcion/model/best.pt"),
        confidence=float(os.getenv("SENTINEL_CONFIDENCE", "0.5")),
        classes=_classes(os.getenv("SENTINEL_CLASSES", "person")),
        event_cooldown_seconds=float(os.getenv("SENTINEL_EVENT_COOLDOWN_SECONDS", "5")),
        scene_zone=os.getenv("SENTINEL_SCENE_ZONE", "sin_zona"),
        scene_lighting=os.getenv("SENTINEL_SCENE_LIGHTING", "desconocida"),
        supabase_url=os.getenv("SUPABASE_URL", "").strip() or None,
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None,
        supabase_detection_events_table=os.getenv(
            "SUPABASE_DETECTION_EVENTS_TABLE", "detection_events"
        ),
        n8n_webhook_url=webhook or None,
        save_images=_as_bool(os.getenv("SENTINEL_SAVE_IMAGES"), default=False),
        image_dir=Path(os.getenv("SENTINEL_IMAGE_DIR", "capturas")),
    )
