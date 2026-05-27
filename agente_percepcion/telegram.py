from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock

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
        self._review_snapshot_requests: list[str] = []
        self._review_snapshot_lock = Lock()

    def poll_supervisor_callbacks(self, stop_event: Event, interval_seconds: float = 2) -> None:
        if not self.bot_token:
            return

        offset = 0
        while not stop_event.is_set():
            try:
                updates = self._get_updates(offset)
                for update in updates:
                    offset = max(offset, int(update.get("update_id", 0)) + 1)
                    callback = update.get("callback_query")
                    if callback:
                        self._handle_callback(callback)
            except requests.RequestException as exc:
                print(f"Telegram callback polling no disponible: {exc}{_callback_polling_hint(exc)}")
                stop_event.wait(interval_seconds)
            stop_event.wait(interval_seconds)

    def _get_updates(self, offset: int) -> list[dict]:
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        response = requests.get(
            url,
            params={"offset": offset, "timeout": 1, "allowed_updates": '["callback_query"]'},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("result") or [])

    def _handle_callback(self, callback: dict) -> None:
        callback_data = str(callback.get("data") or "")
        parts = callback_data.split(":")
        if len(parts) < 3 or parts[0] != "sentinel":
            return

        action = parts[1]
        review_id = parts[2]
        labels = {
            "confirm": ("CONFIRMADA", "Amenaza confirmada", "ALERTA ACTIVADA"),
            "false": ("FALSO_POSITIVO", "Marcado como falso positivo", "EVENTO CERRADO"),
            "review": ("REQUIERE_MAS_REVISION", "Solicitando nueva captura", "REVISION ADICIONAL"),
        }
        status, text, title = labels.get(action, ("DESCONOCIDA", "Respuesta recibida", "RESPUESTA"))
        self._answer_callback(callback.get("id"), text)
        if action == "review":
            self._queue_review_snapshot(review_id)
        self._send_plain_message(
            "\n".join(
                [
                    f"<b>SentinelAI - {title}</b>",
                    f"Revision: {_escape_html(review_id)}",
                    f"Estado: {_escape_html(status)}",
                    _final_instruction_for(action),
                ]
            )
        )
        print(f"Supervisor Telegram: {review_id} -> {status}")

    def consume_review_snapshot_requests(self) -> list[str]:
        with self._review_snapshot_lock:
            requests_to_send = self._review_snapshot_requests[:]
            self._review_snapshot_requests.clear()
        return requests_to_send

    def _queue_review_snapshot(self, review_id: str) -> None:
        with self._review_snapshot_lock:
            self._review_snapshot_requests.append(review_id)

    def _answer_callback(self, callback_id: str | None, text: str) -> None:
        if not callback_id:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
        response = requests.post(
            url,
            json={"callback_query_id": callback_id, "text": text, "show_alert": False},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

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
        if image_path and str(image_path).startswith(("http://", "https://")):
            return self._send_photo_url(str(image_path), caption, reply_markup)
        if image_path and Path(str(image_path)).exists():
            return self._send_photo(Path(str(image_path)), caption, reply_markup)
        return self._send_message(caption, reply_markup)

    def _send_photo(
        self,
        image_path: Path,
        caption: str,
        reply_markup: dict | None,
    ) -> TelegramSendResult:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        try:
            data = {
                "chat_id": self.chat_id,
                "caption": caption,
                "parse_mode": "HTML",
            }
            if reply_markup:
                data["reply_markup"] = _json_dumps(reply_markup)
            with image_path.open("rb") as image_file:
                response = requests.post(
                    url,
                    data=data,
                    files={"photo": image_file},
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
            return TelegramSendResult(sent=True)
        except requests.RequestException as exc:
            return TelegramSendResult(sent=False, error=str(exc))

    def _send_photo_url(
        self,
        image_url: str,
        caption: str,
        reply_markup: dict,
    ) -> TelegramSendResult:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "photo": image_url,
                    "caption": caption,
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup,
                },
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

    def _send_plain_message(self, text: str) -> TelegramSendResult:
        if not self.bot_token or not self.chat_id:
            return TelegramSendResult(sent=False, error="Telegram no esta configurado.")
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return TelegramSendResult(sent=True)
        except requests.RequestException as exc:
            return TelegramSendResult(sent=False, error=str(exc))

    def send_review_snapshot(self, review_id: str, image_path: str | Path) -> TelegramSendResult:
        caption = "\n".join(
            [
                "<b>SentinelAI - Captura adicional</b>",
                f"Revision: {_escape_html(review_id)}",
                "Esta imagen corresponde a la solicitud de Mas revision.",
            ]
        )
        path = Path(image_path)
        if path.exists():
            return self._send_photo(path, caption, None)
        return TelegramSendResult(sent=False, error=f"No existe la captura: {path}")


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


def _final_instruction_for(action: str) -> str:
    if action == "confirm":
        return "Se debe activar el protocolo definido para amenaza real."
    if action == "false":
        return "Se marca como falso positivo y queda listo para entrenamiento."
    if action == "review":
        return "La camara enviara una nueva captura para analizar mejor la escena."
    return "Revisar manualmente."


def _callback_polling_hint(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    text = getattr(response, "text", "") or str(exc)
    if "webhook" in text.lower() and "getupdates" in text.lower():
        return (
            " El bot tiene un webhook activo, normalmente por Telegram Trigger de n8n. "
            "Usa solo una ruta: desactiva el trigger de n8n para polling Python, "
            "o deja n8n activo y desactiva SENTINEL_TELEGRAM_CALLBACK_POLLING."
        )
    return ""
