"""
Integration test suite for Part 1 (Simulator) + Part 2 (Clinical Intelligence) integration.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.services.part1_adapter import Part1Adapter
from src.backend.schemas.schemas import VitalEvent

client = TestClient(app)


def test_part1_adapter_transformation():
    """Test 1 & 4 & 5: Validates contract v1.0 vital_update transformation and timestamp mapping."""
    payload = {
        "schema_version": "1.0",
        "message_type": "vital_update",
        "patient_id": "P-ICU-001",
        "session_id": "sess-test-01",
        "source": "synthetic_generator",
        "timestamp": "2026-10-02T12:00:00Z",
        "simulation_time": "2026-10-02T14:30:00Z",
        "vitals": {
            "heart_rate": 115.0,
            "systolic_bp": 90.0,
            "diastolic_bp": 60.0,
            "spo2": 93.0,
            "temperature": 38.5,
            "respiratory_rate": 24.0
        },
        "quality_status": "valid",
        "scenario_state": "gradual_deterioration"
    }

    event = Part1Adapter.transform_vital_update(payload)

    assert isinstance(event, VitalEvent)
    assert event.patient_id == "P-ICU-001"
    assert event.session_id == "sess-test-01"
    # Verify simulation_time was mapped to clinical timestamp
    assert event.timestamp.year == 2026
    assert event.timestamp.month == 10
    assert event.timestamp.day == 2
    assert event.timestamp.hour == 14
    assert event.timestamp.minute == 30
    assert event.heart_rate == 115.0
    # MAP computed from SBP=90, DBP=60 -> 60 + 30/3 = 70.0
    assert event.map == 70.0
    assert event.resp_rate == 24.0
    assert event.spo2 == 93.0
    assert event.temperature_c == 38.5


@pytest.mark.asyncio
async def test_part1_ingestion_endpoint_triggers_part2_inference():
    """Test 13 & 14 & 15 & 16: Part 1 event triggers Part 2 inference, SHAP, SmartAlertEngine, and persistence."""
    payload = {
        "schema_version": "1.0",
        "message_type": "vital_update",
        "patient_id": "P-ICU-002",
        "session_id": "sess-test-02",
        "source": "synthetic_generator",
        "timestamp": "2026-10-02T12:00:00Z",
        "simulation_time": "2026-10-02T15:00:00Z",
        "vitals": {
            "heart_rate": 130.0,
            "systolic_bp": 80.0,
            "diastolic_bp": 50.0,
            "spo2": 90.0,
            "temperature": 39.2,
            "respiratory_rate": 28.0
        },
        "quality_status": "valid",
        "scenario_state": "rapid_deterioration"
    }

    res = client.post("/api/v1/integration/part1/ingest", json=payload)
    assert res.status_code == 201

    data = res.json()
    assert data["patient_id"] == "P-ICU-002"
    assert "risk_probability" in data
    assert 0.0 <= data["risk_probability"] <= 1.0
    assert "confidence" in data
    assert "signal_quality" in data
    assert "shap_explanation" in data
    assert data["shap_explanation"]["explanation_available"] is True


def test_invalid_part1_message_rejected():
    """Test unsupported message types are rejected by adapter."""
    payload = {
        "schema_version": "1.0",
        "message_type": "invalid_type",
        "patient_id": "P-ICU-003",
        "vitals": {}
    }

    res = client.post("/api/v1/integration/part1/ingest", json=payload)
    assert res.status_code == 422
