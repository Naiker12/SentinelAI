from __future__ import annotations

from datetime import datetime, timezone

from agente_analisis.risk_engine import analyze_event
from agente_analisis.schemas import (
    AnalysisRequest,
    MemoryContext,
    PerceptionEvent,
    SceneContext,
    TrackingContext,
)


def test_analysis_marks_weapon_at_night_as_critical() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="knife",
            confianza=0.94,
            hora=datetime(2026, 5, 26, 23, 40, tzinfo=timezone.utc),
            camara="PC-01",
        ),
        contexto=SceneContext(zona="entrada", iluminacion="baja"),
        tracking=TrackingContext(
            person_id="track_14",
            velocidad=8.2,
            permanencia_segundos=420,
            movimiento_erratico=True,
        ),
        memoria=MemoryContext(eventos_previos_24h=12, alertas_previas_24h=2),
    )

    response = analyze_event(request)

    assert response.result.risk_level == "CRITICO"
    assert response.result.risk_score >= 101
    assert response.decision.action == "ALERTA_CRITICA"
    assert response.decision.notify is True


def test_analysis_marks_normal_person_as_low_or_medium() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="person",
            confianza=0.82,
            hora=datetime(2026, 5, 26, 15, 30, tzinfo=timezone.utc),
            camara="PC-01",
        ),
        contexto=SceneContext(zona="pasillo", iluminacion="normal"),
        tracking=TrackingContext(person_id="track_02", velocidad=1.2, permanencia_segundos=20),
    )

    response = analyze_event(request)

    assert response.result.risk_level == "BAJO"
    assert response.decision.notify is False


def test_analysis_marks_cell_phone_as_low() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="cell phone",
            confianza=0.92,
            hora=datetime(2026, 5, 26, 15, 30, tzinfo=timezone.utc),
            camara="PC-01",
        )
    )

    response = analyze_event(request)

    assert response.result.risk_level == "BAJO"
    assert response.decision.action == "REGISTRAR_EVENTO"


def test_analysis_ignores_low_confidence_unknown_object() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(objeto="unknown", confianza=0.3),
    )

    response = analyze_event(request)

    assert response.decision.action == "IGNORAR_BAJA_CONFIANZA"
