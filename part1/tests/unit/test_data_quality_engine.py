"""
Unit tests for DataQualityEngine per-vital sensor fault injection subsystem.
"""

from datetime import datetime, timedelta, timezone
import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.schemas.contract import QualityStatus, SensorEventMessage
from app.schemas.patient import PatientProfileType
from app.simulation.patient_generator import PatientFactory
from app.simulation.vital_generator import VitalSignGenerator
from app.simulation.noise_sensor import DataQualityEngine, SensorState


@pytest.fixture
def sample_patient_and_gen():
    patient = PatientFactory.create_patient(seed=42, profile_type=PatientProfileType.STANDARD)
    gen = VitalSignGenerator(patient, seed=42)
    return patient, gen


def test_missing_data_explicitly_represented(sample_patient_and_gen):
    patient, gen = sample_patient_and_gen
    quality_engine = DataQualityEngine(seed=42)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Base valid message
    msg = gen.generate_vitals(simulation_time=sim_time)
    assert msg.vitals.spo2 is not None

    # Inject missing fault for spo2
    quality_engine.set_vital_fault("spo2", QualityStatus.MISSING)
    processed_msg = quality_engine.process(msg)

    # Verify spo2 is explicitly None and quality is MISSING without imputation
    assert processed_msg.vitals.spo2 is None
    assert processed_msg.vitals.heart_rate is not None  # HR remains independent & valid!
    assert processed_msg.quality_status == QualityStatus.MISSING


def test_sensor_failure_vs_genuine_low_measurement(sample_patient_and_gen):
    patient, gen = sample_patient_and_gen
    quality_engine = DataQualityEngine(seed=42)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Genuine low SpO2 (e.g. 88%)
    msg_genuine_low = gen.generate_vitals(simulation_time=sim_time)
    # Modify baseline or measurement to simulate genuine low
    msg_genuine_low.vitals.spo2 = 88.0
    msg_genuine_low.quality_status = QualityStatus.VALID

    proc_low = quality_engine.process(msg_genuine_low)
    assert proc_low.vitals.spo2 == 88.0
    assert proc_low.quality_status == QualityStatus.VALID

    # 2. Sensor failure (sensor_unavailable)
    quality_engine.set_vital_fault("spo2", QualityStatus.SENSOR_UNAVAILABLE)
    proc_fault = quality_engine.process(msg_genuine_low)
    assert proc_fault.vitals.spo2 is None
    assert proc_fault.quality_status == QualityStatus.SENSOR_UNAVAILABLE


def test_sensor_disconnection_and_reconnection_events(sample_patient_and_gen):
    patient, gen = sample_patient_and_gen
    quality_engine = DataQualityEngine(seed=42)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Disconnect SpO2 lead
    event_disc, status_disc = quality_engine.inject_sensor_event(
        patient_id=patient.patient_id,
        session_id=patient.session_id,
        vital_name="spo2",
        new_status=QualityStatus.DISCONNECTED,
        simulation_time=sim_time,
    )

    assert isinstance(event_disc, SensorEventMessage)
    assert event_disc.sensor_type == "spo2_sensor"
    assert event_disc.event_type == "disconnected"
    assert quality_engine.sensor_states["spo2"] == SensorState.DISCONNECTED

    # Verify processed vitals set spo2 to None
    msg = gen.generate_vitals(simulation_time=sim_time)
    proc_disc = quality_engine.process(msg)
    assert proc_disc.vitals.spo2 is None

    # Reconnect SpO2 lead
    event_rec, status_rec = quality_engine.inject_sensor_event(
        patient_id=patient.patient_id,
        session_id=patient.session_id,
        vital_name="spo2",
        new_status=QualityStatus.RECONNECTED,
        simulation_time=sim_time + timedelta(seconds=10),
    )

    assert event_rec.event_type == "reconnected"
    quality_engine.clear_vital_fault("spo2")

    msg_after = gen.generate_vitals(simulation_time=sim_time + timedelta(seconds=10))
    proc_rec = quality_engine.process(msg_after)
    assert proc_rec.vitals.spo2 is not None


def test_stale_and_delayed_readings(sample_patient_and_gen):
    patient, gen = sample_patient_and_gen
    quality_engine = DataQualityEngine(seed=42)
    sim_t1 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    sim_t2 = datetime(2026, 10, 1, 12, 0, 1, tzinfo=timezone.utc)

    msg1 = gen.generate_vitals(simulation_time=sim_t1)
    proc1 = quality_engine.process(msg1)
    hr1 = proc1.vitals.heart_rate

    # Generate next tick (which naturally changes slightly)
    msg2 = gen.generate_vitals(simulation_time=sim_t2)

    # Process with stale flag for heart_rate
    proc2_stale = quality_engine.process(msg2, stale_vitals=["heart_rate"])
    assert proc2_stale.vitals.heart_rate == hr1  # Value frozen from tick 1
    assert proc2_stale.quality_status == QualityStatus.STALE


def test_invalid_reading_artifact_no_imputation(sample_patient_and_gen):
    patient, gen = sample_patient_and_gen
    quality_engine = DataQualityEngine(seed=42)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    msg = gen.generate_vitals(simulation_time=sim_time)
    quality_engine.set_vital_fault("heart_rate", QualityStatus.INVALID)
    proc_invalid = quality_engine.process(msg)

    # Verify unphysiological artifact (e.g. 295.0 bpm) is emitted as-is without replacement/imputation
    assert proc_invalid.vitals.heart_rate == 295.0
    assert proc_invalid.quality_status == QualityStatus.INVALID


def test_sudden_sensor_jump(sample_patient_and_gen):
    patient, gen = sample_patient_and_gen
    quality_engine = DataQualityEngine(seed=42)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    msg = gen.generate_vitals(simulation_time=sim_time)
    base_hr = msg.vitals.heart_rate

    # Apply sudden jump artifact (+50 bpm)
    proc_jump = quality_engine.process(msg, jump_vitals={"heart_rate": 50.0})
    assert proc_jump.vitals.heart_rate == pytest.approx(base_hr + 50.0, 0.1)


def test_per_vital_sensor_independence(sample_patient_and_gen):
    patient, gen = sample_patient_and_gen
    quality_engine = DataQualityEngine(seed=42)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    msg = gen.generate_vitals(simulation_time=sim_time)

    # SpO2 disconnected, RR stale, HR valid
    quality_engine.set_vital_fault("spo2", QualityStatus.DISCONNECTED)
    quality_engine.set_vital_fault("respiratory_rate", QualityStatus.STALE)

    proc_msg = quality_engine.process(msg)
    assert proc_msg.vitals.spo2 is None
    assert proc_msg.vitals.heart_rate is not None
    assert proc_msg.vitals.respiratory_rate is not None
