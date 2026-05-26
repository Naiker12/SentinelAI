from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests

from agente_percepcion.detector import Detection


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
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}

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
    def __init__(self, webhook_url: str | None, timeout_seconds: float = 5) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def send(self, event: DetectionEvent) -> N8nResult:
        if not self.webhook_url:
            return N8nResult(sent=False, error="SENTINEL_N8N_WEBHOOK_URL no esta configurado.")
        if "/webhook-test/" in self.webhook_url:
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
    normalized = label.strip().lower().replace("_", " ")
    high_risk = {"knife", "scissors", "gun"}

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


def _hour_from_isoformat(value: str) -> int | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
    except ValueError:
        return None
