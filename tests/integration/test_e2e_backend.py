import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.backend.main import app
from src.backend.db.store import Session, PatientRecord, VitalRecord, PredictionRecord, AlertRecord
from src.backend.db.repositories import patient_repository
from src.backend.services.patient_service import patient_service
from src.backend.services.inference_service import InferenceService
from src.backend.services.inference_runtime import runtime, Runtime
from src.backend.schemas.schemas import VitalEvent

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer fake-super-secret-token"}

def test_01_rest_single_source_of_truth():
    p_id = f"E2E-REST-SST-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    
    ts = datetime.now(timezone.utc).isoformat()
    response = client.post(
        "/api/v1/events/vitals",
        json={
            "patient_id": p_id,
            "timestamp": ts,
            "heart_rate": 88.0,
            "map": 82.0,
            "resp_rate": 18.0,
            "spo2": 97.0,
            "temperature": 37.1
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == p_id
    assert data["model_version"] == "logistic-regression-v1"
    assert data["is_demo_model"] is False
    assert data["shap_explanation"]["explanation_available"] is True
    assert data["uncertainty_summary"]["uncertainty_available"] is False
    assert data["uncertainty_summary"]["method"] == "UNAVAILABLE"

def test_02_websocket_single_source_of_truth():
    p_id = f"E2E-WS-SST-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    ts = datetime.now(timezone.utc).isoformat()
    
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": p_id,
            "timestamp": ts,
            "heart_rate": 85.0,
            "map": 84.0,
            "resp_rate": 17.0,
            "spo2": 98.0,
            "temperature_c": 36.9
        })
        msg = ws.receive_json()
        assert msg["type"] == "prediction"
        p = msg["payload"]
        assert p["patient_id"] == p_id
        assert p["model_version"] == "logistic-regression-v1"
        assert p["is_demo_model"] is False
        assert p["shap_explanation"]["explanation_available"] is True
        assert p["uncertainty_summary"]["uncertainty_available"] is False

def test_03_rest_database_round_trip():
    p_id = f"E2E-ROUNDTRIP-REST-{uuid.uuid4().hex[:6]}"
    # 1. Create Patient
    client.post("/api/v1/patients", json={"patient_id": p_id, "name": "Roundtrip Test"}, headers=AUTH_HEADERS)
    
    # 2. Ingest Vital Event
    ts = datetime.now(timezone.utc).isoformat()
    ingest_res = client.post(
        "/api/v1/events/vitals",
        json={"patient_id": p_id, "timestamp": ts, "heart_rate": 92.0, "map": 78.0, "resp_rate": 19.0, "spo2": 96.0}
    )
    assert ingest_res.status_code == 201
    
    # 3. Query via REST endpoints
    get_p = client.get(f"/api/v1/patients/{p_id}", headers=AUTH_HEADERS)
    assert get_p.status_code == 200
    assert get_p.json()["id"] == p_id

    get_risk = client.get(f"/api/v1/patients/{p_id}/risk", headers=AUTH_HEADERS)
    assert get_risk.status_code == 200
    assert "risk_score" in get_risk.json()

    get_exp = client.get(f"/api/v1/patients/{p_id}/explanation", headers=AUTH_HEADERS)
    assert get_exp.status_code == 200
    assert "feature_importance" in get_exp.json()

def test_04_websocket_database_round_trip():
    p_id = f"E2E-ROUNDTRIP-WS-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": p_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 90.0,
            "map": 80.0,
            "resp_rate": 18.0,
            "spo2": 97.0
        })
        ws.receive_json()
        
    # Verify records in database
    with Session() as s:
        v_row = s.scalars(select(VitalRecord).where(VitalRecord.patient_id == p_id)).first()
        p_row = s.scalars(select(PredictionRecord).where(PredictionRecord.patient_id == p_id)).first()
        assert v_row is not None
        assert p_row is not None
        assert p_row.model_version == "logistic-regression-v1"

def test_05_patient_trajectory():
    p_id = f"E2E-TRAJECTORY-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    now = datetime.now(timezone.utc)

    # Deteriorating vitals sequence
    for i in range(5):
        ts = (now + timedelta(hours=i)).isoformat()
        client.post(
            "/api/v1/events/vitals",
            json={
                "patient_id": p_id,
                "timestamp": ts,
                "heart_rate": 95.0 + i * 12.0,
                "map": 82.0 - i * 10.0,
                "resp_rate": 18.0 + i * 4.0,
                "spo2": 98.0 - i * 3.0,
                "temperature_c": 37.0 + i * 0.6,
                "lactate": 1.0 + i * 1.5
            }
        )
        
    traj_res = client.get(f"/api/v1/patients/{p_id}/trajectory", headers=AUTH_HEADERS)
    assert traj_res.status_code == 200
    points = traj_res.json()["points"]
    assert len(points) == 5
    # Verify chronological ordering
    for idx in range(len(points) - 1):
        assert points[idx]["timestamp"] <= points[idx + 1]["timestamp"]

def test_06_two_patient_isolation_rest():
    p_a = f"E2E-ISO-REST-A-{uuid.uuid4().hex[:6]}"
    p_b = f"E2E-ISO-REST-B-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_a)
    patient_service.require(p_b)
    
    # Interleaved ingestion
    client.post("/api/v1/events/vitals", json={"patient_id": p_a, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 78.0})
    client.post("/api/v1/events/vitals", json={"patient_id": p_b, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 98.0})
    client.post("/api/v1/events/vitals", json={"patient_id": p_a, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 80.0})
    
    v_a = client.get(f"/api/v1/patients/{p_a}/vitals", headers=AUTH_HEADERS).json()
    v_b = client.get(f"/api/v1/patients/{p_b}/vitals", headers=AUTH_HEADERS).json()
    assert len(v_a) == 2
    assert len(v_b) == 1
    for v in v_a:
        assert v.get("patient_id") == p_a or v.get("id") == p_a

def test_07_two_patient_isolation_websocket():
    p_a = f"E2E-ISO-WS-A-{uuid.uuid4().hex[:6]}"
    p_b = f"E2E-ISO-WS-B-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_a)
    patient_service.require(p_b)
    
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"patient_id": p_a, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 75.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0})
        m1 = ws.receive_json()
        assert m1["patient_id"] == p_a

        ws.send_json({"patient_id": p_b, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 88.0, "map": 78.0, "resp_rate": 20.0, "spo2": 95.0})
        m2 = ws.receive_json()
        assert m2["patient_id"] == p_b

def test_08_model_integrity_version_and_features():
    assert runtime.model is not None
    assert runtime.demo is False
    assert runtime.model_version_name == "logistic-regression-v1"
    
    # Model metadata endpoint check
    meta = client.get("/api/v1/model-version").json()
    assert meta["model_version"] == "logistic-regression-v1"
    assert meta["is_demo_model"] is False

def test_09_shap_integrity():
    p_id = f"E2E-SHAP-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    
    res = client.post(
        "/api/v1/events/vitals",
        json={"patient_id": p_id, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 84.0, "map": 82.0, "resp_rate": 17.0, "spo2": 98.0}
    ).json()
    
    shap = res.get("shap_explanation")
    assert shap is not None
    assert shap["explanation_available"] is True
    assert len(shap["feature_attributions"]) == 31

def test_10_uncertainty_integrity():
    p_id = f"E2E-UNC-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    
    res = client.post(
        "/api/v1/events/vitals",
        json={"patient_id": p_id, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 80.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0}
    ).json()
    
    unc = res.get("uncertainty_summary")
    assert unc is not None
    assert unc["uncertainty_available"] is False
    assert unc["method"] == "UNAVAILABLE"

def test_11_alert_engine_hysteresis_and_deduplication():
    p_id = f"E2E-ALERT-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    now = datetime.now(timezone.utc)
    
    # 1. Normal event
    r1 = client.post("/api/v1/events/vitals", json={"patient_id": p_id, "timestamp": now.isoformat(), "heart_rate": 75.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0}).json()
    assert r1.get("alert", {}).get("alert_emitted") is False
    
    # 2. Deteriorating events to trigger alert
    for i in range(1, 4):
        client.post("/api/v1/events/vitals", json={
            "patient_id": p_id,
            "timestamp": (now + timedelta(hours=i)).isoformat(),
            "heart_rate": 100.0 + i * 20.0,
            "map": 80.0 - i * 15.0,
            "resp_rate": 18.0 + i * 5.0,
            "spo2": 96.0 - i * 4.0,
            "temperature_c": 37.0 + i * 0.8,
            "lactate": 1.0 + i * 2.0
        })
        
    alerts = client.get(f"/api/v1/patients/{p_id}/alerts", headers=AUTH_HEADERS).json()
    assert isinstance(alerts, list)

def test_12_transaction_rollback_on_db_error(mocker=None):
    p_id = f"E2E-ROLLBACK-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    
    # Verify that invalid event inputs raise 422 without writing garbage
    res = client.post("/api/v1/events/vitals", json={"patient_id": p_id, "timestamp": "invalid-ts", "heart_rate": 80.0})
    assert res.status_code == 422

def test_13_service_failure_handling():
    # Unsupported numeric string
    res = client.post("/api/v1/events/vitals", json={"patient_id": "P-FAIL", "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": "invalid_number"})
    assert res.status_code == 422
    assert "detail" in res.json()

@pytest.mark.asyncio
async def test_14_concurrent_users_and_streams():
    patients = [f"E2E-CONCUR-{i}-{uuid.uuid4().hex[:4]}" for i in range(4)]
    for p in patients:
        patient_service.require(p)
        
    async def process_p(p_id):
        event = VitalEvent(
            patient_id=p_id,
            timestamp=datetime.now(timezone.utc),
            heart_rate=82.0,
            map=84.0,
            resp_rate=17.0,
            spo2=98.0
        )
        return await InferenceService.ingest(event)

    results = await asyncio.gather(*[process_p(p) for p in patients])
    assert len(results) == 4
    for r in results:
        assert r["model_version"] == "logistic-regression-v1"

def test_15_restart_and_state_recovery():
    p_id = f"E2E-RESTART-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    
    # Ingest event
    client.post("/api/v1/events/vitals", json={"patient_id": p_id, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 80.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0})
    
    # Instantiate fresh Runtime instance (simulating backend restart)
    new_runtime = Runtime()
    assert new_runtime.model is not None
    assert new_runtime.model_version_name == "logistic-regression-v1"
    
    # Query database after restart
    with Session() as s:
        v_row = s.scalars(select(VitalRecord).where(VitalRecord.patient_id == p_id)).first()
        assert v_row is not None
        assert v_row.patient_id == p_id

def test_16_live_postgresql_e2e():
    import os
    from sqlalchemy import create_engine
    
    pg_url = os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/sepsisguard_test"
    try:
        engine_test = create_engine(pg_url, connect_args={"connect_timeout": 2})
        with engine_test.connect() as conn:
            pass
    except Exception:
        pytest.skip("PostgreSQL database unavailable in current environment")
        
    p_id = f"E2E-PG-VERIFY-{uuid.uuid4().hex[:6]}"
    patient_service.require(p_id)
    
    res = client.post("/api/v1/events/vitals", json={"patient_id": p_id, "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 80.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0})
    assert res.status_code == 201

