from __future__ import annotations

from pathlib import Path

import numpy as np

from agente_percepcion.detector import Detection, draw_detections
from agente_percepcion.events import DetectionEvent, EventStore, N8nClient, risk_for_label


def test_detection_event_is_saved(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "events.sqlite3")
    detection = Detection(label="person", confidence=0.91, box=(10, 20, 200, 300))

    event = DetectionEvent.from_detection(detection, camera_name="PC-01")
    store.save(event)

    rows = store.latest(limit=5)

    assert len(rows) == 1
    assert rows[0]["object"] == "person"
    assert rows[0]["camera"] == "PC-01"
    assert rows[0]["risk"] == "medio"


def test_risk_levels() -> None:
    assert risk_for_label("knife") == "alto"
    assert risk_for_label("person") == "medio"
    assert risk_for_label("bottle") == "bajo"


def test_n8n_without_webhook_does_not_send() -> None:
    event = DetectionEvent(
        objeto="person",
        confianza=0.91,
        hora="2026-05-26T00:00:00+00:00",
        camara="PC-01",
        riesgo="medio",
        box=(10, 20, 200, 300),
    )

    assert N8nClient(webhook_url=None).send(event) is False


def test_draw_detections_adds_bounding_box() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    detection = Detection(label="person", confidence=0.91, box=(20, 30, 100, 90))

    output = draw_detections(frame.copy(), [detection])

    assert output.sum() > 0
    assert output[30, 20].sum() > 0
