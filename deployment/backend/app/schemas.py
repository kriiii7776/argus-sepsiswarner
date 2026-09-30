from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class VitalEvent(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    heart_rate: float | None = Field(default=None, ge=0, le=400)
    map: float | None = Field(default=None, ge=0, le=300)
    resp_rate: float | None = Field(default=None, ge=0, le=100)
    spo2: float | None = Field(default=None, ge=0, le=100)
    temperature_c: float | None = Field(default=None, ge=20, le=50)
    lactate: float | None = Field(default=None, ge=0, le=30)
    source: Literal['simulator', 'integration'] = 'simulator'

class PredictionResponse(BaseModel):
    patient_id: str; prediction_timestamp: datetime; prediction_horizon_hours: int = 6
    risk_probability: float; uncertainty_interval: tuple[float, float]; confidence: Literal['HIGH','MEDIUM','LOW']
    signal_quality: Literal['HIGH','MEDIUM','LOW']; alert_severity: str | None
    recommended_clinical_review_level: str; contributing_factors: list[str]; latency_ms: float
    model_version: str; is_demo_model: bool

class SimulatorRequest(BaseModel):
    patient_count: int = Field(default=3, ge=1, le=25)
    duration_minutes: int = Field(default=60, ge=1, le=720)
    cadence_seconds: int = Field(default=5, ge=1, le=60)

class EventEnvelope(BaseModel):
    type: Literal['vital_event','prediction','alert','simulator_status','error']
    occurred_at: datetime
    patient_id: str | None = None
    payload: dict

class PatientCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    source_system: str = Field(default='local', max_length=32)
    sex_at_birth: str | None = Field(default=None, max_length=16)
    birth_year: int | None = Field(default=None, ge=1850, le=2100)
class PatientResponse(PatientCreate):
    created_at: datetime
class VitalResponse(VitalEvent): pass
class TrajectoryPoint(BaseModel):
    timestamp: datetime; risk_probability: float; alert_severity: str | None = None
class TrajectoryResponse(BaseModel):
    patient_id: str; points: list[TrajectoryPoint]
class ExplanationResponse(BaseModel):
    patient_id: str; prediction_timestamp: datetime; contributing_factors: list[str]
    disclaimer: str = 'Factors contributed to the model prediction; they are not causal claims.'
class AlertResponse(BaseModel):
    timestamp: datetime; severity: str; status: str = 'emitted'; reason: list[str] = []
class ModelVersionResponse(BaseModel):
    model_version: str; is_demo_model: bool; prediction_horizon_hours: int = 6
