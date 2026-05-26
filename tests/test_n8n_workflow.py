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


def test_n8n_test_payloads_are_valid_json() -> None:
    for path in Path("n8n").glob("test_payload_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "objeto" in payload
        assert "confianza" in payload
