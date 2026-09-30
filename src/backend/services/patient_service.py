from src.backend.schemas.schemas import Patient, PatientCreate, Vital
from src.backend.core.exceptions import NotFoundException
import uuid

# Mock DB
patients_db = {}
vitals_db = {}

class PatientService:
    @staticmethod
    def create_patient(patient_in: PatientCreate) -> Patient:
        patient_id = str(uuid.uuid4())
        patient = Patient(id=patient_id, **patient_in.model_dump())
        patients_db[patient_id] = patient
        vitals_db[patient_id] = []
        return patient

    @staticmethod
    def get_patient(patient_id: str) -> Patient:
        if patient_id not in patients_db:
            raise NotFoundException("Patient not found")
        return patients_db[patient_id]

    @staticmethod
    def get_vitals(patient_id: str) -> list[Vital]:
        if patient_id not in patients_db:
            raise NotFoundException("Patient not found")
        return vitals_db.get(patient_id, [])

    @staticmethod
    def get_trajectory(patient_id: str):
        # Mock trajectory
        if patient_id not in patients_db:
            raise NotFoundException("Patient not found")
        return {"patient_id": patient_id, "trajectory": ["stable", "improving"]}
