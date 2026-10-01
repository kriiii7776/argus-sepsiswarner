"""
SQLAlchemy ORM Models for ARGUS Part 1 Data Source & Simulation Platform.

Stores patients, baselines, sessions, telemetry vital observations, scenario events, and sensor events.
Excludes all Part 2 features (no ML predictions, risk scores, SHAP values, or clinical alerts).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationSessionModel(Base):
    __tablename__ = "simulation_sessions"

    session_id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), default="stopped")
    speed_factor = Column(Float, default=1.0)
    start_time = Column(DateTime(timezone=True), default=utc_now)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    vital_readings = relationship("VitalReadingModel", back_populates="session", cascade="all, delete-orphan")
    scenario_events = relationship("ScenarioEventModel", back_populates="session", cascade="all, delete-orphan")
    sensor_events = relationship("SensorEventModel", back_populates="session", cascade="all, delete-orphan")


class PatientModel(Base):
    __tablename__ = "patients"

    patient_id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("simulation_sessions.session_id", ondelete="SET NULL"), nullable=True, index=True)
    age = Column(Integer, nullable=False)
    sex = Column(String(16), nullable=False)
    profile_type = Column(String(32), nullable=False)
    status = Column(String(32), default="active")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    baseline = relationship("PatientBaselineModel", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    vital_readings = relationship("VitalReadingModel", back_populates="patient", cascade="all, delete-orphan")
    scenario_events = relationship("ScenarioEventModel", back_populates="patient", cascade="all, delete-orphan")
    sensor_events = relationship("SensorEventModel", back_populates="patient", cascade="all, delete-orphan")


class PatientBaselineModel(Base):
    __tablename__ = "patient_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    heart_rate = Column(Float, nullable=False)
    systolic_bp = Column(Float, nullable=False)
    diastolic_bp = Column(Float, nullable=False)
    spo2 = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    respiratory_rate = Column(Float, nullable=False)

    # Relationship
    patient = relationship("PatientModel", back_populates="baseline")


class VitalReadingModel(Base):
    __tablename__ = "vital_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("simulation_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    schema_version = Column(String(16), default="1.0")
    source = Column(String(32), default="synthetic")
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    simulation_time = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Vital signs (null when missing/disconnected)
    heart_rate = Column(Float, nullable=True)
    systolic_bp = Column(Float, nullable=True)
    diastolic_bp = Column(Float, nullable=True)
    spo2 = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    respiratory_rate = Column(Float, nullable=True)

    quality_status = Column(String(32), default="valid")
    scenario_state = Column(String(32), default="stable")

    # Relationships
    patient = relationship("PatientModel", back_populates="vital_readings")
    session = relationship("SimulationSessionModel", back_populates="vital_readings")


class ScenarioEventModel(Base):
    __tablename__ = "scenario_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("simulation_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    simulation_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(String(64), nullable=False)
    previous_state = Column(String(32), nullable=True)
    new_state = Column(String(32), nullable=True)
    speed_factor = Column(Float, nullable=True)

    # Relationships
    patient = relationship("PatientModel", back_populates="scenario_events")
    session = relationship("SimulationSessionModel", back_populates="scenario_events")


class SensorEventModel(Base):
    __tablename__ = "sensor_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("simulation_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    simulation_time = Column(DateTime(timezone=True), nullable=False)
    sensor_type = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)

    # Relationships
    patient = relationship("PatientModel", back_populates="sensor_events")
    session = relationship("SimulationSessionModel", back_populates="sensor_events")
