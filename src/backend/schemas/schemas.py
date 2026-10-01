from datetime import datetime
from typing import List, Literal, Optional, Any
from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Legacy / Simple Schemas (maintained for existing API & test compatibility)
# ---------------------------------------------------------------------------
class PatientBase(BaseModel):
    name: str = Field(..., description="Patient's full name")
    age: int = Field(..., ge=0, description="Patient's age")
    medical_history: Optional[List[str]] = []

class PatientCreateLegacy(PatientBase):
    pass

class Patient(PatientBase):
    id: str
    class Config:
        from_attributes = True

class Vital(BaseModel):
    heart_rate: float
    blood_pressure: str
    temperature: float
    oxygen_saturation: float
    timestamp: str

class RiskAssessment(BaseModel):
    patient_id: str
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: str
    factors: List[str]

class Alert(BaseModel):
    alert_id: str
    patient_id: str
    severity: str
    message: str
    timestamp: str

class Explanation(BaseModel):
    patient_id: str
    feature_importance: dict
    summary: str

# ---------------------------------------------------------------------------
# Production Runtime Schemas (consolidated from deployment/backend/app)
# ---------------------------------------------------------------------------
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

    @model_validator(mode='before')
    @classmethod
    def alias_vitals(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'temperature' in data and 'temperature_c' not in data:
                data['temperature_c'] = data.pop('temperature')
            if ('map' not in data or data['map'] is None) and ('bp_systolic' in data and 'bp_diastolic' in data):
                sbp = data.get('bp_systolic')
                dbp = data.get('bp_diastolic')
                if sbp is not None and dbp is not None:
                    try:
                        data['map'] = float(dbp) + (float(sbp) - float(dbp)) / 3.0
                    except (ValueError, TypeError):
                        pass
        return data


class PredictionResponse(BaseModel):
    patient_id: str
    prediction_timestamp: datetime
    prediction_horizon_hours: int = 6
    risk_probability: float
    uncertainty_interval: tuple[float, float] | None = None
    uncertainty_summary: dict | None = None
    confidence: Literal['HIGH', 'MEDIUM', 'LOW']
    signal_quality: Literal['HIGH', 'MEDIUM', 'LOW']
    alert_severity: str | None
    recommended_clinical_review_level: str
    contributing_factors: list[str]
    shap_explanation: dict | None = None
    alert: dict | None = None
    latency_ms: float
    model_version: str
    is_demo_model: bool

class SimulatorRequest(BaseModel):
    patient_count: int = Field(default=3, ge=1, le=25)
    duration_minutes: int = Field(default=60, ge=1, le=720)
    cadence_seconds: int = Field(default=5, ge=1, le=60)

class EventEnvelope(BaseModel):
    type: Literal['vital_event', 'prediction', 'alert', 'simulator_status', 'error']
    occurred_at: datetime
    patient_id: str | None = None
    payload: dict

class PatientCreate(BaseModel):
    patient_id: str = Field(default="", min_length=0, max_length=64)
    name: Optional[str] = None
    age: Optional[int] = None
    medical_history: Optional[List[str]] = []
    source_system: str = Field(default='local', max_length=32)
    sex_at_birth: str | None = Field(default=None, max_length=16)
    birth_year: int | None = Field(default=None, ge=1850, le=2100)

class PatientResponse(BaseModel):
    patient_id: str
    source_system: str
    sex_at_birth: str | None = None
    birth_year: int | None = None
    created_at: datetime

class VitalResponse(VitalEvent):
    pass

class TrajectoryPoint(BaseModel):
    timestamp: datetime
    risk_probability: float
    alert_severity: str | None = None

class TrajectoryResponse(BaseModel):
    patient_id: str
    points: list[TrajectoryPoint]

class ExplanationResponse(BaseModel):
    patient_id: str
    prediction_timestamp: datetime
    contributing_factors: list[str]
    disclaimer: str = 'Factors contributed to the model prediction; they are not causal claims.'

class AlertResponse(BaseModel):
    timestamp: datetime
    severity: str
    status: str = 'emitted'
    reason: list[str] = []

class ModelVersionResponse(BaseModel):
    model_version: str
    is_demo_model: bool
    prediction_horizon_hours: int = 6
