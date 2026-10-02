import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from src.backend.schemas.schemas import PatientCreate, Patient, Vital
from src.backend.db.repositories import patient_repository
from src.backend.core.exceptions import NotFoundException

class PatientService:
    repo = patient_repository
    _names_cache: dict[str, str] = {}

    @classmethod
    def create_patient(cls, payload: PatientCreate) -> Patient:
        p_id = getattr(payload, 'patient_id', None) or str(uuid.uuid4())
        name = getattr(payload, 'name', None) or f"Patient {p_id[:8]}"
        age = getattr(payload, 'age', 50) if getattr(payload, 'age', 50) is not None else 50
        history = getattr(payload, 'medical_history', []) or []
        
        cls._names_cache[p_id] = name

        existing = cls.repo.get(p_id)
        if not existing:
            cls.repo.create({
                "patient_id": p_id,
                "source_system": getattr(payload, 'source_system', 'local') or 'local',
                "sex_at_birth": getattr(payload, 'sex_at_birth', None),
                "birth_year": getattr(payload, 'birth_year', None),
                "created_at": datetime.now(timezone.utc)
            })
        
        return Patient(
            id=p_id,
            name=name,
            age=age,
            medical_history=history
        )

    @classmethod
    def require(cls, patient_id: str):
        row = cls.repo.get(patient_id)
        if not row:
            row = cls.repo.create({
                "patient_id": patient_id,
                "source_system": 'local',
                "created_at": datetime.now(timezone.utc)
            })
        return row

    @classmethod
    def get_patient(cls, patient_id: str) -> Patient:
        row = cls.repo.get(patient_id)
        if not row:
            raise NotFoundException(f"Patient {patient_id} not found")
        default_name = row.patient_id if row.patient_id.startswith("MIMIC") else f"Patient {row.patient_id}"
        cached_name = cls._names_cache.get(row.patient_id, default_name)
        return Patient(
            id=row.patient_id,
            name=cached_name,
            age=50,
            medical_history=[]
        )

    @classmethod
    def get_vitals(cls, patient_id: str):
        cls.require(patient_id)
        rows = cls.repo.vitals(patient_id)
        return [r.payload for r in reversed(rows)]

    @classmethod
    def get_trajectory(cls, patient_id: str):
        cls.require(patient_id)
        rows = list(reversed(cls.repo.predictions(patient_id)))
        return {
            "patient_id": patient_id,
            "points": [
                {
                    "timestamp": r.timestamp,
                    "risk_probability": r.risk,
                    "alert_severity": r.payload.get("alert_severity") if isinstance(r.payload, dict) else None
                }
                for r in rows
            ]
        }

    @classmethod
    def get_predictions(cls, patient_id: str):
        cls.require(patient_id)
        return cls.repo.predictions(patient_id)

    @classmethod
    def get_alerts(cls, patient_id: str):
        cls.require(patient_id)
        return cls.repo.alerts(patient_id)

patient_service = PatientService()
