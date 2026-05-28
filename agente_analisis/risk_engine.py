from __future__ import annotations

import math
from datetime import datetime

from agente_analisis.schemas import (
    ActionDecision,
    AnalysisRequest,
    AnalysisResponse,
    RiskFactor,
    RiskResult,
)

OBJECT_BASE_SCORES = {
    "arma": 80,
    "arma_blanca": 65,
    "fusil": 95,
    "violencia": 75,
    "multitud": 35,
    "persona_sospechosa": 45,
    "no_violencia": 2,
    "persona": 10,
    "cell_phone": 5,
    "backpack": 18,
    "car": 8,
    "truck": 8,
    "motorcycle": 10,
}
DANGEROUS_OBJECTS = {"arma", "arma_blanca", "fusil", "violencia"}
KNN_K = 3
KNN_MIN_REAL_SAMPLES = 3


def analyze_event(request: AnalysisRequest) -> AnalysisResponse:
    score, factors = calculate_risk_score(request)
    risk_level = classify_risk(score)
    decision = decide_action(score, risk_level, request.evento.confianza)

    result = RiskResult(
        risk_level=risk_level,
        risk_score=score,
        nivel_riesgo=risk_level,
        score_riesgo=round(score / 100, 4),
        suspicion_level=risk_level,
        possible_behavior=infer_behavior(request, risk_level),
        factors=factors,
        algorithm="risk_rules_v2_knn_temporal",
    )

    return AnalysisResponse(
        pipeline=[
            "AgentePercepcion",
            "AgenteAnalisis",
            "AgenteRiesgo",
            "AgenteAccion",
            "AgenteMemoria",
            "AgenteInterfazHumana",
        ],
        input=request,
        result=result,
        decision=decision,
    )


def calculate_risk_score(request: AnalysisRequest) -> tuple[int, list[RiskFactor]]:
    event = request.evento
    context = request.contexto
    memory = request.memoria
    factors: list[RiskFactor] = []
    score = 0

    def add(points: int, code: str, detail: str) -> None:
        nonlocal score
        score += points
        factors.append(RiskFactor(code=code, points=points, detail=detail))

    objeto = normalize_label(event.objeto)
    if not objeto:
        add(5, "payload_incompleto", "No se recibio objeto detectable.")
    elif objeto in OBJECT_BASE_SCORES:
        code = "objeto_peligroso" if objeto in DANGEROUS_OBJECTS else "objeto_base"
        add(OBJECT_BASE_SCORES[objeto], code, f"Objeto detectado: {objeto}.")
    else:
        add(8, "objeto_observado", f"Objeto observado sin regla critica: {objeto}.")

    if event.confianza >= 0.9:
        add(10, "alta_confianza", f"Confianza alta: {event.confianza}.")
    elif event.confianza >= 0.7:
        add(5, "confianza_media", f"Confianza aceptable: {event.confianza}.")
    else:
        add(-10, "baja_confianza", f"Confianza baja: {event.confianza}.")

    if is_night(event.hora.hour):
        add(15, "horario_nocturno", "Evento en horario nocturno.")

    if normalize_label(context.iluminacion) in {"baja", "oscura", "low", "dark"}:
        add(10, "baja_iluminacion", "Condicion de baja iluminacion.")

    if memory.alertas_previas_24h >= 2:
        add(15, "historial_alertas", "Alertas recientes en la camara/zona.")
    if memory.eventos_previos_24h >= 10:
        add(8, "historial_eventos", "Actividad reciente alta.")

    knn_score = knn_risk_score(request)
    if knn_score is not None:
        if knn_score >= score + 8:
            points = min(12, max(4, round((knn_score - score) / 4)))
            add(points, "knn_vecinos_riesgo", f"KNN historico sugiere riesgo cercano a {knn_score}.")
        elif knn_score <= score - 20 and objeto not in DANGEROUS_OBJECTS:
            add(-5, "knn_vecinos_bajo_riesgo", f"KNN historico compara con eventos de bajo riesgo: {knn_score}.")

    return max(0, min(score, 100)), factors


def knn_risk_score(request: AnalysisRequest, k: int = KNN_K) -> int | None:
    features = _knn_features(request)
    prototypes = _historical_knn_prototypes(request)
    if len(prototypes) < max(1, min(k, KNN_MIN_REAL_SAMPLES)):
        return None
    distances = [
        (_euclidean_distance(features, prototype_features), score)
        for prototype_features, score in prototypes
    ]
    distances.sort(key=lambda item: item[0])
    nearest = distances[: max(1, k)]
    weighted_total = 0.0
    weight_sum = 0.0
    for distance, score in nearest:
        weight = 1 / (distance + 0.001)
        weighted_total += score * weight
        weight_sum += weight
    return round(weighted_total / weight_sum)


def _historical_knn_prototypes(request: AnalysisRequest) -> list[tuple[list[float], int]]:
    prototypes: list[tuple[list[float], int]] = []
    for sample in request.memoria.knn_samples[:200]:
        if not isinstance(sample, dict):
            continue
        score = _number(sample.get("score"))
        if score is None:
            continue
        features = _knn_features_from_values(
            objeto=sample.get("objeto"),
            confianza=sample.get("confianza"),
            hora=sample.get("hora"),
            contexto=sample.get("contexto") if isinstance(sample.get("contexto"), dict) else {},
            tracking=sample.get("tracking") if isinstance(sample.get("tracking"), dict) else {},
            memoria=sample.get("memoria") if isinstance(sample.get("memoria"), dict) else {},
        )
        prototypes.append((features, round(_clamp(score, 0, 100))))
    return prototypes


def _knn_features(request: AnalysisRequest) -> list[float]:
    return _knn_features_from_values(
        objeto=request.evento.objeto,
        confianza=request.evento.confianza,
        hora=request.evento.hora,
        contexto=request.contexto.model_dump(),
        tracking=request.tracking.model_dump(),
        memoria=request.memoria.model_dump(),
    )


def _knn_features_from_values(
    objeto,
    confianza,
    hora,
    contexto: dict,
    tracking: dict,
    memoria: dict,
) -> list[float]:
    objeto = normalize_label(objeto)
    hour = _hour_from_value(hora)
    illumination = normalize_label(contexto.get("iluminacion"))
    people_count = _number(contexto.get("cantidad_personas")) or 0
    previous_alerts = _number(memoria.get("alertas_previas_24h")) or 0
    previous_events = _number(memoria.get("eventos_previos_24h")) or 0
    speed = _number(tracking.get("velocidad")) or 0
    permanence = _number(tracking.get("permanencia_segundos")) or 0
    erratic = bool(tracking.get("movimiento_erratico"))
    danger = {
        "fusil": 1.0,
        "arma": 0.9,
        "arma_blanca": 0.8,
        "violencia": 0.8,
        "persona_sospechosa": 0.5,
        "multitud": 0.4,
        "persona": 0.1,
        "no_violencia": 0.0,
    }.get(objeto, 0.1)
    return [
        danger,
        _clamp(_number(confianza) or 0, 0, 1),
        1.0 if is_night(hour) else 0.0,
        1.0 if illumination in {"baja", "oscura", "low", "dark"} else 0.0,
        _clamp(previous_alerts / 5, 0, 1),
        _clamp(previous_events / 20, 0, 1),
        _clamp(people_count / 5, 0, 1),
        _clamp(speed / 80, 0, 1),
        _clamp(permanence / 900, 0, 1),
        1.0 if erratic else 0.0,
    ]


def _euclidean_distance(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _number(value) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _hour_from_value(value) -> int:
    if isinstance(value, datetime):
        return value.hour
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
        except ValueError:
            return 12
    return 12


def decide_action(score: int, risk_level: str, confidence: float) -> ActionDecision:
    review_actions = ["CONFIRMAR_AMENAZA", "FALSO_POSITIVO", "REQUIERE_MAS_REVISION"]
    if score >= 90:
        return ActionDecision(
            action="SOLICITAR_VALIDACION_URGENTE",
            accion_tomada="SOLICITAR_VALIDACION_URGENTE",
            priority=10,
            notify=True,
            channels=["telegram_supervisor", "dashboard_realtime"],
            requires_human_review=True,
            human_review_status="PENDIENTE",
            allowed_human_actions=review_actions,
            automation_locked=True,
        )
    if score >= 70:
        return ActionDecision(
            action="SOLICITAR_VALIDACION_HUMANA",
            accion_tomada="SOLICITAR_VALIDACION_HUMANA",
            priority=8,
            notify=True,
            channels=["telegram_supervisor", "dashboard_realtime"],
            requires_human_review=True,
            human_review_status="PENDIENTE",
            allowed_human_actions=review_actions,
            automation_locked=True,
        )
    if score >= 30:
        return ActionDecision(
            action="SOLICITAR_REVISION_HUMANA",
            accion_tomada="SOLICITAR_REVISION_HUMANA",
            priority=5,
            notify=True,
            channels=["telegram_supervisor"],
            requires_human_review=True,
            human_review_status="PENDIENTE",
            allowed_human_actions=review_actions,
            automation_locked=True,
        )

    action = "IGNORAR_BAJA_CONFIANZA" if confidence < 0.5 else "REGISTRAR_EVENTO"
    return ActionDecision(
        action=action,
        accion_tomada=action,
        priority=1 if confidence < 0.5 else 2,
        notify=False,
        channels=[],
        requires_human_review=False,
        human_review_status="NO_REQUERIDA",
        allowed_human_actions=[],
        automation_locked=False,
    )


def classify_risk(score: int) -> str:
    if score >= 90:
        return "CRITICO"
    if score >= 70:
        return "ALTO"
    if score >= 30:
        return "MEDIO"
    return "BAJO"


def infer_behavior(request: AnalysisRequest, risk_level: str) -> str:
    objeto = normalize_label(request.evento.objeto)
    if risk_level in {"CRITICO", "ALTO"} and objeto in DANGEROUS_OBJECTS:
        if objeto == "violencia":
            return "posible_pelea_o_agresion"
        return "posible_amenaza_con_objeto_peligroso"
    if objeto == "multitud":
        return "aglomeracion_observada"
    if objeto == "persona_sospechosa":
        return "persona_conducta_sospechosa"
    if request.memoria.alertas_previas_24h >= 2:
        return "zona_con_alertas_recientes"
    return "evento_observado"


def normalize_label(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_")
    aliases = {
        "pistol": "arma",
        "pistola": "arma",
        "handgun": "arma",
        "firearm": "arma",
        "weapon": "arma",
        "gun": "arma",
        "rifle": "fusil",
        "knife": "arma_blanca",
        "cuchillo": "arma_blanca",
        "scissors": "arma_blanca",
        "cellphone": "cell_phone",
        "mobile_phone": "cell_phone",
        "phone": "cell_phone",
        "nonviolence": "no_violencia",
        "non_violence": "no_violencia",
        "non-violence": "no_violencia",
        "no_violence": "no_violencia",
        "no-violence": "no_violencia",
        "normal": "no_violencia",
        "person": "persona",
        "people": "multitud",
        "crowd": "multitud",
        "pelea": "violencia",
        "fight": "violencia",
        "fighting": "violencia",
        "violence": "violencia",
    }
    return aliases.get(normalized, normalized)


def is_night(hour: int) -> bool:
    return hour >= 22 or hour <= 5
