from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["BAJO", "MEDIO", "ALTO", "CRITICO", "DESCONOCIDO"]


class PerceptionEvent(BaseModel):
    objeto: str = Field(default="", description="Objeto detectado por YOLO.")
    confianza: float = Field(default=0.0, ge=0.0, le=1.0)
    hora: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    camara: str = "PC-01"
    box: list[int] | None = None
    imagen: str | None = None


class TrackingContext(BaseModel):
    person_id: str | None = None
    velocidad: float = 0.0
    permanencia_segundos: int = 0
    movimiento_erratico: bool = False
    patron_movimiento: str | None = None


class SceneContext(BaseModel):
    zona: str = "sin_zona"
    iluminacion: str = "desconocida"
    cantidad_personas: int = 0


class MemoryContext(BaseModel):
    eventos_previos_24h: int = 0
    alertas_previas_24h: int = 0


class AnalysisRequest(BaseModel):
    evento: PerceptionEvent
    contexto: SceneContext = Field(default_factory=SceneContext)
    tracking: TrackingContext = Field(default_factory=TrackingContext)
    memoria: MemoryContext = Field(default_factory=MemoryContext)


class RiskFactor(BaseModel):
    code: str
    points: int
    detail: str


class RiskResult(BaseModel):
    risk_level: RiskLevel
    risk_score: int
    suspicion_level: RiskLevel
    possible_behavior: str
    factors: list[RiskFactor]
    algorithm: str = "risk_rules_v1"


class ActionDecision(BaseModel):
    action: str
    priority: int
    notify: bool
    channels: list[str]
    store_in_supabase: bool = True
    requires_human_review: bool


class AnalysisResponse(BaseModel):
    status: str = "procesado"
    agent: str = "AgenteAnalisis"
    version: str = "0.1.0"
    pipeline: list[str]
    input: AnalysisRequest
    result: RiskResult
    decision: ActionDecision
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
