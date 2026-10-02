"""
Unit tests for VitalSignGenerator subsystem.
"""

from datetime import datetime, timedelta, timezone
import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.schemas.contract import MessageType, QualityStatus, ScenarioState, VitalUpdateMessage
from app.schemas.patient import PatientProfileType
from app.simulation.patient_generator import PatientFactory
from app.simulation.vital_generator import VitalSignGenerator


@pytest.fixture
def sample_patient():
    return PatientFactory.create_patient(seed=123, profile_type=PatientProfileType.STANDARD)


def test_vital_sign_generation(sample_patient):
    generator = VitalSignGenerator(sample_patient, seed=456)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    wall_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    msg = generator.generate_vitals(simulation_time=sim_time, wall_timestamp=wall_time)

    assert isinstance(msg, VitalUpdateMessage)
    assert msg.message_type == MessageType.VITAL_UPDATE
    assert msg.patient_id == sample_patient.patient_id
    assert msg.session_id == sample_patient.session_id

    # Check vitals are close to patient baseline
    base = sample_patient.baseline
    assert abs(msg.vitals.heart_rate - base.heart_rate) <= 15.0
    assert abs(msg.vitals.systolic_bp - base.systolic_bp) <= 15.0
    assert abs(msg.vitals.diastolic_bp - base.diastolic_bp) <= 15.0
    assert msg.vitals.diastolic_bp < msg.vitals.systolic_bp


def test_vital_generator_deterministic_seed(sample_patient):
    gen1 = VitalSignGenerator(sample_patient, seed=999)
    gen2 = VitalSignGenerator(sample_patient, seed=999)

    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    msg1 = gen1.generate_vitals(simulation_time=sim_time)
    msg2 = gen2.generate_vitals(simulation_time=sim_time)

    assert msg1.vitals.heart_rate == msg2.vitals.heart_rate
    assert msg1.vitals.systolic_bp == msg2.vitals.systolic_bp
    assert msg1.vitals.spo2 == msg2.vitals.spo2


def test_vital_generator_time_series_continuity(sample_patient):
    generator = VitalSignGenerator(sample_patient, seed=42)
    start_sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    previous_hr = None
    for sec in range(10):
        t = start_sim_time + timedelta(seconds=sec)
        msg = generator.generate_vitals(simulation_time=t)
        if previous_hr is not None:
            # HR change between consecutive seconds should be continuous (e.g. <= 5.0 bpm)
            assert abs(msg.vitals.heart_rate - previous_hr) < 5.0
        previous_hr = msg.vitals.heart_rate
