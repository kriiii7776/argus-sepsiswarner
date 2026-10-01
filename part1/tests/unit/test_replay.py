"""
Unit tests for CSV, JSON, and MIMIC-IV Replay Subsystem and DataNormalizer.
"""

from datetime import datetime, timezone
import io
import json
import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.schemas.contract import DataSource, MessageType, VitalUpdateMessage
from app.replay.adapters import (
    CSVReplayAdapter,
    DataNormalizer,
    JSONReplayAdapter,
    MIMICIVReplayAdapter,
)
from app.replay.controller import ReplayController


@pytest.fixture
def synthetic_csv_content():
    return """timestamp,patient_id,hr,sbp,dbp,spo2,temp_c,rr
2026-10-01T12:00:00Z,P-CSV-01,75.0,120.0,80.0,98.0,36.8,15.0
2026-10-01T12:01:00Z,P-CSV-01,78.0,118.0,78.0,97.5,36.9,16.0
2026-10-01T12:02:00Z,P-CSV-01,82.0,115.0,75.0,97.0,37.0,18.0
"""


@pytest.fixture
def synthetic_json_content():
    return [
        {
            "timestamp": "2026-10-01T12:00:00Z",
            "patient_id": "P-JSON-01",
            "heart_rate": 80.0,
            "systolic_bp": 125.0,
            "diastolic_bp": 82.0,
            "spo2": 99.0,
            "temperature": 37.1,
            "respiratory_rate": 14.0,
        },
        {
            "timestamp": "2026-10-01T12:01:00Z",
            "patient_id": "P-JSON-01",
            "heart_rate": 85.0,
            "systolic_bp": 122.0,
            "diastolic_bp": 80.0,
            "spo2": 98.5,
            "temperature": 37.2,
            "respiratory_rate": 15.0,
        },
    ]


def test_csv_replay_adapter_and_normalization(synthetic_csv_content):
    adapter = CSVReplayAdapter()
    f_in = io.StringIO(synthetic_csv_content)
    records = adapter.load_records(f_in)

    assert len(records) == 3
    assert records[0]["hr"] == "75.0"

    norm_msg = DataNormalizer.normalize_record(
        raw=records[0],
        patient_id="P-CSV-01",
        session_id="SESS-CSV-01",
        source=DataSource.CSV_REPLAY,
    )

    assert isinstance(norm_msg, VitalUpdateMessage)
    assert norm_msg.source == DataSource.CSV_REPLAY
    assert norm_msg.vitals.heart_rate == 75.0
    assert norm_msg.vitals.systolic_bp == 120.0
    assert norm_msg.vitals.diastolic_bp == 80.0
    assert norm_msg.vitals.spo2 == 98.0
    assert norm_msg.vitals.temperature == 36.8
    assert norm_msg.vitals.respiratory_rate == 15.0


def test_temperature_fahrenheit_conversion():
    raw = {
        "timestamp": "2026-10-01T12:00:00Z",
        "heart_rate": 72.0,
        "temperature": 98.6,  # °F
    }
    msg = DataNormalizer.normalize_record(raw, patient_id="P-1", session_id="SESS-1")
    # 98.6°F -> 37.0°C
    assert msg.vitals.temperature == pytest.approx(37.0, 0.1)


def test_json_replay_adapter(synthetic_json_content):
    adapter = JSONReplayAdapter()
    json_str = json.dumps(synthetic_json_content)
    records = adapter.load_records(json_str)

    assert len(records) == 2
    msg = DataNormalizer.normalize_record(records[0], patient_id="P-JSON-01", session_id="SESS-01")
    assert msg.vitals.heart_rate == 80.0


def test_mimic_iv_replay_adapter():
    mimic_raw_records = [
        {"stay_id": 3001, "charttime": "2026-10-01 12:00:00", "itemid": 220045, "valuenum": 84.0},
        {"stay_id": 3001, "charttime": "2026-10-01 12:00:00", "itemid": 220179, "valuenum": 118.0},
        {"stay_id": 3001, "charttime": "2026-10-01 12:00:00", "itemid": 220277, "valuenum": 96.0},
    ]

    adapter = MIMICIVReplayAdapter()
    records = adapter.load_records(mimic_raw_records)

    assert len(records) == 1
    rec = records[0]
    assert rec["patient_id"] == "P-MIMIC-3001"
    assert rec["heart_rate"] == 84.0
    assert rec["systolic_bp"] == 118.0
    assert rec["spo2"] == 96.0

    msg = DataNormalizer.normalize_record(rec, patient_id=rec["patient_id"], session_id="SESS-MIMIC", source=DataSource.MIMIC_IV)
    assert msg.source == DataSource.MIMIC_IV
    assert msg.patient_id == "P-MIMIC-3001"


def test_replay_controller_chronological_sorting_and_stepping(synthetic_csv_content):
    adapter = CSVReplayAdapter()
    controller = ReplayController(adapter=adapter, source_type=DataSource.CSV_REPLAY)

    f_in = io.StringIO(synthetic_csv_content)
    count = controller.load(f_in, patient_id="P-TEST", session_id="SESS-TEST")

    assert count == 3
    assert controller.speed_factor == 1.0

    # Test stepping
    m1 = controller.step()
    m2 = controller.step()
    m3 = controller.step()
    m_end = controller.step()

    assert m1.simulation_time < m2.simulation_time < m3.simulation_time
    assert m_end is None


def test_replay_controller_speed_control():
    adapter = CSVReplayAdapter()
    controller = ReplayController(adapter=adapter)

    controller.set_speed(10.0)
    assert controller.speed_factor == 10.0

    with pytest.raises(ValueError):
        controller.set_speed(-1.0)
