from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests

from agente_percepcion.detector import Detection


@dataclass(frozen=True)
class DetectionEvent:
    objeto: str
    confianza: float
    hora: str
    camara: str
    riesgo: str
    box: tuple[int, int, int, int]
    imagen: str | None = None

    @classmethod
    def from_detection(
        cls,
        detection: Detection,
        camera_name: str,
        image_path: str | None = None,
    ) -> "DetectionEvent":
        return cls(
            objeto=detection.label,
            confianza=detection.confidence,
            hora=datetime.now(timezone.utc).isoformat(),
            camara=camera_name,
            riesgo=risk_for_label(detection.label),
            box=detection.box,
            imagen=image_path,
        )

    def to_payload(self) -> dict:
        return asdict(self)

    def to_supabase_row(self) -> dict:
        return {
            "objeto": self.objeto,
            "confianza": self.confianza,
            "riesgo": self.riesgo.upper(),
            "detected_at": self.hora,
            "camara_id": self.camara,
            "box": list(self.box),
            "imagen_url": self.imagen,
        }


class SupabaseEventStore:
    def __init__(self, supabase_url: str | None, service_role_key: str | None, table: str) -> None:
        if not supabase_url or not service_role_key:
            raise RuntimeError(
                "Faltan SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en el archivo .env."
            )

        from supabase import create_client

        self._client = create_client(supabase_url, service_role_key)
        self._table = table

    def save(self, event: DetectionEvent) -> None:
        self._client.table(self._table).insert(event.to_supabase_row()).execute()

    def latest(self, limit: int = 50) -> list[dict]:
        response = (
            self._client.table(self._table)
            .select("*")
            .order("detected_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])


class N8nClient:
    def __init__(self, webhook_url: str | None, timeout_seconds: float = 5) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def send(self, event: DetectionEvent) -> bool:
        if not self.webhook_url:
            return False

        response = requests.post(
            self.webhook_url,
            json=event.to_payload(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return True


def risk_for_label(label: str) -> str:
    high_risk = {"knife", "scissors", "gun"}
    medium_risk = {"person", "car", "truck", "backpack", "cell phone"}

    if label in high_risk:
        return "alto"
    if label in medium_risk:
        return "medio"
    return "bajo"
