"""
Integration tests for versioned REST control API endpoints using HTTPX / TestClient.
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.main import app
from app.services.patient_registry import patient_registry
from app.services.simulation_service import simulation_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_services():
    patient_registry.clear()
    simulation_service.stop_simulation()


def test_get_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_create_and_get_patient():
    payload = {
        "profile_type": "hypertensive",
        "age": 60,
        "seed": 42,
    }
    create_res = client.post("/api/v1/patients", json=payload)
    assert create_res.status_code == 201
    patient_data = create_res.json()
    p_id = patient_data["patient_id"]
    assert patient_data["profile_type"] == "hypertensive"
    assert patient_data["age"] == 60

    # Get patient by ID
    get_res = client.get(f"/api/v1/patients/{p_id}")
    assert get_res.status_code == 200
    assert get_res.json()["patient_id"] == p_id

    # List patients
    list_res = client.get("/api/v1/patients")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_get_nonexistent_patient_returns_404():
    res = client.get("/api/v1/patients/NONEXISTENT-ID")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "PATIENT_NOT_FOUND"


def test_simulation_control_lifecycle():
    # 1. Create Patient
    p_res = client.post("/api/v1/patients", json={"profile_type": "standard"})
    patient_id = p_res.json()["patient_id"]

    # 2. Start Simulation
    start_res = client.post("/api/v1/simulation/start", json={"speed_factor": 5.0, "patient_id": patient_id})
    assert start_res.status_code == 200
    s_data = start_res.json()
    assert s_data["clock_status"]["state"] == "running"
    assert s_data["clock_status"]["speed_factor"] == 5.0

    # 3. Pause Simulation
    pause_res = client.post("/api/v1/simulation/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["clock_status"]["state"] == "paused"

    # 4. Resume Simulation
    resume_res = client.post("/api/v1/simulation/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["clock_status"]["state"] == "running"

    # 5. Set Speed
    speed_res = client.post("/api/v1/simulation/speed", json={"speed_factor": 10.0})
    assert speed_res.status_code == 200
    assert speed_res.json()["clock_status"]["speed_factor"] == 10.0

    # 6. Set Scenario
    scenario_res = client.post(f"/api/v1/patients/{patient_id}/scenario", json={"scenario_name": "gradual_deterioration"})
    assert scenario_res.status_code == 200
    assert scenario_res.json()["active_scenario_name"] == "gradual_deterioration"

    # 7. Get Status Summary
    status_res = client.get("/api/v1/simulation/status")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["active_patient_id"] == patient_id
    assert st_data["active_scenario_name"] == "gradual_deterioration"

    # 8. Stop Simulation
    stop_res = client.post("/api/v1/simulation/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["clock_status"]["state"] == "stopped"


def test_invalid_speed_validation_error():
    res = client.post("/api/v1/simulation/speed", json={"speed_factor": -5.0})
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
