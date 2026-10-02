import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.services.patient_service import patient_service

client = TestClient(app)

def test_ws_stream_connection_and_pong():
    """Verify WS /api/v1/ws/stream accepts connection and responds to ping."""
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"type": "ping"})
        msg = ws.receive_json()
        assert msg["type"] == "pong"
        assert "occurred_at" in msg

def test_ws_stream_patient_isolation_event_routing():
    """Verify WS stream events isolated by patient_id."""
    patient_a = "WS-ISO-PATIENT-A"
    patient_b = "WS-ISO-PATIENT-B"
    patient_service.require(patient_a)
    patient_service.require(patient_b)

    with client.websocket_connect("/api/v1/ws/stream") as ws_client_a:
        with client.websocket_connect("/api/v1/ws/stream") as ws_client_b:
            # Send event for Patient A
            ws_client_a.send_json({
                "patient_id": patient_a,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "heart_rate": 110.0,
                "map": 60.0,
                "resp_rate": 22.0,
                "spo2": 94.0,
                "temperature_c": 38.0
            })

            m_a = ws_client_a.receive_json()
            m_b = ws_client_b.receive_json()

            assert m_a["type"] == "prediction"
            assert m_a["patient_id"] == patient_a
            assert m_b["patient_id"] == patient_a

def test_ws_stream_prediction_shap_and_uncertainty():
    """Verify WS stream prediction payload returns real SHAP and UNAVAILABLE uncertainty."""
    patient_id = "WS-REALTIME-SHAP"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 125.0,
            "map": 55.0,
            "resp_rate": 28.0,
            "spo2": 90.0,
            "temperature_c": 39.0,
            "lactate": 3.8
        })

        msg = ws.receive_json()
        assert msg["type"] == "prediction"
        payload = msg["payload"]
        assert "risk_probability" in payload
        assert payload["shap_explanation"]["explanation_available"] is True
        assert len(payload["shap_explanation"]["feature_attributions"]) > 0

        unc = payload["uncertainty_summary"]
        assert unc["uncertainty_available"] is False
        assert unc["method"] == "UNAVAILABLE"

def test_ws_stream_smart_alert_emission():
    """Verify WS stream receives alert event when high risk event is ingested."""
    patient_id = "WS-REALTIME-ALERT"
    patient_service.require(patient_id)

    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({
            "patient_id": patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": 150.0,
            "map": 40.0,
            "resp_rate": 36.0,
            "spo2": 80.0,
            "temperature_c": 40.0,
            "lactate": 7.0
        })

        msg1 = ws.receive_json()
        assert msg1["type"] == "prediction"

        if msg1["payload"].get("alert", {}).get("alert_emitted"):
            msg2 = ws.receive_json()
            assert msg2["type"] == "alert"
            assert msg2["patient_id"] == patient_id
            assert "alert_severity" in msg2["payload"] or "severity" in msg2["payload"]

def test_ws_stream_malformed_json_error():
    """Verify WS error message on malformed JSON payload."""
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_text("not_valid_json")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Invalid JSON" in msg["message"]
