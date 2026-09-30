import os
from datetime import datetime
from sqlalchemy import create_engine, String, Float, DateTime, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./sepsisguard.db')
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class PatientRecord(Base):
    __tablename__='patients'; id: Mapped[int]=mapped_column(primary_key=True)
    patient_id: Mapped[str]=mapped_column(String(64), unique=True, index=True)
    source_system: Mapped[str]=mapped_column(String(32)); sex_at_birth: Mapped[str|None]=mapped_column(String(16), nullable=True)
    birth_year: Mapped[int|None]=mapped_column(Integer, nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=datetime.utcnow)
class VitalRecord(Base):
    __tablename__='vital_events'; id: Mapped[int]=mapped_column(primary_key=True)
    patient_id: Mapped[str]=mapped_column(String(64), index=True); timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict]=mapped_column(JSON); source: Mapped[str]=mapped_column(String(24))
class PredictionRecord(Base):
    __tablename__='predictions'; id: Mapped[int]=mapped_column(primary_key=True)
    patient_id: Mapped[str]=mapped_column(String(64), index=True); timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True)
    risk: Mapped[float]=mapped_column(Float); payload: Mapped[dict]=mapped_column(JSON); model_version: Mapped[str]=mapped_column(String(64))
class AlertRecord(Base):
    __tablename__='alerts'; id: Mapped[int]=mapped_column(primary_key=True)
    patient_id: Mapped[str]=mapped_column(String(64), index=True); timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True), index=True)
    severity: Mapped[str]=mapped_column(String(32)); payload: Mapped[dict]=mapped_column(JSON)
def init_db(): Base.metadata.create_all(engine)
