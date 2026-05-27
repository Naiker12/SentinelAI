from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests

from agente_percepcion.events import DetectionEvent


@dataclass(frozen=True)
class TelegramSendResult:
    sent: bool
    error: str | None = None


class TelegramSupervisorClient:
    def __init__(
        self,
        bot_token: str | None,
        chat_id: str | None,
        timeout_seconds: float = 10,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout_seconds = timeout_seconds

    def send_validation(self, event: DetectionEvent) -> TelegramSendResult:
        if not self.bot_token or not self.chat_id:
            return TelegramSendResult(sent=False, error="Telegram no esta configurado.")
        if not event.analisis:
            return TelegramSendResult(sent=False, error="El evento no tiene analisis.")

        payload = event.to_payload()
        caption = _build_caption(payload)
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Confirmar amenaza", "callback_data": f"sentinel:confirm:{_review_id(payload)}"},
                    {"text": "Falso positivo", "callback_data": f"sentinel:false:{_review_id(payload)}"},
                ],
                [
                    {"text": "Mas revision", "callback_data": f"sentinel:review:{_review_id(payload)}"},
                ],
            ]
        }

        image_path = payload.get("entrada", {}).get("imagen")
        if image_path and Path(str(image_path)).exists():
            return self._send_photo(Path(str(image_path)), caption, reply_markup)
        return self._send_message(caption, reply_markup)

    def _send_photo(
        self,
        image_path: Path,
        caption: str,
        reply_markup: dict,
    ) -> TelegramSendResult:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        try:
            with image_path.open("rb") as image_file:
                response = requests.post(
                    url,
                    data={
                        "chat_id": self.chat_id,
                        "caption": caption,
                        "parse_mode": "HTML",
                        "reply_markup": _json_dumps(reply_markup),
                    },
                    files={"photo": image_file},
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
            return TelegramSendResult(sent=True)
        except requests.RequestException as exc:
            return TelegramSendResult(sent=False, error=str(exc))

    def _send_message(self, text: str, reply_markup: dict) -> TelegramSendResult:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return TelegramSendResult(sent=True)
        except requests.RequestException as exc:
            return TelegramSendResult(sent=False, error=str(exc))


def mark_telegram_evidence(event: DetectionEvent, sent: bool, error: str | None = None) -> None:
    if not event.analisis:
        return
    event.analisis.setdefault("contexto", {})
    event.analisis["contexto"]["telegram_evidencia_enviada"] = sent
    if error:
        event.analisis["contexto"]["telegram_evidencia_error"] = error
    event.analisis.setdefault("persistencia", {})
    event.analisis["persistencia"]["telegram_evidencia_enviada"] = sent
    if error:
        event.analisis["persistencia"]["telegram_evidencia_error"] = error


def _build_caption(payload: dict) -> str:
    entrada = payload.get("entrada", {})
    resultado = payload.get("resultado", {})
    decision = payload.get("decision", {})
    factors = resultado.get("factores", [])[:5]
    factor_lines = "\n".join(
        f"- {_escape_html(item.get('code', 'factor'))}: {_escape_html(item.get('detail', ''))}"
        for item in factors
    )
    lines = [
        f"<b>SentinelAI - Revision { _escape_html(resultado.get('nivel_riesgo', 'BAJO')) }</b>",
        f"Camara: {_escape_html(entrada.get('camara', 'PC-01'))}",
        f"Evento: {_escape_html(entrada.get('objeto', 'unknown'))} ({_escape_html(entrada.get('confianza', 0))})",
        f"Score: {_escape_html(resultado.get('score_riesgo', 0))}",
        f"Accion: {_escape_html(decision.get('accion_tomada', decision.get('accion', 'REGISTRAR_EVENTO')))}",
    ]
    if factor_lines:
        lines.append(f"Factores:\n{factor_lines}")
    return "\n".join(lines)[:1024]


def _review_id(payload: dict) -> str:
    value = (
        payload.get("persistencia", {}).get("review_id")
        or payload.get("decision", {}).get("review_id")
        or "sin_evento"
    )
    safe = "".join(char for char in str(value) if char.isalnum() or char in {"_", "-"})
    return safe[:40] or "sin_evento"


def _escape_html(value) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _json_dumps(value: dict) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)
