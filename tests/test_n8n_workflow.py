from __future__ import annotations

import json
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
    assert "AgenteRiesgo - Score Hibrido" in node_names
    assert "AgenteAccion - Preparar Respuesta" in node_names
    assert "Responder a AgentePercepcion" in node_names


def test_agente_analisis_workflow_connections_are_complete() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    connections = workflow["connections"]

    assert "Webhook - Evento Percepcion" in connections
    assert connections["Webhook - Evento Percepcion"]["main"][0][0]["node"] == "Normalizar Evento"
    assert connections["Normalizar Evento"]["main"][0][0]["node"] == "AgenteRiesgo - Score Hibrido"
    assert (
        connections["AgenteRiesgo - Score Hibrido"]["main"][0][0]["node"]
        == "AgenteAccion - Preparar Respuesta"
    )
    assert (
        connections["AgenteAccion - Preparar Respuesta"]["main"][0][0]["node"]
        == "Responder a AgentePercepcion"
    )


def test_agente_analisis_workflow_returns_persistence_contract() -> None:
    workflow = json.loads(Path("n8n/AgenteAnalisis.workflow.json").read_text(encoding="utf-8"))
    code_nodes = {node["name"]: node["parameters"]["jsCode"] for node in workflow["nodes"] if node["type"].endswith(".code")}
    action_code = code_nodes["AgenteAccion - Preparar Respuesta"]

    assert "persistencia" in action_code
    assert "score_riesgo" in action_code
    assert "nivel_riesgo" in action_code
    assert "accion_tomada" in action_code
    assert "detected_at" in action_code


def test_n8n_test_payloads_are_valid_json() -> None:
    for path in Path("n8n").glob("test_payload_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "objeto" in payload
        assert "confianza" in payload
