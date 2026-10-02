"""
Database Repository / DAO pattern implementation for ARGUS Part 1.

Provides transactional persistence abstractions for patients, baselines, sessions, vitals, and events.
"""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.models import (
    PatientBaselineModel,
    PatientModel,
    ScenarioEventModel,
    SensorEventModel,
    SimulationSessionModel,
    VitalReadingModel,
)
from app.schemas.contract import SensorEventMessage, SimulationEventMessage, VitalUpdateMessage
from app.schemas.patient import Patient, PatientBaseline, PatientStatus


class SessionRepository:
    """
    Repository for managing simulation session metadata.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_or_update_session(
        self,
        session_id: str,
        patient_id: Optional[str] = None,
        status: str = "running",
        speed_factor: float = 1.0,
    ) -> SimulationSessionModel:
        sess = self.db.query(SimulationSessionModel).filter_by(session_id=session_id).first()
        if not sess:
            sess = SimulationSessionModel(
                session_id=session_id,
                patient_id=patient_id,
                status=status,
                speed_factor=speed_factor,
                start_time=datetime.now(timezone.utc),
            )
            self.db.add(sess)
        else:
            sess.status = status
            sess.speed_factor = speed_factor
            if patient_id:
                sess.patient_id = patient_id
        self.db.commit()
        self.db.refresh(sess)
        return sess

    def get_session(self, session_id: str) -> Optional[SimulationSessionModel]:
        return self.db.query(SimulationSessionModel).filter_by(session_id=session_id).first()


class PatientRepository:
    """
    Repository for persisting patient demography and physiological baselines.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_patient(self, patient: Patient) -> PatientModel:
        # Check if session exists, create if missing
        if patient.session_id:
            sess_repo = SessionRepository(self.db)
            sess_repo.create_or_update_session(session_id=patient.session_id, patient_id=patient.patient_id)

        p_model = self.db.query(PatientModel).filter_by(patient_id=patient.patient_id).first()
        if not p_model:
            p_model = PatientModel(
                patient_id=patient.patient_id,
                session_id=patient.session_id,
                age=patient.age,
                sex=patient.sex.value,
                profile_type=patient.profile_type.value,
                status=patient.status.value,
            )
            self.db.add(p_model)
            self.db.flush()

            # Create Baseline
            base = patient.baseline
            b_model = PatientBaselineModel(
                patient_id=patient.patient_id,
                heart_rate=base.heart_rate,
                systolic_bp=base.systolic_bp,
                diastolic_bp=base.diastolic_bp,
                spo2=base.spo2,
                temperature=base.temperature,
                respiratory_rate=base.respiratory_rate,
            )
            self.db.add(b_model)
        else:
            p_model.status = patient.status.value
            p_model.session_id = patient.session_id

        self.db.commit()
        self.db.refresh(p_model)
        return p_model

    def get_patient(self, patient_id: str) -> Optional[PatientModel]:
        return self.db.query(PatientModel).filter_by(patient_id=patient_id).first()

    def list_patients(self, status: Optional[PatientStatus] = None) -> List[PatientModel]:
        q = self.db.query(PatientModel)
        if status:
            q = q.filter_by(status=status.value)
        return q.all()


class VitalRepository:
    """
    Repository for persisting vital sign telemetry readings.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_vital_update(self, msg: VitalUpdateMessage) -> VitalReadingModel:
        reading = VitalReadingModel(
            patient_id=msg.patient_id,
            session_id=msg.session_id,
            schema_version=msg.schema_version,
            source=msg.source,
            timestamp=msg.timestamp,
            simulation_time=msg.simulation_time,
            heart_rate=msg.vitals.heart_rate,
            systolic_bp=msg.vitals.systolic_bp,
            diastolic_bp=msg.vitals.diastolic_bp,
            spo2=msg.vitals.spo2,
            temperature=msg.vitals.temperature,
            respiratory_rate=msg.vitals.respiratory_rate,
            quality_status=msg.quality_status.value,
            scenario_state=msg.scenario_state.value,
        )
        self.db.add(reading)
        self.db.commit()
        self.db.refresh(reading)
        return reading

    def get_readings_for_patient(self, patient_id: str, limit: int = 100) -> List[VitalReadingModel]:
        return (
            self.db.query(VitalReadingModel)
            .filter_by(patient_id=patient_id)
            .order_by(VitalReadingModel.simulation_time.desc())
            .limit(limit)
            .all()
        )


class EventRepository:
    """
    Repository for persisting scenario state transitions and sensor lead events.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_sensor_event(self, msg: SensorEventMessage) -> SensorEventModel:
        event = SensorEventModel(
            patient_id=msg.patient_id,
            session_id=msg.session_id,
            timestamp=msg.timestamp,
            simulation_time=msg.simulation_time,
            sensor_type=msg.sensor_type,
            event_type=msg.event_type,
            details=msg.details,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def save_scenario_event(self, msg: SimulationEventMessage) -> ScenarioEventModel:
        event = ScenarioEventModel(
            patient_id=msg.patient_id,
            session_id=msg.session_id,
            timestamp=msg.timestamp,
            simulation_time=msg.simulation_time,
            event_type=msg.event_type,
            previous_state=msg.previous_state.value if msg.previous_state else None,
            new_state=msg.new_state.value if msg.new_state else None,
            speed_factor=msg.speed_factor,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
