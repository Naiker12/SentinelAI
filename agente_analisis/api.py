from __future__ import annotations

from fastapi import FastAPI

from agente_analisis.risk_engine import analyze_event
from agente_analisis.schemas import AnalysisRequest, AnalysisResponse


app = FastAPI(title="SentinelAI AgenteAnalisis", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "AgenteAnalisis"}


@app.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest) -> AnalysisResponse:
    return analyze_event(request)
