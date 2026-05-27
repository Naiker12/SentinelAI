from __future__ import annotations

import numpy as np
import sys
import types

from agente_percepcion.config import _classes
from agente_percepcion.detector import Detection, draw_detections, normalize_label
from agente_percepcion.events import DetectionEvent, N8nClient, _storage_path_for_event, risk_for_label
from agente_percepcion.telegram import TelegramSupervisorClient
from agente_percepcion.memory import should_emit_detection
from agente_analisis.risk_engine import analyze_event


def test_detection_event_maps_to_supabase_row() -> None:
    detection = Detection(label="person", confidence=0.91, box=(10, 20, 200, 300))

    event = DetectionEvent.from_detection(detection, camera_name="PC-01")
    row = event.to_supabase_row()

    assert row["objeto"] == "person"
    assert row["camara_id"] == "PC-01"
    assert row["riesgo"] == "BAJO"
    assert row["box"] == [10, 20, 200, 300]


def test_detection_event_stores_public_image_url_in_supabase_row() -> None:
    detection = Detection(label="violence", confidence=0.91, box=(10, 20, 200, 300))
    image_url = "https://example.supabase.co/storage/v1/object/public/imagen/evento.jpg"

    event = DetectionEvent.from_detection(
        detection,
        camera_name="PC-01",
        image_path=image_url,
    )
    row = event.to_supabase_row()

    assert row["imagen_url"] == image_url


def test_detection_event_maps_n8n_persistence_to_supabase_row() -> None:
    detection = Detection(label="knife", confidence=0.91, box=(10, 20, 200, 300))
    event = DetectionEvent.from_detection(detection, camera_name="PC-01")
    response = {
        "persistencia": {
            "score_riesgo": 0.95,
            "nivel_riesgo": "CRITICO",
            "accion_tomada": "ALERTA_CRITICA",
            "alertas_previas_24h": 2,
            "detected_at": "2026-05-26T23:30:00+00:00",
            "contexto": {"zona": "entrada"},
            "tracking": {"track_id": "knife_0001", "person_id": "person_0001"},
            "memoria": {"eventos_previos_24h": 12},
            "resumen_ia": "Objeto peligroso asociado a una persona.",
        }
    }

    row = event.to_supabase_row(response)

    assert row["score_riesgo"] == 0.95
    assert row["nivel_riesgo"] == "CRITICO"
    assert row["accion_tomada"] == "ALERTA_CRITICA"
    assert row["hora_dia"] == 23
    assert row["contexto"]["tracking"]["person_id"] == "person_0001"
    assert row["contexto"]["resumen_ia"] == "Objeto peligroso asociado a una persona."


def test_risk_levels() -> None:
    assert risk_for_label("Violence") == "alto"
    assert risk_for_label("NonViolence") == "bajo"
    assert risk_for_label("fusil") == "alto"
    assert risk_for_label("persona_sospechosa") == "medio"
    assert risk_for_label("knife") == "alto"
    assert risk_for_label("gun") == "alto"
    assert risk_for_label("pistol") == "alto"
    assert risk_for_label("pistola") == "alto"
    assert risk_for_label("scissors") == "alto"
    assert risk_for_label("person") == "bajo"
    assert risk_for_label("persona") == "bajo"
    assert risk_for_label("cell phone") == "bajo"
    assert risk_for_label("cell_phone") == "bajo"
    assert risk_for_label("backpack") == "bajo"
    assert risk_for_label("bottle") == "bajo"


def test_detection_labels_normalize_weapon_aliases() -> None:
    assert normalize_label("pistol") == "arma"
    assert normalize_label("handgun") == "arma"
    assert normalize_label("firearm") == "arma"
    assert normalize_label("pistola") == "arma"
    assert normalize_label("knife") == "arma_blanca"
    assert normalize_label("cell phone") == "cell_phone"
    assert normalize_label("NonViolence") == "no_violencia"
    assert normalize_label("pelea") == "violencia"


def test_allowed_classes_normalize_to_detector_labels() -> None:
    assert _classes("persona,arma_blanca,arma,cell_phone") == {
        "persona",
        "arma_blanca",
        "arma",
        "cell_phone",
    }


def test_debug_detector_uses_lower_predict_confidence(monkeypatch) -> None:
    from agente_percepcion import detector as detector_module
    from agente_percepcion.detector import YoloDetector

    calls = []

    class FakeBox:
        cls = [0]
        conf = [0.2]
        xyxy = [[10, 20, 30, 40]]

    class FakeModel:
        names = {0: "arma"}

        def predict(self, frame, conf, verbose):
            calls.append(conf)
            return [type("Result", (), {"names": self.names, "boxes": [FakeBox()]})()]

    monkeypatch.setattr(detector_module, "_configure_ultralytics_runtime", lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "ultralytics",
        types.SimpleNamespace(YOLO=lambda model_path: FakeModel()),
    )

    detector = YoloDetector(
        "yolov8n.pt",
        confidence=0.5,
        allowed_classes={"arma"},
        debug_detections=True,
        debug_confidence=0.1,
    )

    assert detector.detect(np.zeros((10, 10, 3), dtype=np.uint8)) == []
    assert calls == [0.1]


def test_n8n_without_webhook_does_not_send() -> None:
    event = DetectionEvent(
        objeto="person",
        confianza=0.91,
        hora="2026-05-26T00:00:00+00:00",
        camara="PC-01",
        riesgo="medio",
        box=(10, 20, 200, 300),
    )

    result = N8nClient(webhook_url=None).send(event)

    assert result.sent is False
    assert result.error is not None


def test_n8n_rejects_test_webhook_for_camera_flow() -> None:
    event = DetectionEvent(
        objeto="person",
        confianza=0.91,
        hora="2026-05-26T00:00:00+00:00",
        camara="PC-01",
        riesgo="bajo",
        box=(10, 20, 200, 300),
    )

    result = N8nClient("http://localhost:5678/webhook-test/sentinel-analysis").send(event)

    assert result.sent is False
    assert result.error is not None
    assert "/webhook/sentinel-analysis" in result.error


def test_n8n_can_allow_test_webhook_for_manual_workflow_debug() -> None:
    event = DetectionEvent(
        objeto="person",
        confianza=0.91,
        hora="2026-05-26T00:00:00+00:00",
        camara="PC-01",
        riesgo="bajo",
        box=(10, 20, 200, 300),
    )

    client = N8nClient(
        "http://localhost:5678/webhook-test/sentinel-analysis",
        allow_test_webhook=True,
    )

    assert client.webhook_url.endswith("/webhook-test/sentinel-analysis")
    assert client.allow_test_webhook is True


def test_detection_event_includes_analysis_context() -> None:
    detection = Detection(label="knife", confidence=0.91, box=(10, 20, 200, 300))

    event = DetectionEvent.from_detection(
        detection,
        camera_name="PC-01",
        contexto={"zona": "entrada", "iluminacion": "baja", "cantidad_personas": 1},
        tracking={
            "person_id": "person_0001",
            "track_id": "knife_0001",
            "velocidad": 12.5,
            "permanencia_segundos": 3,
            "movimiento_erratico": False,
        },
        memoria={"eventos_previos_24h": 2, "alertas_previas_24h": 1},
    )

    payload = event.to_payload()

    assert payload["contexto"]["zona"] == "entrada"
    assert payload["tracking"]["person_id"] == "person_0001"
    assert payload["memoria"]["alertas_previas_24h"] == 1


def test_detection_event_can_emit_precomputed_analysis_payload() -> None:
    detection = Detection(label="pistol", confidence=0.94, box=(10, 20, 200, 300))
    event = DetectionEvent.from_detection(
        detection,
        camera_name="PC-01",
        contexto={"zona": "entrada", "iluminacion": "baja", "cantidad_personas": 1},
        tracking={
            "person_id": "person_0001",
            "track_id": "gun_0001",
            "velocidad": 8.2,
            "permanencia_segundos": 420,
            "movimiento_erratico": True,
        },
        memoria={"eventos_previos_24h": 12, "alertas_previas_24h": 2},
    )

    analyzed = event.with_analysis(analyze_event(event.to_analysis_request()))
    payload = analyzed.to_payload()

    assert payload["entrada"]["objeto"] == "arma"
    assert payload["tracking"]["track_id"] == "gun_0001"
    assert payload["resultado"]["nivel_riesgo"] == "CRITICO"
    assert payload["decision"]["accion_tomada"] == "SOLICITAR_VALIDACION_URGENTE"
    assert payload["decision"]["requiere_revision_humana"] is True
    assert payload["decision"]["automatizacion_bloqueada"] is True
    assert payload["persistencia"]["tracking"]["person_id"] == "person_0001"


def test_storage_path_for_event_is_stable_and_grouped() -> None:
    event = DetectionEvent(
        objeto="violence",
        confianza=0.91,
        hora="2026-05-27T17:50:07+00:00",
        camara="PC-01",
        riesgo="alto",
        box=(10, 20, 200, 300),
    )

    path = _storage_path_for_event(event, local_path="capturas/evento_123.jpg")

    assert path.startswith("PC-01/2026/05/27/violencia/")
    assert path.endswith(".jpg")


def test_telegram_validation_sends_public_image_url(monkeypatch) -> None:
    calls = []

    class Response:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr("agente_percepcion.telegram.requests.post", fake_post)
    detection = Detection(label="violence", confidence=0.91, box=(10, 20, 200, 300))
    event = DetectionEvent.from_detection(
        detection,
        camera_name="PC-01",
        image_path="https://example.supabase.co/storage/v1/object/public/imagen/evento.jpg",
    ).with_analysis(analyze_event(DetectionEvent.from_detection(detection, "PC-01").to_analysis_request()))

    result = TelegramSupervisorClient("token", "123").send_validation(event)

    assert result.sent is True
    assert calls[0][0].endswith("/sendPhoto")
    assert calls[0][1]["json"]["photo"].startswith("https://example.supabase.co")


def test_event_gate_uses_label_and_camera_cooldown() -> None:
    last_event_at: dict[str, float] = {}

    assert should_emit_detection("person", "PC-01", last_event_at, 1.0, 5)
    assert not should_emit_detection("person", "PC-01", last_event_at, 2.0, 5)
    assert should_emit_detection("person", "CAM-02", last_event_at, 2.0, 5)
    assert should_emit_detection("person", "PC-01", last_event_at, 7.0, 5)


def test_event_gate_allows_same_label_in_different_frame_regions() -> None:
    last_event_at: dict[str, float] = {}

    assert should_emit_detection("violence", "PC-01", last_event_at, 1.0, 5, (10, 10, 120, 120))
    assert should_emit_detection("violence", "PC-01", last_event_at, 1.1, 5, (360, 10, 500, 120))
    assert not should_emit_detection("violence", "PC-01", last_event_at, 1.2, 5, (15, 15, 125, 125))


def test_draw_detections_adds_bounding_box() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    detection = Detection(label="person", confidence=0.91, box=(20, 30, 100, 90))

    output = draw_detections(frame.copy(), [detection])

    assert output.sum() > 0
    assert output[30, 20].sum() > 0


def test_draw_detections_marks_violence_as_high_risk_color() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    detection = Detection(label="violence", confidence=0.91, box=(20, 30, 100, 90))

    output = draw_detections(frame.copy(), [detection])

    assert output[30, 20, 2] > output[30, 20, 1]
