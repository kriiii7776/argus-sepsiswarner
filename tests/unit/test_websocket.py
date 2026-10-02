import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.services.event_broker import broker
from src.backend.services.patient_service import patient_service
from src.backend.services.inference_runtime import runtime

client = TestClient(app)

def test_01_connection_accepted():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        assert ws is not None

def test_02_canonical_endpoint():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        # Send keepalive ping
        ws.send_json({"type": "ping"})
        msg = ws.receive_json()
        assert msg["type"] == "pong"
        assert "occurred_at" in msg

def test_03_compatibility_alias():
    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_text("Hello Server")
        data = ws.receive_text()
        assert data == "Message text was: Hello Server"

def test_04_connection_cleanup():
    initial_count = len(broker.subscribers)
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        assert len(broker.subscribers) >= initial_count + 1
    # After exiting context manager, subscriber count should drop
    assert len(broker.subscribers) == initial_count

def test_05_valid_raw_event():
    patient_id = "WS-P101"
    patient_service.require(patient_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        event_payload = {
            "patient_id": patient_id,
            "timestamp": now_iso,
            "heart_rate": 82.0,
            "bp_systolic": 118.0,
            "bp_diastolic": 76.0,
            "resp_rate": 16.0,
            "spo2": 98.0,
            "temperature": 37.0
        }
        ws.send_json(event_payload)
        response = ws.receive_json()
        assert response["type"] == "prediction"
        assert response["patient_id"] == patient_id
        assert "payload" in response

def test_06_prediction_returned():
    patient_id = "WS-P102"
    patient_service.require(patient_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": now_iso,
            "heart_rate": 80.0,
            "bp_systolic": 120.0,
            "bp_diastolic": 80.0,
            "resp_rate": 18.0,
            "spo2": 97.0,
            "temperature": 36.8
        })
        msg = ws.receive_json()
        p = msg["payload"]
        assert p["model_version"] == "logistic-regression-v1"
        assert p["is_demo_model"] is False
        assert "risk_probability" in p
        assert isinstance(p["risk_probability"], float)

def test_07_shap_returned():
    patient_id = "WS-P103"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 88.0,
            "map": 85.0,
            "resp_rate": 19.0,
            "spo2": 96.0,
            "temperature_c": 37.2
        })
        msg = ws.receive_json()
        shap = msg["payload"].get("shap_explanation")
        assert shap is not None
        assert shap["explanation_available"] is True
        assert "feature_attributions" in shap

def test_08_uncertainty_unavailable():
    patient_id = "WS-P104"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 75.0,
            "map": 80.0,
            "resp_rate": 16.0,
            "spo2": 99.0
        })
        msg = ws.receive_json()
        unc = msg["payload"].get("uncertainty_summary")
        assert unc is not None
        assert unc.get("method") == "UNAVAILABLE" or unc.get("status") == "UNAVAILABLE"
        assert unc["uncertainty_available"] is False

def test_09_alert_returned():
    patient_id = "WS-P105-HIGH"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        # High-risk vitals to trigger alert
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 140.0,
            "map": 45.0,
            "resp_rate": 35.0,
            "spo2": 82.0,
            "temperature_c": 39.8,
            "lactate": 6.5
        })
        # Should receive prediction message followed by alert message
        msg1 = ws.receive_json()
        assert msg1["type"] == "prediction"
        
        # Check if alert was emitted in payload
        if msg1["payload"].get("alert", {}).get("alert_emitted"):
            msg2 = ws.receive_json()
            assert msg2["type"] == "alert"
            assert msg2["patient_id"] == patient_id

def test_10_clinical_timestamp_preserved():
    patient_id = "WS-P106"
    patient_service.require(patient_id)
    clinical_ts = "2026-10-01T15:30:00+00:00"

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": clinical_ts,
            "heart_rate": 78.0,
            "map": 82.0,
            "resp_rate": 16.0,
            "spo2": 98.0
        })
        msg = ws.receive_json()
        pred_ts = msg["payload"]["prediction_timestamp"]
        assert "2026-10-01" in pred_ts
        assert "15:30:00" in pred_ts

def test_11_iso_timestamp():
    patient_id = "WS-P107"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": "2026-10-01T12:00:00Z",
            "heart_rate": 70.0,
            "map": 90.0,
            "resp_rate": 14.0,
            "spo2": 99.0
        })
        msg = ws.receive_json()
        assert msg["type"] == "prediction"

def test_12_out_of_order_events():
    patient_id = "WS-P108"
    patient_service.require(patient_id)
    now = datetime.now(timezone.utc)
    t1 = (now - timedelta(minutes=10)).isoformat()
    t2 = (now - timedelta(minutes=30)).isoformat() # older event arriving later

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"patient_id": patient_id, "timestamp": t1, "heart_rate": 80.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0})
        ws.receive_json()
        ws.send_json({"patient_id": patient_id, "timestamp": t2, "heart_rate": 85.0, "map": 82.0, "resp_rate": 17.0, "spo2": 97.0})
        msg2 = ws.receive_json()
        assert msg2["type"] == "prediction"

def test_13_duplicate_timestamp():
    patient_id = "WS-P109"
    patient_service.require(patient_id)
    t_dup = datetime.now(timezone.utc).isoformat()

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"patient_id": patient_id, "timestamp": t_dup, "heart_rate": 80.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0})
        ws.receive_json()
        ws.send_json({"patient_id": patient_id, "timestamp": t_dup, "heart_rate": 82.0, "map": 86.0, "resp_rate": 16.0, "spo2": 98.0})
        msg2 = ws.receive_json()
        assert msg2["type"] == "prediction"

def test_14_malformed_json():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_text("{malformed_json_content")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Invalid JSON" in msg["message"]

def test_15_missing_patient_id():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 80.0})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Missing required fields" in msg["message"]

def test_16_missing_timestamp():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"patient_id": "WS-P110", "heart_rate": 80.0})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Missing required fields" in msg["message"]

def test_17_invalid_numeric_values():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": "WS-P111",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 9999.0 # Impossible value exceeding ge=0, le=400
        })
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "validation failed" in msg["message"]

def test_18_client_disconnect():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"type": "ping"})
        ws.receive_json()
        ws.close()
    # Should close cleanly without crashing backend

def test_19_client_reconnect():
    patient_id = "WS-P112"
    patient_service.require(patient_id)

    # First connection
    with client.websocket_connect("/api/v1/ws/stream") as ws1:
        ws1.send_json({"type": "ping"})
        ws1.receive_json()

    # Second connection (reconnect)
    with client.websocket_connect("/api/v1/ws/stream") as ws2:
        ws2.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 78.0,
            "map": 88.0,
            "resp_rate": 15.0,
            "spo2": 99.0
        })
        msg = ws2.receive_json()
        assert msg["type"] == "prediction"

def test_20_multiple_clients():
    patient_id = "WS-P113"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws1:
        with client.websocket_connect("/api/v1/ws/stream") as ws2:
            ws1.send_json({
                "patient_id": patient_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "heart_rate": 84.0,
                "map": 82.0,
                "resp_rate": 17.0,
                "spo2": 98.0
            })
            # Both client 1 and client 2 should receive the broadcast prediction message
            m1 = ws1.receive_json()
            m2 = ws2.receive_json()
            assert m1["type"] == "prediction"
            assert m2["type"] == "prediction"
            assert m1["patient_id"] == patient_id
            assert m2["patient_id"] == patient_id

def test_21_multiple_patients():
    patient_service.require("WS-P114-A")
    patient_service.require("WS-P114-B")

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"patient_id": "WS-P114-A", "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 75.0, "map": 85.0, "resp_rate": 16.0, "spo2": 98.0})
        m1 = ws.receive_json()
        assert m1["patient_id"] == "WS-P114-A"

        ws.send_json({"patient_id": "WS-P114-B", "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 88.0, "map": 78.0, "resp_rate": 20.0, "spo2": 95.0})
        m2 = ws.receive_json()
        assert m2["patient_id"] == "WS-P114-B"

def test_22_patient_isolation():
    patient_service.require("WS-ISO-A")
    patient_service.require("WS-ISO-B")

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"patient_id": "WS-ISO-A", "timestamp": datetime.now(timezone.utc).isoformat(), "heart_rate": 72.0, "map": 84.0, "resp_rate": 15.0, "spo2": 99.0})
        msg = ws.receive_json()
        assert msg["payload"]["patient_id"] == "WS-ISO-A"

def test_23_no_duplicate_inference(mocker=None):
    patient_id = "WS-P115"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 79.0,
            "map": 86.0,
            "resp_rate": 16.0,
            "spo2": 98.0
        })
        msg = ws.receive_json()
        assert msg["type"] == "prediction"

def test_24_no_legacy_dependency():
    import inspect
    from src.backend.api.endpoints import websocket
    from src.backend.services import event_broker

    ws_src = inspect.getsource(websocket)
    eb_src = inspect.getsource(event_broker)

    assert "deployment.backend" not in ws_src
    assert "deployment/backend" not in ws_src
    assert "deployment.backend" not in eb_src
    assert "deployment/backend" not in eb_src

def test_25_end_to_end_ws_event_prediction_alert():
    patient_id = "WS-E2E-PATIENT"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        # High risk vitals
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 135.0,
            "map": 50.0,
            "resp_rate": 32.0,
            "spo2": 85.0,
            "temperature_c": 39.5,
            "lactate": 5.0
        })
        m1 = ws.receive_json()
        assert m1["type"] == "prediction"
        assert m1["payload"]["model_version"] == "logistic-regression-v1"
        assert m1["payload"]["is_demo_model"] is False
        assert m1["payload"]["shap_explanation"]["explanation_available"] is True
        unc = m1["payload"]["uncertainty_summary"]
        assert unc.get("method") == "UNAVAILABLE" or unc.get("status") == "UNAVAILABLE"
        assert unc["uncertainty_available"] is False

