"""
Pydantic Schemas for Patient Baseline and Profile Management.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator


class PatientSex(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "OTHER"


class PatientProfileType(str, Enum):
    STANDARD = "standard"
    ATHLETIC = "athletic"
    GERIATRIC = "geriatric"
    HYPERTENSIVE = "hypertensive"
    ICU_BASELINE = "icu_baseline"


class PatientStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISCHARGED = "discharged"
    INACTIVE = "inactive"


class PatientBaseline(BaseModel):
    heart_rate: float = Field(..., ge=40.0, le=140.0, description="Baseline HR in bpm")
    systolic_bp: float = Field(..., ge=70.0, le=200.0, description="Baseline Systolic BP in mmHg")
    diastolic_bp: float = Field(..., ge=40.0, le=120.0, description="Baseline Diastolic BP in mmHg")
    spo2: float = Field(..., ge=85.0, le=100.0, description="Baseline SpO2 percentage")
    temperature: float = Field(..., ge=35.0, le=40.0, description="Baseline Temperature in °C")
    respiratory_rate: float = Field(..., ge=8.0, le=35.0, description="Baseline RR in breaths/min")

    @field_validator("diastolic_bp")
    @classmethod
    def validate_bp_ratio(cls, v: float, info) -> float:
        systolic = info.data.get("systolic_bp")
        if systolic is not None and v >= systolic:
            raise ValueError(f"Diastolic BP ({v}) must be strictly less than Systolic BP ({systolic})")
        return v


class Patient(BaseModel):
    patient_id: str = Field(default_factory=lambda: f"P-{uuid4().hex[:8].upper()}", min_length=1)
    session_id: str = Field(default_factory=lambda: f"SESS-{uuid4().hex[:8].upper()}", min_length=1)
    age: int = Field(..., ge=18, le=100)
    sex: PatientSex = PatientSex.MALE
    profile_type: PatientProfileType = PatientProfileType.STANDARD
    status: PatientStatus = PatientStatus.ACTIVE
    baseline: PatientBaseline
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at", "updated_at")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
