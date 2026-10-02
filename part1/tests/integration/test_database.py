"""
Integration tests for database persistence, SQLAlchemy models, and repositories.
"""

from datetime import datetime, timezone
import pytest
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.database.session import Base
from app.models.models import PatientModel
from app.database.repositories import (
    EventRepository,
    PatientRepository,
    SessionRepository,
    VitalRepository,
)
from app.schemas.contract import (
    QualityStatus,
    ScenarioState,
    SensorEventMessage,
    SimulationEventMessage,
)
from app.schemas.patient import PatientProfileType
from app.simulation.patient_generator import PatientFactory
from app.simulation.vital_generator import VitalSignGenerator
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def db_session():
    # Use in-memory SQLite for deterministic repository testing
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_session_repository(db_session):
    repo = SessionRepository(db_session)
    sess_model = repo.create_or_update_session(
        session_id="SESS-DB-01",
        patient_id="P-DB-01",
        status="running",
        speed_factor=5.0,
    )

    assert sess_model.session_id == "SESS-DB-01"
    assert sess_model.speed_factor == 5.0

    retrieved = repo.get_session("SESS-DB-01")
    assert retrieved is not None
    assert retrieved.status == "running"


def test_patient_and_baseline_persistence(db_session):
    p_repo = PatientRepository(db_session)
    patient = PatientFactory.create_patient(
        patient_id="P-DB-100",
        session_id="SESS-DB-100",
        profile_type=PatientProfileType.HYPERTENSIVE,
        seed=42,
    )

    p_model = p_repo.save_patient(patient)
    assert p_model.patient_id == "P-DB-100"
    assert p_model.profile_type == "hypertensive"

    # Verify Baseline Relationship
    assert p_model.baseline is not None
    assert p_model.baseline.systolic_bp == patient.baseline.systolic_bp
    assert p_model.baseline.diastolic_bp == patient.baseline.diastolic_bp

    # Query Patient
    retrieved = p_repo.get_patient("P-DB-100")
    assert retrieved is not None
    assert retrieved.age == patient.age


def test_vital_reading_persistence(db_session):
    p_repo = PatientRepository(db_session)
    v_repo = VitalRepository(db_session)

    patient = PatientFactory.create_patient(patient_id="P-VITAL-01", session_id="SESS-VITAL-01", seed=10)
    p_repo.save_patient(patient)

    gen = VitalSignGenerator(patient, seed=10)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    vital_msg = gen.generate_vitals(simulation_time=sim_time)

    v_model = v_repo.save_vital_update(vital_msg)
    assert v_model.id is not None
    assert v_model.patient_id == "P-VITAL-01"
    assert v_model.heart_rate == vital_msg.vitals.heart_rate
    assert v_model.quality_status == QualityStatus.VALID.value

    # List readings for patient
    readings = v_repo.get_readings_for_patient("P-VITAL-01")
    assert len(readings) == 1
    assert readings[0].systolic_bp == vital_msg.vitals.systolic_bp


def test_event_persistence(db_session):
    p_repo = PatientRepository(db_session)
    e_repo = EventRepository(db_session)

    patient = PatientFactory.create_patient(patient_id="P-EVT-01", session_id="SESS-EVT-01")
    p_repo.save_patient(patient)

    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)

    # 1. Sensor Event
    s_msg = SensorEventMessage(
        schema_version="1.0",
        message_type="sensor_event",
        patient_id="P-EVT-01",
        session_id="SESS-EVT-01",
        source="synthetic",
        timestamp=now_utc,
        simulation_time=sim_time,
        sensor_type="ecg_lead",
        event_type="disconnected",
        details="Lead unclipped",
    )
    s_model = e_repo.save_sensor_event(s_msg)
    assert s_model.sensor_type == "ecg_lead"
    assert s_model.event_type == "disconnected"

    # 2. Scenario Simulation Event
    sc_msg = SimulationEventMessage(
        schema_version="1.0",
        message_type="simulation_event",
        patient_id="P-EVT-01",
        session_id="SESS-EVT-01",
        source="synthetic",
        timestamp=now_utc,
        simulation_time=sim_time,
        event_type="scenario_transition",
        previous_state=ScenarioState.STABLE,
        new_state=ScenarioState.GRADUAL_DETERIORATION,
        speed_factor=5.0,
    )
    sc_model = e_repo.save_scenario_event(sc_msg)
    assert sc_model.event_type == "scenario_transition"
    assert sc_model.new_state == "gradual_deterioration"


def test_transaction_rollback(db_session):
    p_repo = PatientRepository(db_session)
    patient = PatientFactory.create_patient(patient_id="P-FAIL-01", session_id="SESS-FAIL-01")
    p_repo.save_patient(patient)

    # Directly insert duplicate PatientModel with same primary key to trigger DB IntegrityError
    dup_model = PatientModel(
        patient_id="P-FAIL-01",
        age=45,
        sex="M",
        profile_type="standard",
        status="active",
    )
    db_session.add(dup_model)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # Verify session remains healthy and operational after rollback
    retrieved = p_repo.get_patient("P-FAIL-01")
    assert retrieved is not None
    assert retrieved.patient_id == "P-FAIL-01"
