import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.services.inference_runtime import runtime

client = TestClient(app)

def test_1_health_endpoint():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}

def test_2_root_api_metadata_endpoint():
    res = client.get("/api/v1/model-version")
    assert res.status_code == 200
    data = res.json()
    assert data["model_version"] == "logistic-regression-v1"
    assert data["is_demo_model"] is False
    assert data["prediction_horizon_hours"] == 6

def test_3_valid_prediction_request():
    payload = {
        "patient_id": "P-REST-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 115.0,
        "map": 62.0,
        "resp_rate": 24.0,
        "spo2": 94.0,
        "temperature_c": 39.1,
        "source": "simulator"
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["patient_id"] == "P-REST-01"
    assert 0.0 <= data["risk_probability"] <= 1.0

def test_4_invalid_prediction_request():
    res = client.post("/api/v1/events/vitals", content="invalid json body", headers={"Content-Type": "application/json"})
    assert res.status_code == 422

def test_5_missing_required_fields():
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 115.0
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 422

def test_6_invalid_timestamp():
    payload = {
        "patient_id": "P-REST-06",
        "timestamp": "not-a-valid-timestamp",
        "heart_rate": 115.0
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 422

def test_7_invalid_numeric_input():
    payload = {
        "patient_id": "P-REST-07",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 9999.0  # Exceeds max limit 400
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 422

def test_8_patient_lookup():
    # Create patient
    create_res = client.post(
        "/api/v1/patients",
        json={"name": "REST Patient", "age": 55, "medical_history": ["hypertension"]},
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert create_res.status_code == 200
    patient_id = create_res.json()["id"]

    # Get patient
    get_res = client.get(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "REST Patient"

def test_9_patient_not_found_handling():
    res = client.get(
        "/api/v1/patients/nonexistent-patient-9999",
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_10_prediction_response_schema():
    payload = {
        "patient_id": "P-REST-10",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 110.0,
        "map": 65.0,
        "resp_rate": 20.0,
        "spo2": 96.0,
        "temperature_c": 38.5
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 201
    data = res.json()
    
    required_keys = [
        "patient_id", "prediction_timestamp", "prediction_horizon_hours",
        "risk_probability", "confidence", "signal_quality",
        "contributing_factors", "shap_explanation", "uncertainty_summary",
        "latency_ms", "model_version", "is_demo_model", "alert"
    ]
    for key in required_keys:
        assert key in data, f"Missing required response key: {key}"

def test_11_model_version_is_logistic_regression_v1():
    payload = {
        "patient_id": "P-REST-11",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 80.0
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 201
    assert res.json()["model_version"] == "logistic-regression-v1"

def test_12_is_demo_model_is_false():
    payload = {
        "patient_id": "P-REST-12",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 80.0
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 201
    assert res.json()["is_demo_model"] is False

def test_13_shap_remains_available():
    payload = {
        "patient_id": "P-REST-13",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 120.0,
        "map": 60.0
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 201
    shap_exp = res.json()["shap_explanation"]
    assert shap_exp["explanation_available"] is True
    assert len(shap_exp["feature_attributions"]) == 31

def test_14_uncertainty_remains_explicitly_unavailable():
    payload = {
        "patient_id": "P-REST-14",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 80.0
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 201
    unc = res.json()["uncertainty_summary"]
    assert unc["uncertainty_available"] is False
    assert unc["method"] == "UNAVAILABLE"

def test_15_alert_payload_remains_valid():
    payload = {
        "patient_id": "P-REST-15",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "heart_rate": 145.0,
        "map": 45.0,
        "resp_rate": 30.0,
        "spo2": 88.0,
        "temperature_c": 39.5
    }
    res = client.post("/api/v1/events/vitals", json=payload)
    assert res.status_code == 201
    alert_info = res.json()["alert"]
    assert isinstance(alert_info, dict)
    assert "alert_emitted" in alert_info

def test_16_correct_http_status_codes():
    # GET read health -> 200
    assert client.get("/api/v1/health").status_code == 200
    # GET not found -> 404
    assert client.get("/api/v1/patients/invalid-9999", headers={"Authorization": "Bearer fake-super-secret-token"}).status_code == 404
    # POST invalid -> 422
    assert client.post("/api/v1/events/vitals", json={}).status_code == 422
    # Unauthorized token -> 401
    assert client.get("/api/v1/patients/some-id", headers={"Authorization": "Bearer invalid-token"}).status_code == 401

def test_17_internal_errors_do_not_leak_sensitive_info():
    res = client.get("/api/v1/patients/nonexistent-17", headers={"Authorization": "Bearer fake-super-secret-token"})
    assert res.status_code == 404
    detail = str(res.json()["detail"])
    # Verify no file paths or stack traces in error detail
    assert "C:" not in detail
    assert "Traceback" not in detail
    assert ".py" not in detail

def test_18_cors_configuration_present():
    from fastapi.middleware.cors import CORSMiddleware
    middlewares = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in middlewares

def test_19_authentication_behavior():
    # Valid token succeeds (returns 404 since patient ID doesn't exist, but authentication passes)
    res_valid = client.get("/api/v1/patients/P-AUTH-TEST", headers={"Authorization": "Bearer fake-super-secret-token"})
    assert res_valid.status_code == 404
    
    # Invalid token fails with 401 Unauthorized
    res_invalid = client.get("/api/v1/patients/P-AUTH-TEST", headers={"Authorization": "Bearer wrong-token"})
    assert res_invalid.status_code == 401

def test_20_no_active_rest_endpoint_depends_on_legacy_deployment_backend():
    import sys
    # Verify that deployment.backend is not loaded in sys.modules by src.backend
    for mod in list(sys.modules.keys()):
        assert not mod.startswith("deployment.backend"), f"Legacy module loaded: {mod}"
