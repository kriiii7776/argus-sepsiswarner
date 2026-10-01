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
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(24))

class PredictionRecord(Base):
    __tablename__ = 'predictions'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    risk: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(64))

class AlertRecord(Base):
    __tablename__ = 'alerts'
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    severity: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)

def init_db():
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:
        logger.error(f"Database initialization error: {exc}")
        raise

# Ensure tables exist on module load for test & runtime convenience
try:
    init_db()
except Exception:
    logger.warning("Database init failed during initial import (will retry on startup if database becomes available)")


