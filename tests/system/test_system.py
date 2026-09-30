import time
import pytest
from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_api_latency():
    start = time.time()
    response = client.get("/api/v1/health")
    latency = time.time() - start
    assert response.status_code == 200
    assert latency < 0.500, f"Latency too high: {latency}s"

def test_database_failure_degradation(monkeypatch):
    # Simulate a DB failure
    def mock_get_patient(*args):
        from src.backend.core.exceptions import NotFoundException
        raise NotFoundException("DB Connection Timeout")
        
    from src.backend.services.patient_service import PatientService
    monkeypatch.setattr(PatientService, "get_patient", mock_get_patient)
    
    response = client.get(
        "/api/v1/patients/some-id",
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    # The system shouldn't crash 500, it should yield the appropriate error code
    assert response.status_code == 404
