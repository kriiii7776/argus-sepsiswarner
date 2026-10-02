"""
ARGUS Data Contract v1.0 Pydantic Schemas.

Defines the exact payload contracts exchanged between ARGUS Part 1 and consumers.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    VITAL_UPDATE = "vital_update"
    PATIENT_EVENT = "patient_event"
    SENSOR_EVENT = "sensor_event"
    SIMULATION_EVENT = "simulation_event"
    CLINICAL_UPDATE = "clinical_update"


class DataSource(str, Enum):
    SYNTHETIC = "synthetic"
    CSV_REPLAY = "csv_replay"
    MIMIC_IV = "mimic_iv"


class QualityStatus(str, Enum):
    VALID = "valid"
    MISSING = "missing"
    SENSOR_UNAVAILABLE = "sensor_unavailable"
    DELAYED = "delayed"
    STALE = "stale"
    INVALID = "invalid"
    DISCONNECTED = "disconnected"
    RECONNECTED = "reconnected"


class ScenarioState(str, Enum):
    STABLE = "stable"
    GRADUAL_DETERIORATION = "gradual_deterioration"
    RAPID_DETERIORATION = "rapid_deterioration"
    RECOVERY = "recovery"
    NOISY = "noisy"
    SENSOR_FAILURE = "sensor_failure"
    DATA_QUALITY_PROBLEM = "data_quality_problem"


class VitalUnits(BaseModel):
    heart_rate: str = "bpm"
    systolic_bp: str = "mmHg"
    diastolic_bp: str = "mmHg"
    spo2: str = "%"
    temperature: str = "°C"
    respiratory_rate: str = "breaths/min"


class VitalSignSet(BaseModel):
    heart_rate: Optional[float] = Field(None, ge=0.0, le=300.0, description="Heart rate in bpm")
    systolic_bp: Optional[float] = Field(None, ge=0.0, le=300.0, description="Systolic BP in mmHg")
    diastolic_bp: Optional[float] = Field(None, ge=0.0, le=300.0, description="Diastolic BP in mmHg")
    spo2: Optional[float] = Field(None, ge=0.0, le=100.0, description="SpO2 percentage")
    temperature: Optional[float] = Field(None, ge=20.0, le=45.0, description="Temperature in °C")
    respiratory_rate: Optional[float] = Field(None, ge=0.0, le=100.0, description="Respiratory rate in breaths/min")


class BaseMessage(BaseModel):
    schema_version: str = Field("1.0", description="Contract version")
    message_type: MessageType = Field(..., description="Message type classification")
    patient_id: str = Field(..., min_length=1, description="Stable patient identifier")
    session_id: str = Field(..., min_length=1, description="Simulation session identifier")
    source: str = Field("synthetic", description="Data source indicator")
    timestamp: datetime = Field(..., description="Wall-clock emission time in UTC")
    simulation_time: datetime = Field(..., description="Simulated virtual time in UTC")

    @field_validator("timestamp", "simulation_time")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class VitalUpdateMessage(BaseMessage):
    message_type: Literal[MessageType.VITAL_UPDATE] = MessageType.VITAL_UPDATE
    vitals: VitalSignSet
    vital_units: VitalUnits = Field(default_factory=VitalUnits)
    quality_status: QualityStatus = QualityStatus.VALID
    scenario_state: ScenarioState = ScenarioState.STABLE


class PatientEventMessage(BaseMessage):
    message_type: Literal[MessageType.PATIENT_EVENT] = MessageType.PATIENT_EVENT
    event_name: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class SensorEventMessage(BaseMessage):
    message_type: Literal[MessageType.SENSOR_EVENT] = MessageType.SENSOR_EVENT
    sensor_type: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    details: Optional[str] = None


class SimulationEventMessage(BaseMessage):
    message_type: Literal[MessageType.SIMULATION_EVENT] = MessageType.SIMULATION_EVENT
    event_type: str = Field(..., min_length=1)
    previous_state: Optional[ScenarioState] = None
    new_state: Optional[ScenarioState] = None
    speed_factor: Optional[float] = Field(1.0, ge=0.0)


class ClinicalContext(BaseModel):
    """Lower-frequency observations supplied by the EHR/laboratory stream."""

    platelets: Optional[float] = Field(None, ge=0, description="Platelet count, 10^9/L")
    bilirubin: Optional[float] = Field(None, ge=0, description="Total bilirubin, mg/dL")
    creatinine: Optional[float] = Field(None, ge=0, description="Creatinine, mg/dL")
    lactate: Optional[float] = Field(None, ge=0, description="Lactate, mmol/L")
    pao2_fio2_ratio: Optional[float] = Field(None, ge=0, description="PaO2/FiO2 ratio")
    glasgow_coma_scale: Optional[int] = Field(None, ge=3, le=15)
    urine_output_6h: Optional[float] = Field(None, ge=0, description="Urine output over six hours, mL")
    norepinephrine_dose: Optional[float] = Field(None, ge=0, description="Norepinephrine equivalent, mcg/kg/min")


class ClinicalContextUnits(BaseModel):
    platelets: str = "10^9/L"
    bilirubin: str = "mg/dL"
    creatinine: str = "mg/dL"
    lactate: str = "mmol/L"
    pao2_fio2_ratio: str = "mmHg"
    glasgow_coma_scale: str = "score"
    urine_output_6h: str = "mL/6h"
    norepinephrine_dose: str = "mcg/kg/min"


class ClinicalUpdateMessage(BaseMessage):
    """An EHR/laboratory update. Consumers must use the as-of timestamp, not future results."""

    message_type: Literal[MessageType.CLINICAL_UPDATE] = MessageType.CLINICAL_UPDATE
    clinical_context: ClinicalContext
    clinical_units: ClinicalContextUnits = Field(default_factory=ClinicalContextUnits)
    recorded_at: datetime = Field(..., description="When this result became available on the simulation timeline")
    clinical_observation_times: Dict[str, Optional[datetime]] = Field(
        default_factory=dict,
        description="Original source observation time for each clinical field; null means not available.",
    )
    data_origin: str = Field("demo_replay", description="Origin of the replayed clinical record")


class APIErrorPayload(BaseModel):
    code: str = Field(..., min_length=1, description="Machine-readable error code")
    message: str = Field(..., min_length=1, description="Human-readable error description")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context or diagnostics")
    timestamp: datetime = Field(..., description="UTC timestamp of error occurrence")

    @field_validator("timestamp")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class APIErrorResponse(BaseModel):
    error: APIErrorPayload
