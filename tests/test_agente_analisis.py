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
            objeto="arma_blanca",
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
    assert response.result.risk_score == 100
    assert response.decision.action == "SOLICITAR_VALIDACION_URGENTE"
    assert response.decision.notify is True
    assert response.decision.requires_human_review is True
    assert response.decision.automation_locked is True


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
    assert response.decision.requires_human_review is False


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


def test_analysis_normalizes_pistol_alias_to_gun() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="pistola",
            confianza=0.94,
            hora=datetime(2026, 5, 26, 23, 40, tzinfo=timezone.utc),
            camara="PC-01",
        ),
        contexto=SceneContext(zona="entrada", iluminacion="baja"),
        tracking=TrackingContext(person_id="person_0001", track_id="gun_0001", velocidad=8.2),
    )

    response = analyze_event(request)

    assert response.result.risk_level == "CRITICO"
    assert any(factor.detail == "Objeto detectado: arma." for factor in response.result.factors)
    assert response.decision.requires_human_review is True


def test_analysis_sends_medium_risk_to_human_supervisor() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="arma_blanca",
            confianza=0.82,
            hora=datetime(2026, 5, 26, 15, 30, tzinfo=timezone.utc),
            camara="PC-01",
        )
    )

    response = analyze_event(request)

    assert response.result.risk_level == "ALTO"
    assert response.decision.action == "SOLICITAR_VALIDACION_HUMANA"
    assert response.decision.channels == ["telegram_supervisor", "dashboard_realtime"]
    assert response.decision.requires_human_review is True
    assert response.decision.human_review_status == "PENDIENTE"


def test_analysis_ignores_low_confidence_unknown_object() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(objeto="unknown", confianza=0.3),
    )

    response = analyze_event(request)

    assert response.decision.action == "IGNORAR_BAJA_CONFIANZA"


def test_analysis_marks_violence_as_high_risk_for_human_review() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="Violence",
            confianza=0.86,
            hora=datetime(2026, 5, 27, 20, 30, tzinfo=timezone.utc),
            camara="PC-01",
        )
    )

    response = analyze_event(request)

    assert response.result.risk_level == "ALTO"
    assert response.result.possible_behavior == "posible_pelea_o_agresion"
    assert response.decision.requires_human_review is True


def test_analysis_marks_nonviolence_as_low_risk() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="NonViolence",
            confianza=0.92,
            hora=datetime(2026, 5, 27, 14, 30, tzinfo=timezone.utc),
            camara="PC-01",
        )
    )

    response = analyze_event(request)

    assert response.result.risk_level == "BAJO"
    assert response.decision.requires_human_review is False


def test_analysis_marks_persona_sospechosa_as_medium_risk() -> None:
    request = AnalysisRequest(
        evento=PerceptionEvent(
            objeto="persona_sospechosa",
            confianza=0.84,
            hora=datetime(2026, 5, 27, 16, 30, tzinfo=timezone.utc),
            camara="PC-01",
        )
    )

    response = analyze_event(request)

    assert response.result.risk_level == "MEDIO"
    assert response.result.possible_behavior == "persona_conducta_sospechosa"
    assert response.decision.requires_human_review is True
