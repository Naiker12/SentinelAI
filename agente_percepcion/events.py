from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone

import requests

from agente_analisis.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    MemoryContext,
    PerceptionEvent,
    SceneContext,
    TrackingContext,
)
from agente_percepcion.detector import Detection, normalize_label


@dataclass(frozen=True)
class DetectionEvent:
    objeto: str
    confianza: float
    hora: str
    camara: str
    riesgo: str
    box: tuple[int, int, int, int]
    imagen: str | None = None
    contexto: dict | None = None
    tracking: dict | None = None
    memoria: dict | None = None
    analisis: dict | None = None

    @classmethod
    def from_detection(
        cls,
        detection: Detection,
        camera_name: str,
        image_path: str | None = None,
        contexto: dict | None = None,
        tracking: dict | None = None,
        memoria: dict | None = None,
    ) -> "DetectionEvent":
        return cls(
            objeto=detection.label,
            confianza=detection.confidence,
            hora=datetime.now(timezone.utc).isoformat(),
            camara=camera_name,
            riesgo=risk_for_label(detection.label),
            box=detection.box,
            imagen=image_path,
            contexto=contexto,
            tracking=tracking,
            memoria=memoria,
        )

    def to_payload(self) -> dict:
        if self.analisis:
            return self.analisis
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}

    def to_analysis_request(self) -> AnalysisRequest:
        return AnalysisRequest(
            evento=PerceptionEvent(
                objeto=self.objeto,
                confianza=self.confianza,
                hora=datetime.fromisoformat(self.hora.replace("Z", "+00:00")),
                camara=self.camara,
                box=list(self.box),
                imagen=self.imagen,
            ),
            contexto=SceneContext(**(self.contexto or {})),
            tracking=TrackingContext(**(self.tracking or {})),
            memoria=MemoryContext(**(self.memoria or {})),
        )

    def with_analysis(self, response: AnalysisResponse) -> "DetectionEvent":
        return replace(self, analisis=_analysis_to_orchestrator_payload(self, response))

    def to_supabase_row(self, analysis_response: dict | list | str | None = None) -> dict:
        enriched = _extract_persistence(analysis_response)
        context = self.contexto or {}
        if self.tracking:
            context = {**context, "tracking": self.tracking}
        if self.memoria:
            context = {**context, "memoria": self.memoria}
        if enriched.get("contexto"):
            context = {**context, **enriched["contexto"]}
        if enriched.get("tracking"):
            context = {**context, "tracking": enriched["tracking"]}
        if enriched.get("memoria"):
            context = {**context, "memoria": enriched["memoria"]}
        if enriched.get("resumen_ia"):
            context = {**context, "resumen_ia": enriched["resumen_ia"]}
        if enriched.get("factores_ia"):
            context = {**context, "factores_ia": enriched["factores_ia"]}
        for key in (
            "requiere_revision_humana",
            "estado_revision_humana",
            "automatizacion_bloqueada",
            "review_id",
        ):
            if key in enriched:
                context = {**context, key: enriched[key]}

        detected_at = enriched.get("detected_at") or self.hora
        risk_level = str(enriched.get("nivel_riesgo") or self.riesgo).upper()
        score = enriched.get("score_riesgo")
        action = enriched.get("accion_tomada")
        previous_alerts = enriched.get("alertas_previas_24h")

        return {
            "objeto": self.objeto,
            "confianza": self.confianza,
            "riesgo": self.riesgo.upper(),
            "detected_at": detected_at,
            "camara_id": self.camara,
            "box": list(self.box),
            "imagen_url": self.imagen,
            "score_riesgo": score,
            "nivel_riesgo": risk_level,
            "accion_tomada": action,
            "alertas_previas_24h": previous_alerts or 0,
            "hora_dia": _hour_from_isoformat(detected_at),
            "contexto": context or None,
        }


class SupabaseEventStore:
    def __init__(self, supabase_url: str | None, service_role_key: str | None, table: str) -> None:
        if not supabase_url or not service_role_key:
            raise RuntimeError(
                "Faltan SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en el archivo .env."
            )

        from supabase import create_client

        self._client = create_client(supabase_url, service_role_key)
        self._table = table

    def save(self, event: DetectionEvent, analysis_response: dict | list | str | None = None) -> None:
        self._client.table(self._table).insert(event.to_supabase_row(analysis_response)).execute()

    def latest(self, limit: int = 50) -> list[dict]:
        response = (
            self._client.table(self._table)
            .select("*")
            .order("detected_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])


@dataclass(frozen=True)
class N8nResult:
    sent: bool
    status_code: int | None = None
    response: dict | list | str | None = None
    error: str | None = None


class N8nClient:
    def __init__(
        self,
        webhook_url: str | None,
        timeout_seconds: float = 5,
        allow_test_webhook: bool = False,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        self.allow_test_webhook = allow_test_webhook

    def send(self, event: DetectionEvent) -> N8nResult:
        if not self.webhook_url:
            return N8nResult(sent=False, error="SENTINEL_N8N_WEBHOOK_URL no esta configurado.")
        if "/webhook-test/" in self.webhook_url and not self.allow_test_webhook:
            return N8nResult(
                sent=False,
                error=(
                    "La camara esta usando una URL de prueba de n8n. "
                    "Cambia SENTINEL_N8N_WEBHOOK_URL a "
                    f"{self.webhook_url.replace('/webhook-test/', '/webhook/')} "
                    "y activa el workflow."
                ),
            )

        try:
            response = requests.post(
                self.webhook_url,
                json=event.to_payload(),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return N8nResult(
                sent=True,
                status_code=response.status_code,
                response=_parse_response(response),
            )
        except requests.HTTPError as exc:
            hint = ""
            if exc.response is not None and exc.response.status_code == 404:
                hint = (
                    " Revisa que el workflow este activo y que el path del Webhook sea "
                    "'sentinel-analysis'."
                )
            return N8nResult(sent=False, error=f"{exc}{hint}")
        except requests.RequestException as exc:
            return N8nResult(sent=False, error=str(exc))


def risk_for_label(label: str) -> str:
    normalized = normalize_label(label)
    high_risk = {"knife", "scissors", "gun", "violence"}

    if normalized in high_risk:
        return "alto"
    return "bajo"


def _parse_response(response: requests.Response) -> dict | list | str | None:
    if not response.text:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


def _extract_persistence(response: dict | list | str | None) -> dict:
    if isinstance(response, list) and response:
        response = response[0]
    if not isinstance(response, dict):
        return {}
    if isinstance(response.get("persistencia"), dict):
        return response["persistencia"]
    return {}


def _analysis_to_orchestrator_payload(event: DetectionEvent, response: AnalysisResponse) -> dict:
    result = response.result
    decision = response.decision
    tracking = event.tracking or {}
    memory = event.memoria or {}
    context = event.contexto or {}
    score_riesgo = result.score_riesgo
    risk = result.nivel_riesgo
    action = decision.accion_tomada

    entrada = {
        "objeto": normalize_label(event.objeto).replace(" ", "_"),
        "confianza": event.confianza,
        "camara": event.camara,
        "hora": event.hora,
        "box": list(event.box),
        "imagen": event.imagen,
    }

    return {
        "status": response.status,
        "agente": "AgenteAnalisis",
        "version": "0.2.0",
        "pipeline": response.pipeline,
        "entrada": entrada,
        "contexto": context,
        "tracking": tracking,
        "memoria": memory,
        "resultado": {
            "riesgo": risk,
            "nivel_riesgo": risk,
            "severidad": "CRITICA" if risk == "CRITICO" else risk,
            "score": result.risk_score,
            "score_riesgo": score_riesgo,
            "factores": [factor.model_dump(mode="json") for factor in result.factors],
            "comportamiento_posible": result.possible_behavior,
            "algoritmo": result.algorithm,
        },
        "decision": {
            "accion": decision.action,
            "accion_tomada": action,
            "prioridad": decision.priority,
            "notificar": decision.notify,
            "canales": decision.channels,
            "guardar_en_supabase": decision.store_in_supabase,
            "requiere_revision_humana": decision.requires_human_review,
            "estado_revision_humana": decision.human_review_status,
            "acciones_humanas_permitidas": decision.allowed_human_actions,
            "automatizacion_bloqueada": decision.automation_locked,
        },
        "persistencia": {
            "camara_id": event.camara,
            "objeto": normalize_label(event.objeto).replace(" ", "_"),
            "confianza": event.confianza,
            "score_riesgo": score_riesgo,
            "nivel_riesgo": risk,
            "accion_tomada": action,
            "alertas_previas_24h": memory.get("alertas_previas_24h", 0),
            "detected_at": event.hora,
            "box": list(event.box),
            "contexto": context,
            "tracking": tracking,
            "memoria": memory,
            "requiere_revision_humana": decision.requires_human_review,
            "estado_revision_humana": decision.human_review_status,
            "review_id": _review_id(event),
        },
        "mensaje": f"{action}: {risk} con score {score_riesgo}",
        "procesado_en": response.processed_at.isoformat(),
    }


def _hour_from_isoformat(value: str) -> int | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
    except ValueError:
        return None


def _review_id(event: DetectionEvent) -> str:
    normalized_object = normalize_label(event.objeto).replace(" ", "_")
    timestamp = event.hora.replace(":", "").replace("-", "").replace(".", "")
    safe_camera = event.camara.replace(" ", "_")
    return f"{safe_camera}_{normalized_object}_{timestamp}"[:64]
