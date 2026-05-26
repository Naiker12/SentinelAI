from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

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


class EventStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS detection_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    camera TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    risk TEXT NOT NULL,
                    box TEXT NOT NULL,
                    image_path TEXT
                )
                """
            )

    def save(self, event: DetectionEvent) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO detection_events (
                    created_at, camera, object, confidence, risk, box, image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.hora,
                    event.camara,
                    event.objeto,
                    event.confianza,
                    event.riesgo,
                    ",".join(str(value) for value in event.box),
                    event.imagen,
                ),
            )

    def latest(self, limit: int = 50) -> list[dict]:
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, created_at, camera, object, confidence, risk, box, image_path
                FROM detection_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


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
