from sqlalchemy import select
from .store import Session, PatientRecord, VitalRecord, PredictionRecord, AlertRecord

class PatientRepository:
    def get(self, patient_id):
        with Session() as s: return s.scalars(select(PatientRecord).where(PatientRecord.patient_id==patient_id)).first()
    def create(self, data):
        with Session.begin() as s:
            row=PatientRecord(**data); s.add(row); s.flush(); return row
    def vitals(self, patient_id, limit=200):
        with Session() as s: return list(s.scalars(select(VitalRecord).where(VitalRecord.patient_id==patient_id).order_by(VitalRecord.timestamp.desc()).limit(limit)))
    def predictions(self, patient_id, limit=200):
        with Session() as s: return list(s.scalars(select(PredictionRecord).where(PredictionRecord.patient_id==patient_id).order_by(PredictionRecord.timestamp.desc()).limit(limit)))
    def alerts(self, patient_id, limit=100):
        with Session() as s: return list(s.scalars(select(AlertRecord).where(AlertRecord.patient_id==patient_id).order_by(AlertRecord.timestamp.desc()).limit(limit)))
