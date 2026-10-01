"""
Contract validation tests for ARGUS Data Contract v1.0 schemas.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

import sys
from pathlib import Path

# Add backend directory to sys.path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.schemas.contract import (
    APIErrorPayload,
    APIErrorResponse,
    DataSource,
    MessageType,
    PatientEventMessage,
    QualityStatus,
    ScenarioState,
    SensorEventMessage,
    SimulationEventMessage,
    VitalSignSet,
    VitalUnits,
    VitalUpdateMessage,
)


def test_valid_vital_update_message():
    now_utc = datetime.now(timezone.utc)
    payload = {
        "schema_version": "1.0",
        "message_type": "vital_update",
        "patient_id": "P-101",
        "session_id": "SESS-2026-001",
        "source": "synthetic",
        "timestamp": now_utc,
        "simulation_time": now_utc,
        "vitals": {
            "heart_rate": 78.5,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "spo2": 98.0,
            "temperature": 36.8,
            "respiratory_rate": 16.0,
        },
        "quality_status": "valid",
        "scenario_state": "stable",
    }

    msg = VitalUpdateMessage(**payload)
    assert msg.schema_version == "1.0"
    assert msg.message_type == MessageType.VITAL_UPDATE
    assert msg.patient_id == "P-101"
    assert msg.session_id == "SESS-2026-001"
    assert msg.vitals.heart_rate == 78.5
    assert msg.vitals.systolic_bp == 120.0
    assert msg.vitals.diastolic_bp == 80.0
    assert msg.vitals.spo2 == 98.0
    assert msg.vitals.temperature == 36.8
    assert msg.vitals.respiratory_rate == 16.0
    assert msg.vital_units.heart_rate == "bpm"
    assert msg.vital_units.systolic_bp == "mmHg"
    assert msg.vital_units.diastolic_bp == "mmHg"
    assert msg.vital_units.spo2 == "%"
    assert msg.vital_units.temperature == "°C"
    assert msg.vital_units.respiratory_rate == "breaths/min"
    assert msg.quality_status == QualityStatus.VALID
    assert msg.scenario_state == ScenarioState.STABLE


def test_all_six_vitals_supported_with_nulls():
    """Verify that vital fields can be null when quality_status indicates missingness."""
    now_utc = datetime.now(timezone.utc)
    msg = VitalUpdateMessage(
        schema_version="1.0",
        patient_id="P-101",
        session_id="SESS-001",
        source="synthetic",
        timestamp=now_utc,
        simulation_time=now_utc,
        vitals=VitalSignSet(
            heart_rate=80.0,
            systolic_bp=None,
            diastolic_bp=None,
            spo2=95.0,
            temperature=None,
            respiratory_rate=20.0,
        ),
        quality_status=QualityStatus.MISSING,
        scenario_state=ScenarioState.DATA_QUALITY_PROBLEM,
    )
    assert msg.vitals.systolic_bp is None
    assert msg.quality_status == QualityStatus.MISSING
    assert msg.scenario_state == ScenarioState.DATA_QUALITY_PROBLEM


def test_mandatory_identity_missing():
    """Verify missing patient_id or session_id raises validation error."""
    now_utc = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        VitalUpdateMessage(
            schema_version="1.0",
            patient_id="",  # Empty string rejected by min_length=1
            session_id="SESS-001",
            source="synthetic",
            timestamp=now_utc,
            simulation_time=now_utc,
            vitals=VitalSignSet(heart_rate=70.0),
        )

    with pytest.raises(ValidationError):
        VitalUpdateMessage(
            schema_version="1.0",
            patient_id="P-101",
            # session_id omitted
            source="synthetic",
            timestamp=now_utc,
            simulation_time=now_utc,
            vitals=VitalSignSet(heart_rate=70.0),
        )


def test_out_of_bounds_vitals_rejected():
    """Verify unphysiological values violate bounds."""
    now_utc = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        VitalSignSet(heart_rate=-5.0)

    with pytest.raises(ValidationError):
        VitalSignSet(spo2=105.0)

    with pytest.raises(ValidationError):
        VitalSignSet(temperature=60.0)


def test_valid_patient_event_message():
    now_utc = datetime.now(timezone.utc)
    msg = PatientEventMessage(
        schema_version="1.0",
        patient_id="P-102",
        session_id="SESS-002",
        source="synthetic",
        timestamp=now_utc,
        simulation_time=now_utc,
        event_name="baseline_configured",
        payload={"age": 55, "baseline_hr": 72.0},
    )
    assert msg.message_type == MessageType.PATIENT_EVENT
    assert msg.event_name == "baseline_configured"
    assert msg.payload["age"] == 55


def test_valid_sensor_event_message():
    now_utc = datetime.now(timezone.utc)
    msg = SensorEventMessage(
        schema_version="1.0",
        patient_id="P-102",
        session_id="SESS-002",
        source="synthetic",
        timestamp=now_utc,
        simulation_time=now_utc,
        sensor_type="ecg_lead_ii",
        event_type="disconnected",
        details="Lead detached",
    )
    assert msg.message_type == MessageType.SENSOR_EVENT
    assert msg.sensor_type == "ecg_lead_ii"
    assert msg.event_type == "disconnected"


def test_valid_simulation_event_message():
    now_utc = datetime.now(timezone.utc)
    msg = SimulationEventMessage(
        schema_version="1.0",
        patient_id="P-102",
        session_id="SESS-002",
        source="synthetic",
        timestamp=now_utc,
        simulation_time=now_utc,
        event_type="scenario_transition",
        previous_state=ScenarioState.STABLE,
        new_state=ScenarioState.GRADUAL_DETERIORATION,
        speed_factor=5.0,
    )
    assert msg.message_type == MessageType.SIMULATION_EVENT
    assert msg.previous_state == ScenarioState.STABLE
    assert msg.new_state == ScenarioState.GRADUAL_DETERIORATION
    assert msg.speed_factor == 5.0


def test_valid_api_error_response():
    now_utc = datetime.now(timezone.utc)
    err = APIErrorResponse(
        error=APIErrorPayload(
            code="SESSION_NOT_FOUND",
            message="The specified simulation session does not exist.",
            details={"session_id": "INVALID-ID"},
            timestamp=now_utc,
        )
    )
    assert err.error.code == "SESSION_NOT_FOUND"
    assert err.error.details["session_id"] == "INVALID-ID"


def test_utc_timezone_enforcement():
    """Verify naive datetime is auto-tagged with UTC tzinfo."""
    naive_dt = datetime(2026, 10, 1, 12, 0, 0)
    msg = VitalUpdateMessage(
        schema_version="1.0",
        patient_id="P-101",
        session_id="SESS-001",
        source="synthetic",
        timestamp=naive_dt,
        simulation_time=naive_dt,
        vitals=VitalSignSet(heart_rate=75.0),
    )
    assert msg.timestamp.tzinfo == timezone.utc
    assert msg.simulation_time.tzinfo == timezone.utc
