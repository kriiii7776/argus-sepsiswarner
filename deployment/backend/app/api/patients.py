from fastapi import APIRouter, Depends, HTTPException
from ..auth import require_api_key
from ..schemas import PatientCreate, PatientResponse, VitalResponse, TrajectoryResponse, TrajectoryPoint, PredictionResponse, ExplanationResponse, AlertResponse
from ..services.patient_service import patient_service

router=APIRouter(prefix='/patients',tags=['patients'],dependencies=[Depends(require_api_key)])
@router.post('',response_model=PatientResponse,status_code=201)
def create_patient(payload:PatientCreate):
    r=patient_service.create(payload); return PatientResponse(patient_id=r.patient_id,source_system=r.source_system,sex_at_birth=r.sex_at_birth,birth_year=r.birth_year,created_at=r.created_at)
@router.get('/{patient_id}',response_model=PatientResponse)
def get_patient(patient_id:str):
    r=patient_service.require(patient_id); return PatientResponse(patient_id=r.patient_id,source_system=r.source_system,sex_at_birth=r.sex_at_birth,birth_year=r.birth_year,created_at=r.created_at)
@router.get('/{patient_id}/vitals',response_model=list[VitalResponse])
def vitals(patient_id:str): return [VitalResponse(**r.payload) for r in reversed(patient_service.vitals(patient_id))]
@router.get('/{patient_id}/trajectory',response_model=TrajectoryResponse)
def trajectory(patient_id:str):
    rows=list(reversed(patient_service.predictions(patient_id))); return TrajectoryResponse(patient_id=patient_id,points=[TrajectoryPoint(timestamp=r.timestamp,risk_probability=r.risk,alert_severity=r.payload.get('alert_severity')) for r in rows])
@router.get('/{patient_id}/risk',response_model=PredictionResponse)
def risk(patient_id:str):
    rows=patient_service.predictions(patient_id)
    if not rows: raise HTTPException(404,'No prediction found for patient.')
    return rows[0].payload
@router.get('/{patient_id}/explanation',response_model=ExplanationResponse)
def explanation(patient_id:str):
    rows=patient_service.predictions(patient_id)
    if not rows: raise HTTPException(404,'No prediction found for patient.')
    r=rows[0]; return ExplanationResponse(patient_id=patient_id,prediction_timestamp=r.timestamp,contributing_factors=r.payload.get('contributing_factors',[]))
@router.get('/{patient_id}/alerts',response_model=list[AlertResponse])
def alerts(patient_id:str): return [AlertResponse(timestamp=r.timestamp,severity=r.severity,reason=r.payload.get('reason',[])) for r in patient_service.alerts(patient_id)]
