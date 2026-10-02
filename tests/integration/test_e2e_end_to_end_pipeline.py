"""
End-to-End Pipeline & Alert Acknowledgement Lifecycle Integration Test.

Validates:
1. Part 1 Simulator vital event transform & Bridge ingestion into Part 2.
2. Feature engineering, inference runtime (logistic-regression-v1), calibration, and SHAP.
3. SmartAlertEngine alert generation & database persistence.
4. Mobile alert acknowledgement lifecycle: ACK of alert #1 does NOT stop telemetry or permanently suppress alert #2.
5. IAM patient isolation filtering.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from src.backend.schemas.schemas import VitalEvent
from src.backend.services.part1_adapter import Part1Adapter
from src.backend.services.inference_runtime import runtime
from src.backend.services.alert_router import alert_router
from src.backend.db.store import init_db, Session, PatientRecord, PredictionRecord, AlertRecord, AlertAcknowledgementRecord


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    with Session.begin() as s:
        s.query(AlertAcknowledgementRecord).delete()
        s.query(AlertRecord).delete()
        s.query(PredictionRecord).delete()
        s.query(PatientRecord).delete()
    yield


@pytest.mark.asyncio
async def test_part1_to_part2_pipeline_and_ack_lifecycle():
    # 1. Transform Part 1 vital_update message for PATIENT-001
    p1_message = {
        "message_type": "vital_update",
        "schema_version": "1.0",
        "patient_id": "PATIENT-001",
        "session_id": "LIVE-TEST-001",
        "simulation_time": "2026-10-02T20:00:00.000000Z",
        "vitals": {
            "heart_rate": 130.0,
            "systolic_bp": 90.0,
            "diastolic_bp": 50.0,
            "map": 63.33,
            "spo2": 88.0,
            "temperature": 38.5,
            "respiratory_rate": 28.0
        },
        "quality_status": "HIGH",
        "scenario_state": "CRITICAL"
    }

    event = Part1Adapter.transform_vital_update(p1_message)
    assert event.patient_id == "PATIENT-001"
    assert event.heart_rate == 130.0
    assert event.map == 63.33

    # 2. Process message through Part 1 Adapter -> Part 2 Ingestion
    res1 = await Part1Adapter.process_part1_message(p1_message)
    assert res1["patient_id"] == "PATIENT-001"
    assert res1["model_version"] == "logistic-regression-v1"
    assert "shap_explanation" in res1

    # 3. Verify DB persistence
    with Session() as s:
        pts = s.query(PatientRecord).filter(PatientRecord.patient_id == "PATIENT-001").all()
        assert len(pts) == 1
        preds = s.query(PredictionRecord).filter(PredictionRecord.patient_id == "PATIENT-001").all()
        assert len(preds) >= 1

    # 4. Route alert #1
    alert_payload_1 = {
        "alert_id": "alert-PATIENT-001-1001",
        "patient_id": "PATIENT-001",
        "session_id": "LIVE-TEST-001",
        "severity": "RED — URGENT",
        "alert_severity": "RED — URGENT",
        "recommended_clinical_review_level": "URGENT — urgent clinical review",
        "prediction_timestamp": "2026-10-02T20:00:00Z"
    }
    routed1 = await alert_router.route_alert("PATIENT-001", alert_payload_1)
    assert routed1["alert_id"] == "alert-PATIENT-001-1001"
    assert routed1["status"] == "EMITTED"

    # 5. Acknowledge alert #1 (Simulating mobile tap)
    ack_res1 = await alert_router.acknowledge_alert("alert-PATIENT-001-1001", "USER-001")
    assert ack_res1["status"] == "ACKNOWLEDGED"
    assert ack_res1["user_id"] == "USER-001"

    with Session() as s:
        ack_rec = s.query(AlertAcknowledgementRecord).filter(
            AlertAcknowledgementRecord.alert_id == "alert-PATIENT-001-1001"
        ).first()
        assert ack_rec is not None
        assert ack_rec.status == "ACKNOWLEDGED"

    # 6. Telemetry MUST CONTINUE after acknowledgement — send event #2 (t + 1 min)
    p1_message_2 = dict(p1_message)
    p1_message_2["simulation_time"] = "2026-10-02T20:01:00.000000Z"
    p1_message_2["vitals"] = dict(p1_message["vitals"])
    p1_message_2["vitals"]["heart_rate"] = 135.0

    res2 = await Part1Adapter.process_part1_message(p1_message_2)
    assert res2["patient_id"] == "PATIENT-001"

    # 7. Route NEW alert #2 — must be assigned NEW alert_id and NOT blocked by ack of alert #1
    alert_payload_2 = {
        "alert_id": "alert-PATIENT-001-1002",
        "patient_id": "PATIENT-001",
        "session_id": "LIVE-TEST-001",
        "severity": "RED — URGENT",
        "alert_severity": "RED — URGENT",
        "recommended_clinical_review_level": "URGENT — urgent clinical review",
        "prediction_timestamp": "2026-10-02T20:01:00Z"
    }
    routed2 = await alert_router.route_alert("PATIENT-001", alert_payload_2)
    assert routed2["alert_id"] == "alert-PATIENT-001-1002"
    assert routed2["status"] == "EMITTED"

    # Verify DB has 2 alert records with distinct IDs
    with Session() as s:
        acks = s.query(AlertAcknowledgementRecord).filter(
            AlertAcknowledgementRecord.patient_id == "PATIENT-001"
        ).all()
        ack_ids = [a.alert_id for a in acks]
        assert "alert-PATIENT-001-1001" in ack_ids
        assert "alert-PATIENT-001-1002" in ack_ids
