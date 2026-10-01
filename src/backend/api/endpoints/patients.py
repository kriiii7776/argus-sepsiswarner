from fastapi import APIRouter, Depends
from src.backend.schemas.schemas import Patient, PatientCreate, RiskAssessment, Explanation, Alert
from src.backend.services.patient_service import patient_service
from src.backend.services.inference_service import inference_service
from src.backend.core.security import get_current_user

router = APIRouter()

@router.post("/patients", response_model=Patient)
def create_patient(patient: PatientCreate, current_user=Depends(get_current_user)):
    return patient_service.create_patient(patient)

@router.get("/patients/{id}", response_model=Patient)
def get_patient(id: str, current_user=Depends(get_current_user)):
    return patient_service.get_patient(id)

@router.get("/patients/{id}/vitals")
def get_vitals(id: str, current_user=Depends(get_current_user)):
    return patient_service.get_vitals(id)

@router.get("/patients/{id}/trajectory")
def get_trajectory(id: str, current_user=Depends(get_current_user)):
    return patient_service.get_trajectory(id)

@router.get("/patients/{id}/risk", response_model=RiskAssessment)
def get_risk(id: str, current_user=Depends(get_current_user)):
    return inference_service.predict_risk(id)

@router.get("/patients/{id}/explanation", response_model=Explanation)
def get_explanation(id: str, current_user=Depends(get_current_user)):
    return inference_service.explain_prediction(id)

@router.get("/patients/{id}/alerts")
def get_alerts(id: str, current_user=Depends(get_current_user)):
    rows = patient_service.get_alerts(id)
    return [
        {
            "alert_id": str(i),
            "patient_id": id,
            "severity": r.severity,
            "message": r.payload.get("reason", ["Alert emitted"])[0] if isinstance(r.payload, dict) and r.payload.get("reason") else "Alert emitted",
            "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp)
        }
        for i, r in enumerate(rows)
    ]
