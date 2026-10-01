"""
Fake External Part 2 Consumer & Final Integration Contract Test Suite.

Simulates a completely isolated external consumer reading only raw JSON payloads over HTTP REST
and WebSockets without importing any ARGUS internal Python modules.
"""

from datetime import datetime, timedelta, timezone
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.patient_registry import patient_registry
from app.services.simulation_service import simulation_service
from app.streaming.manager import stream_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    patient_registry.clear()
    simulation_service.stop_simulation()


class StandalonePart2Consumer:
    """
    Fake External Part 2 Consumer.
    Uses ONLY raw JSON dictionary parsing over HTTP & WebSockets.
    Imports NO ARGUS internal simulation or schema Python code.
    """

    def __init__(self):
        self.received_messages = []
        self.patient_timelines = {}

    def ingest_json_message(self, json_str: str):
        data = json.loads(json_str)

        # 1. Identity & Header Validation
        assert "schema_version" in data, "Missing schema_version"
        assert data["schema_version"] == "1.0", f"Unexpected schema_version {data['schema_version']}"
        assert "patient_id" in data and len(data["patient_id"]) > 0, "Missing or empty patient_id"
        assert "session_id" in data and len(data["session_id"]) > 0, "Missing or empty session_id"
        assert "timestamp" in data, "Missing wall-clock timestamp"
        assert "simulation_time" in data, "Missing simulation_time"
        assert "message_type" in data, "Missing message_type"

        # 2. Chronological Timeline Verification per Patient
        p_id = data["patient_id"]
        sim_time = datetime.fromisoformat(data["simulation_time"].replace("Z", "+00:00"))

        if p_id not in self.patient_timelines:
            self.patient_timelines[p_id] = []

        if self.patient_timelines[p_id]:
            last_sim_time = self.patient_timelines[p_id][-1]["simulation_time"]
            assert sim_time >= last_sim_time, f"Non-chronological timestamp jump: {sim_time} < {last_sim_time}"

        # 3. Message Type Specific Validation
        m_type = data["message_type"]

        if m_type == "vital_update":
            assert "vitals" in data, "Missing vitals field in vital_update"
            vitals = data["vitals"]
            # Verify 6 mandatory vital sign keys exist in contract dict
            for key in ["heart_rate", "systolic_bp", "diastolic_bp", "spo2", "temperature", "respiratory_rate"]:
                assert key in vitals, f"Missing vital field key '{key}'"

            assert "quality_status" in data, "Missing quality_status"
            assert "scenario_state" in data, "Missing scenario_state"

        elif m_type == "sensor_event":
            assert "sensor_type" in data, "Missing sensor_type"
            assert "event_type" in data, "Missing event_type"

        elif m_type == "simulation_event":
            assert "event_type" in data, "Missing event_type"

        self.received_messages.append(data)
        self.patient_timelines[p_id].append({"simulation_time": sim_time, "data": data})
        return data


def test_part2_consumer_websocket_integration():
    consumer = StandalonePart2Consumer()

    # 1. Create Patient via REST API
    res = client.post("/api/v1/patients", json={"profile_type": "standard", "seed": 42})
    assert res.status_code == 201
    patient_data = res.json()
    p_id = patient_data["patient_id"]
    sess_id = patient_data["session_id"]

    # 2. Connect Fake Consumer to WebSocket Stream
    with client.websocket_connect(f"/api/v1/stream/{sess_id}") as ws:
        # Start simulation at 5x speed
        start_res = client.post("/api/v1/simulation/start", json={"patient_id": p_id, "speed_factor": 5.0})
        assert start_res.status_code == 200

        # Generate & broadcast telemetry frame
        import asyncio
        from app.simulation.patient_generator import PatientFactory
        from app.simulation.vital_generator import VitalSignGenerator

        patient = PatientFactory.create_patient(patient_id=p_id, session_id=sess_id, seed=42)
        gen = VitalSignGenerator(patient, seed=42)
        sim_t = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

        msg = gen.generate_vitals(simulation_time=sim_t)
        asyncio.run(stream_manager.broadcast(msg, session_id=sess_id))

        # Consumer receives raw string frame
        raw_text = ws.receive_text()
        ingested = consumer.ingest_json_message(raw_text)

        assert ingested["patient_id"] == p_id
        assert ingested["session_id"] == sess_id
        assert ingested["vitals"]["heart_rate"] == msg.vitals.heart_rate


def test_part2_consumer_missing_data_and_fault_representation():
    consumer = StandalonePart2Consumer()
    p_id = "P-CONSUMER-FAULT"
    sess_id = "SESS-CONSUMER-FAULT"

    # Simulated sensor failure frame (null SpO2)
    raw_fault_json = json.dumps({
        "schema_version": "1.0",
        "message_type": "vital_update",
        "patient_id": p_id,
        "session_id": sess_id,
        "source": "synthetic",
        "timestamp": "2026-10-01T12:00:00.000Z",
        "simulation_time": "2026-10-01T12:00:00.000Z",
        "vitals": {
            "heart_rate": 82.0,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0,
            "spo2": None,  # Explicit NULL representation
            "temperature": 36.8,
            "respiratory_rate": 16.0
        },
        "vital_units": {
            "heart_rate": "bpm",
            "systolic_bp": "mmHg",
            "diastolic_bp": "mmHg",
            "spo2": "%",
            "temperature": "°C",
            "respiratory_rate": "breaths/min"
        },
        "quality_status": "sensor_unavailable",
        "scenario_state": "sensor_failure"
    })

    data = consumer.ingest_json_message(raw_fault_json)
    assert data["vitals"]["spo2"] is None
    assert data["vitals"]["heart_rate"] == 82.0
    assert data["quality_status"] == "sensor_unavailable"


def test_part2_consumer_four_hour_historical_timeline_reconstruction():
    consumer = StandalonePart2Consumer()
    p_id = "P-HIST-4H"
    sess_id = "SESS-HIST-4H"
    start_time = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)

    # Ingest 4 hours (240 minutes) of 1-minute sampled telemetry frames
    for minute in range(240):
        t_sim = start_time + timedelta(minutes=minute)
        raw_frame = json.dumps({
            "schema_version": "1.0",
            "message_type": "vital_update",
            "patient_id": p_id,
            "session_id": sess_id,
            "source": "synthetic",
            "timestamp": "2026-10-01T12:00:00.000Z",
            "simulation_time": t_sim.isoformat(),
            "vitals": {
                "heart_rate": 75.0 + (minute * 0.05),
                "systolic_bp": 120.0 - (minute * 0.05),
                "diastolic_bp": 80.0 - (minute * 0.03),
                "spo2": 98.0,
                "temperature": 36.8,
                "respiratory_rate": 16.0
            },
            "quality_status": "valid",
            "scenario_state": "gradual_deterioration"
        })
        consumer.ingest_json_message(raw_frame)

    timeline = consumer.patient_timelines[p_id]
    assert len(timeline) == 240
    # Verify span is exactly 4 hours (239 minutes between first and last)
    span = timeline[-1]["simulation_time"] - timeline[0]["simulation_time"]
    assert span == timedelta(hours=3, minutes=59)


@pytest.mark.parametrize("speed", [1.0, 5.0, 10.0, 30.0, 60.0])
def test_all_simulation_speeds_control_api(speed):
    start_res = client.post("/api/v1/simulation/start", json={"speed_factor": speed})
    assert start_res.status_code == 200
    data = start_res.json()
    assert data["clock_status"]["speed_factor"] == speed


@pytest.mark.parametrize("scenario", [
    "stable",
    "gradual_deterioration",
    "rapid_deterioration",
    "recovery",
    "noisy",
    "sensor_failure",
    "data_quality_problem",
])
def test_all_supported_scenarios_rest_control(scenario):
    p_res = client.post("/api/v1/patients", json={"profile_type": "standard"})
    patient_id = p_res.json()["patient_id"]

    sc_res = client.post(f"/api/v1/patients/{patient_id}/scenario", json={"scenario_name": scenario})
    assert sc_res.status_code == 200
    data = sc_res.json()
    assert data["active_scenario_name"] == scenario
