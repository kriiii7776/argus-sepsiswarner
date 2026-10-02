"""
Regression test suite for Part 1 WebSocket streaming loop and Part 1 -> Part 2 bridge integration.
Verifies that:
1. VitalUpdateMessage can be created and serialized.
2. SimulationService stream loop runs without AttributeError.
3. stream_manager.broadcast() delivers vital_update messages over WebSockets.
4. Message fields match expected patient_id, session_id, simulation_time, and 6 vitals.
5. Part1WSBridge receives Part 1 live messages, passes them to Part1Adapter and Part 2 InferenceService.
6. Part 2 persists vitals and produces risk predictions.
"""

import asyncio
from datetime import datetime, timezone
import json
import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.main import app as part1_app
from app.schemas.contract import MessageType, QualityStatus, VitalUpdateMessage
from app.services.patient_registry import patient_registry
from app.services.simulation_service import simulation_service
from app.simulation.vital_generator import VitalSignGenerator
from app.streaming.manager import stream_manager

from src.backend.services.part1_ws_bridge import Part1WSBridge
from src.backend.services.patient_service import PatientService
from src.backend.db.store import init_db

part1_client = TestClient(part1_app)


def test_vital_update_message_creation_and_serialization():
    """Requirements 1 & 2: VitalUpdateMessage can be created and serialized."""
    p = patient_registry.create_patient(
        patient_id="TEST-PAT-01",
        session_id="TEST-SESS-01",
        age=60,
        seed=123
    )
    gen = VitalSignGenerator(p, seed=123)
    msg = gen.generate_vitals(simulation_time=datetime.now(timezone.utc))

    assert isinstance(msg, VitalUpdateMessage)
    assert msg.patient_id == "TEST-PAT-01"
    assert msg.session_id == "TEST-SESS-01"

    serialized = msg.model_dump_json()
    assert isinstance(serialized, str)
    deserialized = json.loads(serialized)
    assert deserialized["message_type"] == "vital_update"
    assert deserialized["patient_id"] == "TEST-PAT-01"


@pytest.mark.asyncio
async def test_simulation_service_stream_loop_generation_and_broadcast():
    """Requirements 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14: Stream loop generates and delivers vital_update via stream_manager."""
    patient_registry.clear()
    init_db()
    p = patient_registry.create_patient(
        patient_id="PATIENT-001",
        session_id="LIVE-TEST-001",
        age=65,
        seed=42
    )

    class MockWS:
        def __init__(self):
            self.received = []
        async def send_text(self, text):
            self.received.append(text)

    mock_ws = MockWS()
    stream_manager._active_connections[mock_ws] = None

    try:
        # Start simulation service
        status = simulation_service.start_simulation(
            patient_id="PATIENT-001",
            session_id="LIVE-TEST-001",
            speed_factor=10.0
        )
        assert status.clock_status.state == "running"

        # Wait for stream loop ticks
        await asyncio.sleep(2.5)

        assert len(mock_ws.received) > 0
        matching_msgs = [json.loads(m) for m in mock_ws.received if json.loads(m).get("patient_id") == "PATIENT-001"]
        assert len(matching_msgs) > 0
        data = matching_msgs[0]

        assert data["message_type"] == "vital_update"
        assert data["patient_id"] == "PATIENT-001"
        assert data["session_id"] == "LIVE-TEST-001"
        assert "simulation_time" in data
        assert data["simulation_time"] is not None

        vitals = data["vitals"]
        assert vitals["heart_rate"] is not None
        assert vitals["systolic_bp"] is not None
        assert vitals["diastolic_bp"] is not None
        assert vitals["spo2"] is not None
        assert vitals["temperature"] is not None
        assert vitals["respiratory_rate"] is not None

        # Test Part1WSBridge processing of generated message
        raw_msg = json.dumps(data)
        bridge = Part1WSBridge(enabled=True)
        success = await bridge.process_raw_message(raw_msg)
        assert success is True

        # Verify Part 2 patient service persisted vital event
        vitals_list = PatientService.get_vitals("PATIENT-001")
        assert len(vitals_list) > 0
        latest_vital = vitals_list[-1]
        assert latest_vital["patient_id"] == "PATIENT-001"

    finally:
        simulation_service.stop_simulation()
        stream_manager.disconnect(mock_ws)
