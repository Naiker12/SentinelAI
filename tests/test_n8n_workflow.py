from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_agente_analisis_workflow_is_valid_json() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))

    assert workflow["name"] == "AgenteAnalisis"
    assert workflow["active"] is False


def test_agente_analisis_workflow_has_core_nodes() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    node_names = {node["name"] for node in workflow["nodes"]}

    assert "Webhook - Evento Percepcion" in node_names
    assert "Normalizar Evento" in node_names
    assert "AgenteRiesgo - Validar Analisis Python" in node_names
    assert "AgenteAccion - Preparar Respuesta" in node_names
    assert "Requiere Revision Humana?" in node_names
    assert "AgenteInterfazHumana - Preparar Telegram" in node_names
    assert "Telegram Supervisor - Enviar Validacion" in node_names
    assert "Telegram Trigger - Callback Supervisor" in node_names
    assert "Webhook - Callback Telegram Supervisor" in node_names
    assert "AgenteInterfazHumana - Procesar Callback" in node_names
    assert "Telegram Supervisor - Responder Callback" in node_names
    assert "Responder Callback Telegram" in node_names
    assert "Responder a AgentePercepcion" in node_names


def test_agente_analisis_workflow_connections_are_complete() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    connections = workflow["connections"]

    assert "Webhook - Evento Percepcion" in connections
    assert connections["Webhook - Evento Percepcion"]["main"][0][0]["node"] == "Normalizar Evento"
    assert connections["Normalizar Evento"]["main"][0][0]["node"] == "AgenteRiesgo - Validar Analisis Python"
    assert (
        connections["AgenteRiesgo - Validar Analisis Python"]["main"][0][0]["node"]
        == "AgenteAccion - Preparar Respuesta"
    )
    assert (
        connections["AgenteAccion - Preparar Respuesta"]["main"][0][0]["node"]
        == "Requiere Revision Humana?"
    )
    assert connections["Requiere Revision Humana?"]["main"][0][0]["node"] == "Responder a AgentePercepcion"
    assert (
        connections["Requiere Revision Humana?"]["main"][0][1]["node"]
        == "AgenteInterfazHumana - Preparar Telegram"
    )
    assert connections["Requiere Revision Humana?"]["main"][1][0]["node"] == "Responder a AgentePercepcion"
    assert (
        connections["AgenteInterfazHumana - Preparar Telegram"]["main"][0][0]["node"]
        == "Telegram Supervisor - Enviar Validacion"
    )
    assert (
        connections["Webhook - Callback Telegram Supervisor"]["main"][0][0]["node"]
        == "AgenteInterfazHumana - Procesar Callback"
    )
    assert (
        connections["Telegram Trigger - Callback Supervisor"]["main"][0][0]["node"]
        == "AgenteInterfazHumana - Procesar Callback"
    )
    assert (
        connections["AgenteInterfazHumana - Procesar Callback"]["main"][0][0]["node"]
        == "Responder Callback Telegram"
    )
    assert (
        connections["AgenteInterfazHumana - Procesar Callback"]["main"][0][1]["node"]
        == "Telegram Supervisor - Responder Callback"
    )


def test_agente_analisis_workflow_uses_native_telegram_nodes() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    nodes = {node["name"]: node for node in workflow["nodes"]}

    sender = nodes["Telegram Supervisor - Enviar Validacion"]
    trigger = nodes["Telegram Trigger - Callback Supervisor"]

    assert sender["type"] == "n8n-nodes-base.telegram"
    assert trigger["type"] == "n8n-nodes-base.telegramTrigger"
    assert sender["credentials"]["telegramApi"]["name"] == "SentinelAI Telegram Bot"
    assert trigger["credentials"]["telegramApi"]["name"] == "SentinelAI Telegram Bot"
    assert sender["parameters"]["replyMarkup"] == "inlineKeyboard"
    assert "SENTINEL_TELEGRAM_CHAT_ID" in sender["parameters"]["chatId"]


def test_agente_analisis_workflow_returns_persistence_contract() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    code_nodes = {node["name"]: node["parameters"]["jsCode"] for node in workflow["nodes"] if node["type"].endswith(".code")}
    action_code = code_nodes["AgenteAccion - Preparar Respuesta"]

    assert "persistencia" in action_code
    assert "score_riesgo" in action_code
    assert "nivel_riesgo" in action_code
    assert "accion_tomada" in action_code
    assert "detected_at" in action_code
    assert "tracking: data.persistencia?.tracking ?? data.tracking ?? {}" in action_code
    assert "memoria: data.persistencia?.memoria ?? data.memoria ?? {}" in action_code
    assert "review_id" in action_code


def test_agente_analisis_workflow_uses_security_model_base_scores() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    code_nodes = {node["name"]: node["parameters"]["jsCode"] for node in workflow["nodes"] if node["type"].endswith(".code")}
    risk_code = code_nodes["AgenteRiesgo - Validar Analisis Python"]

    assert "risk_rules_v2_knn_temporal" in risk_code
    assert "n8n_orquestador_sin_calculo_riesgo" in risk_code
    assert "Falta resultado de AgenteRiesgo Python" in risk_code


def test_agente_analisis_workflow_normalizes_aliases_to_security_vocab() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    code_nodes = {node["name"]: node["parameters"]["jsCode"] for node in workflow["nodes"] if node["type"].endswith(".code")}
    normalize_code = code_nodes["Normalizar Evento"]

    assert "pistol: 'arma'" in normalize_code
    assert "pistola: 'arma'" in normalize_code
    assert "handgun: 'arma'" in normalize_code
    assert "firearm: 'arma'" in normalize_code
    assert "knife: 'arma_blanca'" in normalize_code
    assert "violence: 'violencia'" in normalize_code


def test_agente_analisis_workflow_accepts_python_precomputed_result() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    code_nodes = {node["name"]: node["parameters"]["jsCode"] for node in workflow["nodes"] if node["type"].endswith(".code")}

    assert "payload.entrada && payload.resultado && payload.decision" in code_nodes["Normalizar Evento"]
    assert "data.resultado && data.decision" in code_nodes["AgenteRiesgo - Validar Analisis Python"]
    assert "data.resultado && data.decision" in code_nodes["AgenteAccion - Preparar Respuesta"]


def test_agente_analisis_workflow_blocks_automation_until_human_review() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    code_nodes = {node["name"]: node["parameters"]["jsCode"] for node in workflow["nodes"] if node["type"].endswith(".code")}
    action_code = code_nodes["AgenteAccion - Preparar Respuesta"]

    assert "requiere_revision_humana" in action_code
    assert "telegram_supervisor_pendiente" in action_code
    assert "estado_revision_humana" in action_code
    assert "automatizacion_bloqueada" in action_code


def test_agente_analisis_workflow_uses_no_tracking_contract() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    code_nodes = {node["name"]: node["parameters"]["jsCode"] for node in workflow["nodes"] if node["type"].endswith(".code")}
    normalize_code = code_nodes["Normalizar Evento"]
    risk_code = code_nodes["AgenteRiesgo - Validar Analisis Python"]
    action_code = code_nodes["AgenteAccion - Preparar Respuesta"]

    assert "cantidad_personas" in normalize_code
    assert "tracking" in normalize_code
    assert "persona_asociada_objeto_peligroso" not in risk_code
    assert "risk_rules_v5_seguridad_multiclase" not in risk_code
    assert "n8n no calcula riesgo" in normalize_code
    assert "interfaz_humana" in action_code


def test_n8n_test_payloads_are_valid_json() -> None:
    for path in Path("n8n").glob("test_payload_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        entrada = payload.get("entrada", payload)
        assert "objeto" in entrada
        assert "confianza" in entrada
        if "resultado" in payload:
            assert "decision" in payload


def test_n8n_ia_code_snippets_are_present() -> None:
    prepare = Path("n8n/code/Preparar_Datos_IA.js")
    parser = Path("n8n/code/Parsear_JSON_LLM.js")
    prompt = Path("n8n/code/SYSTEM_PROMPT_AGENTE_ANALISIS_IA.md")
    risk = Path("n8n/code/Calcular_Riesgo_Code.js")
    memory = Path("n8n/code/Preparar_Memoria_Sheets.js")
    telegram = Path("n8n/code/Preparar_Alerta_Telegram.js")
    supervisor = Path("n8n/code/Procesar_Respuesta_Supervisor_Telegram.js")
    responder = Path("n8n/code/Responder_Webhook_Final.js")
    guide = Path("n8n/FLUJO_IA_RIESGO.md")

    assert prepare.exists()
    assert parser.exists()
    assert prompt.exists()
    assert risk.exists()
    assert memory.exists()
    assert telegram.exists()
    assert supervisor.exists()
    assert responder.exists()
    assert guide.exists()
    assert "prompt_ia" in prepare.read_text(encoding="utf-8")
    assert "payload.entrada && payload.resultado && payload.decision" in prepare.read_text(encoding="utf-8")
    assert "parsed.resultado && parsed.decision && parsed.persistencia" in risk.read_text(encoding="utf-8")
    assert 'pistol: "arma"' in prepare.read_text(encoding="utf-8")
    assert 'pistol: "arma"' in risk.read_text(encoding="utf-8")
    assert 'fusil: 95' in prepare.read_text(encoding="utf-8")
    assert "risk_rules_v2_plus_llm_guarded" in parser.read_text(encoding="utf-8")
    assert "risk_rules_v3_history_llm_guarded" in risk.read_text(encoding="utf-8")
    assert "score_riesgo" in memory.read_text(encoding="utf-8")
    assert "inline_keyboard" in telegram.read_text(encoding="utf-8")
    assert "sentinel:confirm" in telegram.read_text(encoding="utf-8")
    assert "review_id" in telegram.read_text(encoding="utf-8")
    assert "human_label" in supervisor.read_text(encoding="utf-8")
    assert "answer_callback_query" in supervisor.read_text(encoding="utf-8")
    assert "telegram_followup" in supervisor.read_text(encoding="utf-8")
    assert "request_new_capture" in supervisor.read_text(encoding="utf-8")
    assert "Alerta_Final_Telegram" in guide.read_text(encoding="utf-8")
    assert "Supervisor Humano" in guide.read_text(encoding="utf-8")
    assert "Responde solo JSON valido" in prompt.read_text(encoding="utf-8")


def test_n8n_ia_code_snippets_have_valid_javascript_syntax() -> None:
    for path in [
        Path("n8n/code/Preparar_Datos_IA.js"),
        Path("n8n/code/Parsear_JSON_LLM.js"),
        Path("n8n/code/Calcular_Riesgo_Code.js"),
        Path("n8n/code/Preparar_Memoria_Sheets.js"),
        Path("n8n/code/Preparar_Alerta_Telegram.js"),
        Path("n8n/code/Procesar_Respuesta_Supervisor_Telegram.js"),
        Path("n8n/code/Responder_Webhook_Final.js"),
    ]:
        result = subprocess.run(
            ["node", "--check", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
