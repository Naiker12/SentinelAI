from __future__ import annotations

from dashboard.data import generate_events, normalize_supabase_events


def test_generate_events_has_dashboard_columns() -> None:
    df = generate_events(10)

    assert len(df) == 10
    assert {"timestamp", "camara_id", "objeto", "score_riesgo", "nivel_riesgo"}.issubset(
        df.columns
    )


def test_normalize_supabase_events_uses_detected_at() -> None:
    rows = [
        {
            "detected_at": "2026-05-26T12:00:00+00:00",
            "camara_id": "PC-01",
            "objeto": "person",
            "confianza": 0.91,
            "riesgo": "MEDIO",
            "box": [1, 2, 3, 4],
        }
    ]

    df = normalize_supabase_events(rows)

    assert len(df) == 1
    assert df.iloc[0]["camara_id"] == "PC-01"
    assert df.iloc[0]["nivel_riesgo"] == "MEDIO"
    assert df.iloc[0]["score_riesgo"] > 0
    assert df["timestamp"].dt.tz is None


def test_normalize_supabase_events_adds_spanish_labels() -> None:
    rows = [
        {
            "detected_at": "2026-05-26T12:00:00+00:00",
            "camara_id": "PC-01",
            "objeto": "cell phone",
            "confianza": 0.91,
            "riesgo": "BAJO",
            "accion_tomada": "REGISTRAR_EVENTO",
            "box": [1, 2, 3, 4],
        }
    ]

    df = normalize_supabase_events(rows)

    assert df.iloc[0]["objeto_nombre"] == "Celular"
    assert df.iloc[0]["nivel_nombre"] == "Bajo"
    assert df.iloc[0]["accion_nombre"] == "Registrar evento"


def test_normalize_supabase_events_reads_tracking_and_ia_context() -> None:
    rows = [
        {
            "detected_at": "2026-05-26T23:00:00+00:00",
            "camara_id": "PC-01",
            "objeto": "knife",
            "confianza": 0.91,
            "riesgo": "ALTO",
            "score_riesgo": 0.92,
            "nivel_riesgo": "CRITICO",
            "accion_tomada": "ALERTA_CRITICA",
            "box": [1, 2, 3, 4],
            "contexto": {
                "zona": "entrada",
                "tracking": {
                    "track_id": "knife_0001",
                    "person_id": "person_0001",
                    "velocidad": 8.5,
                    "permanencia_segundos": 120,
                    "movimiento_erratico": True,
                },
                "memoria": {"eventos_previos_24h": 9},
                "resumen_ia": "Objeto peligroso con persona asociada.",
            },
        }
    ]

    df = normalize_supabase_events(rows)

    assert df.iloc[0]["track_id"] == "knife_0001"
    assert df.iloc[0]["permanencia_s"] == 120
    assert df.iloc[0]["velocidad"] == 8.5
    assert df.iloc[0]["movimiento_erratico"] == True
    assert df.iloc[0]["eventos_previos_24h"] == 9
    assert "persona asociada" in df.iloc[0]["resumen_ia"]


def test_normalize_supabase_events_reads_human_interface_context() -> None:
    rows = [
        {
            "detected_at": "2026-05-26T23:00:00+00:00",
            "camara_id": "PC-01",
            "objeto": "knife",
            "confianza": 0.91,
            "riesgo": "ALTO",
            "score_riesgo": 0.92,
            "nivel_riesgo": "CRITICO",
            "accion_tomada": "SOLICITAR_VALIDACION_URGENTE",
            "box": [1, 2, 3, 4],
            "contexto": {
                "zona": "entrada",
                "requiere_revision_humana": True,
                "estado_revision_humana": "PENDIENTE",
                "automatizacion_bloqueada": True,
                "review_id": "PC-01_knife_20260526",
            },
        }
    ]

    df = normalize_supabase_events(rows)

    assert df.iloc[0]["requiere_revision_humana"] == True
    assert df.iloc[0]["estado_revision_humana"] == "PENDIENTE"
    assert df.iloc[0]["automatizacion_bloqueada"] == True
    assert df.iloc[0]["review_id"] == "PC-01_knife_20260526"
