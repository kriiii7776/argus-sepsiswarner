"""
Pydantic schemas for REST Control API requests and responses.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.patient import (
    Patient,
    PatientProfileType,
    PatientSex,
    PatientStatus,
)
from app.simulation.clock import ClockState, SimulationClockStatus
from app.simulation.scenario_engine import ScenarioEngineState, ScenarioName


class PatientCreateRequest(BaseModel):
    patient_id: Optional[str] = Field(None, description="Optional custom patient identifier")
    session_id: Optional[str] = Field(None, description="Optional simulation session identifier")
    age: Optional[int] = Field(None, ge=18, le=100, description="Patient age in years")
    sex: Optional[PatientSex] = Field(None, description="Patient sex ('M', 'F', 'OTHER')")
    profile_type: PatientProfileType = Field(PatientProfileType.STANDARD, description="Baseline profile distribution")
    seed: Optional[int] = Field(None, description="Random seed for reproducible baseline generation")


class PatientScenarioRequest(BaseModel):
    scenario_name: ScenarioName = Field(..., description="Target scenario state-machine name")


class SimulationStartRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Session ID to run")
    patient_id: Optional[str] = Field(None, description="Patient ID to attach to session")
    speed_factor: float = Field(1.0, ge=0.1, le=100.0, description="Initial simulation clock speed multiplier")
    initial_simulation_time: Optional[datetime] = Field(None, description="Optional initial simulation UTC time")


class SimulationSpeedRequest(BaseModel):
    speed_factor: float = Field(..., ge=0.1, le=100.0, description="New speed multiplier (e.g. 1.0, 5.0, 10.0, 30.0, 60.0)")


class SimulationStatusResponse(BaseModel):
    clock_status: SimulationClockStatus
    active_session_id: Optional[str] = Field(None, description="Active session identifier")
    active_patient_id: Optional[str] = Field(None, description="Active patient identifier")
    active_scenario_name: ScenarioName = Field(ScenarioName.STABLE, description="Active scenario name")
    active_scenario_state: ScenarioEngineState = Field(ScenarioEngineState.STABLE, description="Active trajectory phase")
    registered_patients_count: int = Field(..., description="Total patients in registry")
