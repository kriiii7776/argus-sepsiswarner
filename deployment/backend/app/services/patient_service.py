from fastapi import HTTPException
from ..repositories import PatientRepository

class PatientService:
    def __init__(self, repo=None): self.repo=repo or PatientRepository()
    def create(self, payload):
        if self.repo.get(payload.patient_id): raise HTTPException(409,'Patient already exists.')
        return self.repo.create(payload.model_dump())
    def require(self, patient_id):
        row=self.repo.get(patient_id)
        if not row: raise HTTPException(404,'Patient not found.')
        return row
    def vitals(self, patient_id): self.require(patient_id); return self.repo.vitals(patient_id)
    def predictions(self, patient_id): self.require(patient_id); return self.repo.predictions(patient_id)
    def alerts(self, patient_id): self.require(patient_id); return self.repo.alerts(patient_id)
patient_service=PatientService()
