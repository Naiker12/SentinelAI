from __future__ import annotations

from agente_analisis.schemas import (
    ActionDecision,
    AnalysisRequest,
    AnalysisResponse,
    RiskFactor,
    RiskResult,
)


DANGEROUS_OBJECTS = {"knife", "gun", "scissors"}
RELEVANT_OBJECTS = {"person", "car", "truck", "motorcycle", "backpack", "cell_phone"}


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
    )

    return AnalysisResponse(
        pipeline=[
            "AgentePercepcion",
            "AgenteTracking",
            "AgenteAnalisis",
            "AgenteRiesgo",
            "AgenteAccion",
            "AgenteMemoria",
        ],
        input=request,
        result=result,
        decision=decision,
    )


def calculate_risk_score(request: AnalysisRequest) -> tuple[int, list[RiskFactor]]:
    event = request.evento
    context = request.contexto
    tracking = request.tracking
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
    elif objeto in DANGEROUS_OBJECTS:
        add(70 if objeto == "gun" else 55, "objeto_peligroso", f"Objeto peligroso: {objeto}.")
    elif objeto in RELEVANT_OBJECTS:
        add(20, "objeto_relevante", f"Objeto relevante: {objeto}.")
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

    if tracking.velocidad >= 7:
        add(12, "movimiento_rapido", f"Velocidad elevada: {tracking.velocidad}.")
    if tracking.movimiento_erratico:
        add(15, "movimiento_erratico", "Movimiento erratico reportado.")
    if tracking.permanencia_segundos >= 900:
        add(25, "permanencia_sospechosa", "Permanencia mayor o igual a 15 minutos.")
    elif tracking.permanencia_segundos >= 300:
        add(10, "permanencia_media", "Permanencia mayor o igual a 5 minutos.")

    if memory.alertas_previas_24h >= 2:
        add(15, "historial_alertas", "Alertas recientes en la camara/zona.")
    if memory.eventos_previos_24h >= 10:
        add(8, "historial_eventos", "Actividad reciente alta.")

    return max(0, min(score, 120)), factors


def decide_action(score: int, risk_level: str, confidence: float) -> ActionDecision:
    if score >= 101:
        return ActionDecision(
            action="ALERTA_CRITICA",
            accion_tomada="ALERTA_CRITICA",
            priority=10,
            notify=True,
            channels=["telegram", "dashboard_realtime"],
            requires_human_review=True,
        )
    if score >= 61:
        return ActionDecision(
            action="ENVIAR_ALERTA",
            accion_tomada="ENVIAR_ALERTA",
            priority=8,
            notify=True,
            channels=["dashboard_realtime"],
            requires_human_review=True,
        )
    if score >= 31:
        return ActionDecision(
            action="MONITOREAR",
            accion_tomada="MONITOREAR",
            priority=5,
            notify=False,
            channels=[],
            requires_human_review=False,
        )

    action = "IGNORAR_BAJA_CONFIANZA" if confidence < 0.5 else "REGISTRAR_EVENTO"
    return ActionDecision(
        action=action,
        accion_tomada=action,
        priority=1 if confidence < 0.5 else 2,
        notify=False,
        channels=[],
        requires_human_review=False,
    )


def classify_risk(score: int) -> str:
    if score >= 101:
        return "CRITICO"
    if score >= 61:
        return "ALTO"
    if score >= 31:
        return "MEDIO"
    return "BAJO"


def infer_behavior(request: AnalysisRequest, risk_level: str) -> str:
    objeto = normalize_label(request.evento.objeto)
    if risk_level in {"CRITICO", "ALTO"} and objeto in DANGEROUS_OBJECTS:
        return "posible_amenaza_con_objeto_peligroso"
    if request.tracking.permanencia_segundos >= 900:
        return "posible_merodeo"
    if request.tracking.movimiento_erratico:
        return "movimiento_anomalo"
    return "evento_observado"


def normalize_label(value: str | None) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def is_night(hour: int) -> bool:
    return hour >= 22 or hour <= 5
