import os
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Float, DateTime, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from src.backend.core.config import settings

logger = logging.getLogger('sepsisguard.db')

def get_database_url() -> str:
    return os.getenv('DATABASE_URL') or getattr(settings, 'database_url', None) or 'sqlite:///./sepsisguard.db'

DATABASE_URL = get_database_url()

engine_kwargs = {
    'pool_pre_ping': True,
}

if DATABASE_URL.startswith('postgresql'):
    # Production-grade connection pool settings for PostgreSQL
    engine_kwargs.update({
        'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
        'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '1800')),
    })
elif DATABASE_URL.startswith('sqlite'):
    engine_kwargs['connect_args'] = {'check_same_thread': False}
    if ':memory:' in DATABASE_URL:
        from sqlalchemy.pool import StaticPool
        engine_kwargs['poolclass'] = StaticPool

engine = create_engine(DATABASE_URL, **engine_kwargs)
Session = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class PatientRecord(Base):
    __tablename__ = 'patients'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_system: Mapped[str] = mapped_column(String(32))
    sex_at_birth: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class VitalRecord(Base):
    __tablename__ = 'vital_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(24))

class PredictionRecord(Base):
    __tablename__ = 'predictions'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    risk: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(64))

class AlertRecord(Base):
    __tablename__ = 'alerts'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    severity: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)

class StaffRecord(Base):
    __tablename__ = 'staff_users'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32)) # DOCTOR, NURSE, ICU_ADMIN
    assigned_unit: Mapped[str] = mapped_column(String(64), default='ICU-A')
    active: Mapped[bool] = mapped_column(default=True)
    notification_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PatientAssignmentRecord(Base):
    __tablename__ = 'patient_assignments'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class DeviceRegistrationRecord(Base):
    __tablename__ = 'device_registrations'
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32), default='android')
    push_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AlertAcknowledgementRecord(Base):
    __tablename__ = 'alert_acknowledgements'
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default='EMITTED') # EMITTED, DELIVERED, VIEWED, ACKNOWLEDGED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

def seed_default_track_b_data():
    with Session.begin() as s:
        if s.query(StaffRecord).count() == 0:
            s.add_all([
                StaffRecord(user_id='ADMIN-001', name='Admin Sarah', role='ADMIN', assigned_unit='ICU-SYSTEM'),
                StaffRecord(user_id='USER-001', name='Dr. Arun', role='DOCTOR', assigned_unit='ICU-A'),
                StaffRecord(user_id='USER-002', name='Nurse Priya', role='NURSE', assigned_unit='ICU-A'),
                StaffRecord(user_id='USER-003', name='Dr. Vikram', role='DOCTOR', assigned_unit='ICU-A'),
                StaffRecord(user_id='USER-004', name='Nurse Sunita', role='NURSE', assigned_unit='ICU-A'),
            ])
        if s.query(PatientAssignmentRecord).count() == 0:
            s.add_all([
                PatientAssignmentRecord(patient_id='PATIENT-001', user_id='USER-001'),
                PatientAssignmentRecord(patient_id='PATIENT-001', user_id='USER-002'),
                PatientAssignmentRecord(patient_id='PATIENT-002', user_id='USER-001'),
                PatientAssignmentRecord(patient_id='PATIENT-002', user_id='USER-002'),
                PatientAssignmentRecord(patient_id='PATIENT-003', user_id='USER-003'),
                PatientAssignmentRecord(patient_id='PATIENT-003', user_id='USER-004'),
                PatientAssignmentRecord(patient_id='PATIENT-004', user_id='USER-003'),
                PatientAssignmentRecord(patient_id='PATIENT-004', user_id='USER-004'),
            ])
        if s.query(DeviceRegistrationRecord).count() == 0:
            s.add_all([
                DeviceRegistrationRecord(device_id='DEVICE-001', user_id='USER-001', platform='android'),
                DeviceRegistrationRecord(device_id='DEVICE-002', user_id='USER-002', platform='android'),
                DeviceRegistrationRecord(device_id='DEVICE-003', user_id='USER-003', platform='android'),
                DeviceRegistrationRecord(device_id='DEVICE-004', user_id='USER-004', platform='android'),
            ])

def init_db():
    try:
        Base.metadata.create_all(engine)
        # Additive migration for databases created before session traceability.
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        with engine.begin() as connection:
            for table in ('vital_events', 'predictions', 'alerts'):
                if table in inspector.get_table_names() and 'session_id' not in {
                    column['name'] for column in inspector.get_columns(table)
                }:
                    connection.execute(text(f'ALTER TABLE {table} ADD COLUMN session_id VARCHAR(128)'))

            if 'staff_users' in inspector.get_table_names() and 'notification_preferences' not in {
                column['name'] for column in inspector.get_columns('staff_users')
            }:
                connection.execute(text('ALTER TABLE staff_users ADD COLUMN notification_preferences JSON'))
        seed_default_track_b_data()
    except Exception as exc:
        logger.error(f"Database initialization error: {exc}")
        raise

# Ensure tables exist on module load for test & runtime convenience
try:
    init_db()
except Exception:
    logger.warning("Database init failed during initial import (will retry on startup if database becomes available)")

