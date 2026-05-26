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
