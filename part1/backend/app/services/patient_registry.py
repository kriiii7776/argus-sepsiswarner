"""
Thread-safe Patient Registry Service.

Manages active patient simulation lifecycles and patient metadata.
"""

from threading import Lock
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.schemas.patient import (
    Patient,
    PatientProfileType,
    PatientSex,
    PatientStatus,
)
from app.simulation.patient_generator import PatientFactory
from app.core.exceptions import ARGUSException


class PatientRegistry:
    """
    In-memory thread-safe registry for managing active simulation patients.
    """

    def __init__(self):
        self._patients: Dict[str, Patient] = {}
        self._lock = Lock()

    def register_patient(self, patient: Patient) -> Patient:
        """
        Registers an existing Patient instance into the registry.
        """
        with self._lock:
            self._patients[patient.patient_id] = patient
            return patient

    def create_patient(
        self,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        age: Optional[int] = None,
        sex: Optional[PatientSex] = None,
        profile_type: PatientProfileType = PatientProfileType.STANDARD,
        status: PatientStatus = PatientStatus.ACTIVE,
        seed: Optional[int] = None,
    ) -> Patient:
        """
        Creates a new synthetic patient baseline and registers it.
        """
        patient = PatientFactory.create_patient(
            patient_id=patient_id,
            session_id=session_id,
            age=age,
            sex=sex,
            profile_type=profile_type,
            status=status,
            seed=seed,
        )
        return self.register_patient(patient)

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        """
        Retrieves a patient by patient_id.
        """
        with self._lock:
            return self._patients.get(patient_id)

    def list_patients(self, status: Optional[PatientStatus] = None) -> List[Patient]:
        """
        Lists registered patients, optionally filtering by PatientStatus.
        """
        with self._lock:
            if status is None:
                return list(self._patients.values())
            return [p for p in self._patients.values() if p.status == status]

    def update_patient_status(self, patient_id: str, status: PatientStatus) -> Patient:
        """
        Updates the simulation status of a patient.
        """
        with self._lock:
            if patient_id not in self._patients:
                raise ARGUSException(
                    code="PATIENT_NOT_FOUND",
                    message=f"Patient '{patient_id}' not found in registry.",
                    status_code=404,
                )
            patient = self._patients[patient_id]
            updated_patient = patient.model_copy(
                update={"status": status, "updated_at": datetime.now(timezone.utc)}
            )
            self._patients[patient_id] = updated_patient
            return updated_patient

    def remove_patient(self, patient_id: str) -> bool:
        """
        Removes a patient from the registry.
        """
        with self._lock:
            if patient_id in self._patients:
                del self._patients[patient_id]
                return True
            return False

    def clear(self) -> None:
        """
        Clears all patients from the registry (primarily for test isolation).
        """
        with self._lock:
            self._patients.clear()


# Global Singleton Registry Instance
patient_registry = PatientRegistry()
