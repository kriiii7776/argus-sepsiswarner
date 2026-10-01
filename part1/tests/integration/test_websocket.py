"""
Integration tests for WebSocket streaming endpoints and real-time broadcast.
"""

from datetime import datetime, timedelta, timezone
import json
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.main import app
from app.schemas.contract import (
    MessageType,
    QualityStatus,
    ScenarioState,
    VitalSignSet,
    VitalUpdateMessage,
)
from app.simulation.patient_generator import PatientFactory
from app.simulation.vital_generator import VitalSignGenerator
from app.streaming.manager import stream_manager

client = TestClient(app)


@pytest.mark.asyncio
async def test_websocket_connection_and_disconnect():
    with client.websocket_connect("/api/v1/stream") as websocket:
        # Connection established successfully
        assert websocket is not None

    # Disconnect handled gracefully
    assert stream_manager.connection_count == 0


def test_websocket_broadcast_vital_update_schema_validation():
    patient = PatientFactory.create_patient(seed=42)
    generator = VitalSignGenerator(patient, seed=42)

    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    wall_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    vital_msg = generator.generate_vitals(simulation_time=sim_time, wall_timestamp=wall_time)

    with client.websocket_connect(f"/api/v1/stream/{patient.session_id}") as websocket:
        # Broadcast vital update asynchronously
        import asyncio
        asyncio.run(stream_manager.broadcast(vital_msg, session_id=patient.session_id))

        # Receive text frame
        data = websocket.receive_text()
        json_payload = json.loads(data)

        # Validate strictly against contract schema
        received_msg = VitalUpdateMessage(**json_payload)
        assert received_msg.schema_version == "1.0"
        assert received_msg.message_type == MessageType.VITAL_UPDATE
        assert received_msg.patient_id == patient.patient_id
        assert received_msg.session_id == patient.session_id
        assert received_msg.vitals.heart_rate == vital_msg.vitals.heart_rate
        assert received_msg.vitals.systolic_bp == vital_msg.vitals.systolic_bp
        assert received_msg.quality_status == QualityStatus.VALID


def test_websocket_multi_client_broadcast():
    patient = PatientFactory.create_patient(seed=101)
    generator = VitalSignGenerator(patient, seed=101)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    vital_msg = generator.generate_vitals(simulation_time=sim_time)

    with client.websocket_connect("/api/v1/stream") as ws1:
        with client.websocket_connect("/api/v1/stream") as ws2:
            import asyncio
            asyncio.run(stream_manager.broadcast(vital_msg))

            # Both clients receive the same broadcast message
            data1 = ws1.receive_text()
            data2 = ws2.receive_text()

            msg1 = VitalUpdateMessage(**json.loads(data1))
            msg2 = VitalUpdateMessage(**json.loads(data2))

            assert msg1.patient_id == msg2.patient_id
            assert msg1.vitals.heart_rate == msg2.vitals.heart_rate


def test_websocket_session_filtering_multiple_patients():
    p1 = PatientFactory.create_patient(patient_id="P-1", session_id="SESS-1", seed=1)
    p2 = PatientFactory.create_patient(patient_id="P-2", session_id="SESS-2", seed=2)

    gen1 = VitalSignGenerator(p1, seed=1)
    gen2 = VitalSignGenerator(p2, seed=2)

    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    msg1 = gen1.generate_vitals(simulation_time=sim_time)
    msg2 = gen2.generate_vitals(simulation_time=sim_time)

    # ws1 listens to SESS-1, ws2 listens to SESS-2
    with client.websocket_connect("/api/v1/stream?session_id=SESS-1") as ws1:
        with client.websocket_connect("/api/v1/stream?session_id=SESS-2") as ws2:
            import asyncio
            asyncio.run(stream_manager.broadcast(msg1, session_id="SESS-1"))

            data1 = ws1.receive_text()
            recv1 = VitalUpdateMessage(**json.loads(data1))
            assert recv1.patient_id == "P-1"
            assert recv1.session_id == "SESS-1"

            asyncio.run(stream_manager.broadcast(msg2, session_id="SESS-2"))
            data2 = ws2.receive_text()
            recv2 = VitalUpdateMessage(**json.loads(data2))
            assert recv2.patient_id == "P-2"
            assert recv2.session_id == "SESS-2"


def test_websocket_chronological_simulation_time_stream():
    patient = PatientFactory.create_patient(seed=50)
    generator = VitalSignGenerator(patient, seed=50)
    start_sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    with client.websocket_connect("/api/v1/stream") as ws:
        import asyncio
        for sec in range(3):
            sim_t = start_sim_time + timedelta(seconds=sec)
            msg = generator.generate_vitals(simulation_time=sim_t)
            asyncio.run(stream_manager.broadcast(msg))

            raw_text = ws.receive_text()
            parsed_msg = VitalUpdateMessage(**json.loads(raw_text))
            assert parsed_msg.simulation_time == sim_t
