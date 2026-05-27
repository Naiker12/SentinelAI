from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv


load_dotenv()


LEVEL_ORDER = ["BAJO", "MEDIO", "ALTO", "CRITICO"]
OBJECTS = ["person", "knife", "gun", "backpack", "cell_phone", "scissors"]
CAMERAS = ["PC-01", "CAM-02", "CAM-03", "CAM-04"]
ZONES = ["Entrada principal", "Pasillo central", "Patio trasero", "Estacionamiento"]
ACTIONS = {
    "BAJO": "REGISTRAR_EVENTO",
    "MEDIO": "MONITOREAR",
    "ALTO": "ENVIAR_ALERTA",
    "CRITICO": "ALERTA_CRITICA",
}
RISK_BASE = {
    "violence": 0.80,
    "nonviolence": 0.05,
    "gun": 0.95,
    "knife": 0.80,
    "scissors": 0.50,
    "backpack": 0.35,
    "cell_phone": 0.15,
    "person": 0.20,
}
OBJECT_LABELS = {
    "violence": "Violencia",
    "nonviolence": "No violencia",
    "non violence": "No violencia",
    "person": "Persona",
    "knife": "Cuchillo",
    "gun": "Pistola",
    "backpack": "Mochila",
    "cell_phone": "Celular",
    "cell phone": "Celular",
    "scissors": "Tijeras",
}
ACTION_LABELS = {
    "REGISTRAR_EVENTO": "Registrar evento",
    "MONITOREAR": "Monitorear",
    "ENVIAR_ALERTA": "Enviar alerta",
    "ALERTA_CRITICA": "Alerta critica",
    "IGNORAR_BAJA_CONFIANZA": "Ignorar por baja confianza",
    "SOLICITAR_REVISION_HUMANA": "Solicitar revision humana",
    "SOLICITAR_VALIDACION_HUMANA": "Solicitar validacion humana",
    "SOLICITAR_VALIDACION_URGENTE": "Validacion urgente",
}
LEVEL_LABELS = {
    "BAJO": "Bajo",
    "MEDIO": "Medio",
    "ALTO": "Alto",
    "CRITICO": "Critico",
}


def level_from_score(score: float) -> str:
    if score < 0.35:
        return "BAJO"
    if score < 0.60:
        return "MEDIO"
    if score < 0.80:
        return "ALTO"
    return "CRITICO"


def score_from_level(level: str) -> float:
    return {
        "BAJO": 0.20,
        "MEDIO": 0.45,
        "ALTO": 0.70,
        "CRITICO": 0.90,
    }.get(str(level).upper(), 0.20)


def generate_events(count: int = 300) -> pd.DataFrame:
    random.seed(42)
    now = datetime.now()
    rows: list[dict] = []
    tracking_ids: dict[str, list[str]] = {}

    for _ in range(count):
        timestamp = now - timedelta(hours=random.expovariate(0.15))
        obj = random.choices(OBJECTS, weights=[40, 12, 5, 18, 20, 5])[0]
        camera_index = random.randint(0, len(CAMERAS) - 1)
        camera = CAMERAS[camera_index]
        zone = ZONES[camera_index]
        confidence = round(random.uniform(0.50, 0.99), 2)
        hour = timestamp.hour

        score = RISK_BASE[obj] + (confidence - 0.5) * 0.3
        if 0 <= hour < 6:
            score += 0.20
        score += random.uniform(-0.05, 0.05)
        score = round(min(max(score, 0.0), 1.0), 2)
        level = level_from_score(score)

        tracking_ids.setdefault(camera, [])
        if obj == "person":
            if not tracking_ids[camera] or random.random() < 0.3:
                track_id = f"T{random.randint(100, 999)}"
                tracking_ids[camera].append(track_id)
                tracking_ids[camera] = tracking_ids[camera][-5:]
            else:
                track_id = random.choice(tracking_ids[camera])
            permanence = round(random.uniform(0.5, 45.0), 1)
        else:
            track_id = None
            permanence = None
        speed = round(random.uniform(0, 12), 2) if track_id else 0.0
        erratic = bool(track_id and random.random() < 0.12)

        rows.append(
            {
                "timestamp": timestamp,
                "camara_id": camera,
                "zona": zone,
                "objeto": obj,
                "confianza": confidence,
                "score_riesgo": score,
                "nivel_riesgo": level,
                "accion_tomada": ACTIONS[level],
                "objeto_nombre": OBJECT_LABELS.get(obj, obj),
                "accion_nombre": ACTION_LABELS[ACTIONS[level]],
                "nivel_nombre": LEVEL_LABELS[level],
                "track_id": track_id,
                "permanencia_s": permanence,
                "velocidad": speed,
                "movimiento_erratico": erratic,
                "eventos_previos_24h": random.randint(0, 20),
                "resumen_ia": (
                    "Objeto peligroso con contexto de seguimiento."
                    if level in {"ALTO", "CRITICO"}
                    else ""
                ),
                "factores_ia": [],
                "requiere_revision_humana": level in {"MEDIO", "ALTO", "CRITICO"},
                "estado_revision_humana": "PENDIENTE" if level in {"MEDIO", "ALTO", "CRITICO"} else "NO_REQUERIDA",
                "automatizacion_bloqueada": level in {"MEDIO", "ALTO", "CRITICO"},
                "review_id": f"{camera}_{obj}_{int(timestamp.timestamp())}",
                "hora": hour,
                "dia_semana": timestamp.strftime("%A"),
            }
        )

    return pd.DataFrame(rows).sort_values("timestamp", ascending=False).reset_index(drop=True)


def normalize_supabase_events(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=dashboard_columns())

    df = pd.DataFrame(rows)
    if "timestamp" not in df.columns:
        df["timestamp"] = df.get("detected_at", df.get("created_at"))
    df["timestamp"] = normalize_timestamp_series(df["timestamp"])

    if "nivel_riesgo" not in df.columns or df["nivel_riesgo"].isna().all():
        df["nivel_riesgo"] = df.get("riesgo", "BAJO")
    df["nivel_riesgo"] = df["nivel_riesgo"].fillna(df.get("riesgo", "BAJO")).astype(str).str.upper()

    if "score_riesgo" not in df.columns:
        df["score_riesgo"] = df["nivel_riesgo"].map(score_from_level)
    df["score_riesgo"] = pd.to_numeric(df["score_riesgo"], errors="coerce")
    df["score_riesgo"] = df["score_riesgo"].fillna(df["nivel_riesgo"].map(score_from_level)).fillna(0.0)

    if "accion_tomada" not in df.columns:
        df["accion_tomada"] = df["nivel_riesgo"].map(ACTIONS)
    df["accion_tomada"] = df["accion_tomada"].fillna(df["nivel_riesgo"].map(ACTIONS))

    if "zona" not in df.columns:
        df["zona"] = df.get("ubicacion", "Sin zona")
    df["zona"] = df["zona"].fillna("Sin zona")

    context_series = df["contexto"] if "contexto" in df.columns else pd.Series([{}] * len(df))
    tracking_series = context_series.map(_context_tracking)
    memory_series = context_series.map(_context_memory)

    if "track_id" not in df.columns:
        df["track_id"] = tracking_series.map(lambda value: value.get("track_id") or value.get("person_id"))
    if "permanencia_s" not in df.columns:
        df["permanencia_s"] = tracking_series.map(lambda value: value.get("permanencia_segundos"))
    if "velocidad" not in df.columns:
        df["velocidad"] = tracking_series.map(lambda value: value.get("velocidad"))
    if "movimiento_erratico" not in df.columns:
        df["movimiento_erratico"] = tracking_series.map(lambda value: value.get("movimiento_erratico", False))
    if "resumen_ia" not in df.columns:
        df["resumen_ia"] = context_series.map(lambda value: _safe_dict(value).get("resumen_ia"))
    if "factores_ia" not in df.columns:
        df["factores_ia"] = context_series.map(lambda value: _safe_dict(value).get("factores_ia"))
    if "eventos_previos_24h" not in df.columns:
        df["eventos_previos_24h"] = memory_series.map(lambda value: value.get("eventos_previos_24h", 0))
    if "requiere_revision_humana" not in df.columns:
        df["requiere_revision_humana"] = df["nivel_riesgo"].isin(["MEDIO", "ALTO", "CRITICO"])
    if "estado_revision_humana" not in df.columns:
        df["estado_revision_humana"] = context_series.map(
            lambda value: _safe_dict(value).get("estado_revision_humana")
        )
    if "automatizacion_bloqueada" not in df.columns:
        df["automatizacion_bloqueada"] = context_series.map(
            lambda value: _safe_dict(value).get("automatizacion_bloqueada")
        )
    if "review_id" not in df.columns:
        df["review_id"] = context_series.map(lambda value: _safe_dict(value).get("review_id"))

    df["hora"] = df.get("hora_dia")
    df["hora"] = pd.to_numeric(df["hora"], errors="coerce")
    df["hora"] = df["hora"].fillna(df["timestamp"].dt.hour).astype(int)
    df["dia_semana"] = df["timestamp"].dt.strftime("%A")
    df["confianza"] = pd.to_numeric(df.get("confianza", 0.0), errors="coerce").fillna(0.0)
    df["permanencia_s"] = pd.to_numeric(df["permanencia_s"], errors="coerce")
    df["velocidad"] = pd.to_numeric(df["velocidad"], errors="coerce").fillna(0.0)
    df["movimiento_erratico"] = df["movimiento_erratico"].fillna(False).astype(bool)
    df["eventos_previos_24h"] = pd.to_numeric(df["eventos_previos_24h"], errors="coerce").fillna(0).astype(int)
    df["resumen_ia"] = df["resumen_ia"].fillna("")
    df["requiere_revision_humana"] = df["requiere_revision_humana"].fillna(False).astype(bool)
    df["estado_revision_humana"] = df["estado_revision_humana"].fillna(
        df["requiere_revision_humana"].map(lambda value: "PENDIENTE" if value else "NO_REQUERIDA")
    )
    df["automatizacion_bloqueada"] = df["automatizacion_bloqueada"].fillna(False).astype(bool)
    df["review_id"] = df["review_id"].fillna("")
    df["camara_id"] = df.get("camara_id", "PC-01")
    df["objeto"] = df.get("objeto", "unknown")
    df["objeto_nombre"] = df["objeto"].map(OBJECT_LABELS).fillna(df["objeto"])
    df["accion_nombre"] = df["accion_tomada"].map(ACTION_LABELS).fillna(df["accion_tomada"])
    df["nivel_nombre"] = df["nivel_riesgo"].map(LEVEL_LABELS).fillna(df["nivel_riesgo"])

    return df[dashboard_columns()].sort_values("timestamp", ascending=False).reset_index(drop=True)


def dashboard_columns() -> list[str]:
    return [
        "timestamp",
        "camara_id",
        "zona",
        "objeto",
        "confianza",
        "score_riesgo",
        "nivel_riesgo",
        "nivel_nombre",
        "accion_tomada",
        "accion_nombre",
        "objeto_nombre",
        "track_id",
        "permanencia_s",
        "velocidad",
        "movimiento_erratico",
        "eventos_previos_24h",
        "resumen_ia",
        "factores_ia",
        "requiere_revision_humana",
        "estado_revision_humana",
        "automatizacion_bloqueada",
        "review_id",
        "hora",
        "dia_semana",
    ]


def normalize_timestamp_series(series: pd.Series) -> pd.Series:
    timestamps = pd.to_datetime(series, errors="coerce", utc=True)
    fallback = pd.Timestamp.now(tz="UTC")
    timestamps = timestamps.fillna(fallback)
    return timestamps.dt.tz_convert(None)


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _context_tracking(value) -> dict:
    context = _safe_dict(value)
    return _safe_dict(context.get("tracking"))


def _context_memory(value) -> dict:
    context = _safe_dict(value)
    return _safe_dict(context.get("memoria"))


def load_events(limit: int = 500) -> tuple[pd.DataFrame, str]:
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        return generate_events(300), "Datos simulados"

    try:
        from supabase import create_client

        client = create_client(supabase_url, supabase_key)
        response = (
            client.table("detection_events")
            .select("*")
            .order("detected_at", desc=True)
            .limit(limit)
            .execute()
        )
        return normalize_supabase_events(response.data or []), "Supabase real"
    except Exception as exc:
        return generate_events(300), f"Datos simulados: {exc}"
