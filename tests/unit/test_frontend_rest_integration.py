import pytest
from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_api_client_health():
    """Verify GET /api/v1/health contract for frontend status component."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_api_client_model_version():
    """Verify GET /api/v1/model-version contract for frontend model metadata display."""
    response = client.get("/api/v1/model-version")
    assert response.status_code == 200
    data = response.json()
    assert "model_version" in data
    assert data["model_version"] == "logistic-regression-v1"
    assert "is_demo_model" in data
    assert data["is_demo_model"] is False

def test_api_client_auth_failure_401():
    """Verify 401 Unauthorized handling for invalid bearer token on patient endpoints."""
    response = client.get("/api/v1/patients/P-TEST-AUTH-401", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    assert "detail" in response.json()

def test_api_client_create_and_get_patient():
    """Verify POST /api/v1/patients and GET /api/v1/patients/{id} contract."""
    create_res = client.post(
        "/api/v1/patients",
        json={"patient_id": "P-TEST-AUTH-OK", "name": "Auth Patient", "age": 60},
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert create_res.status_code == 200
    assert create_res.json()["id"] == "P-TEST-AUTH-OK"

    get_res = client.get(
        "/api/v1/patients/P-TEST-AUTH-OK",
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == "P-TEST-AUTH-OK"

def test_api_client_vitals_retrieval():
    """Verify GET /api/v1/patients/{id}/vitals returns vitals list."""
    response = client.get("/api/v1/patients/P-TEST-VITALS/vitals", headers={"Authorization": "Bearer fake-super-secret-token"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_api_client_risk_retrieval():
    """Verify GET /api/v1/patients/{id}/risk returns RiskAssessment structure."""
    response = client.get("/api/v1/patients/P-TEST-RISK/risk", headers={"Authorization": "Bearer fake-super-secret-token"})
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 1.0
    assert "risk_level" in data

def test_api_client_explanation_shap():
    """Verify GET /api/v1/patients/{id}/explanation returns SHAP feature importance structure."""
    response = client.get("/api/v1/patients/P-TEST-SHAP/explanation", headers={"Authorization": "Bearer fake-super-secret-token"})
    assert response.status_code == 200
    data = response.json()
    assert "feature_importance" in data
    assert "summary" in data

def test_api_client_alerts_retrieval():
    """Verify GET /api/v1/patients/{id}/alerts returns alert list."""
    response = client.get("/api/v1/patients/P-TEST-ALERTS/alerts", headers={"Authorization": "Bearer fake-super-secret-token"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_api_client_uncertainty_unavailable():
    """Verify event ingestion returns explicit uncertainty_available: False state."""
    event_payload = {
        "patient_id": "P-TEST-UNCERTAINTY",
        "timestamp": "2026-10-01T12:00:00Z",
        "heart_rate": 95.0,
        "map": 70.0,
        "resp_rate": 18.0,
        "spo2": 96.0,
        "temperature_c": 37.0,
        "lactate": 1.5,
        "source": "integration"
    }
    response = client.post("/api/v1/events/vitals", json=event_payload)
    assert response.status_code == 201
    data = response.json()
    assert "uncertainty_summary" in data
    unc = data["uncertainty_summary"]
    assert unc["uncertainty_available"] is False
    assert unc["method"] == "UNAVAILABLE"

def test_api_client_malformed_input_422():
    """Verify 422 Unprocessable Entity for invalid event schema."""
    response = client.post("/api/v1/events/vitals", json={"invalid_field": True})
    assert response.status_code == 422
