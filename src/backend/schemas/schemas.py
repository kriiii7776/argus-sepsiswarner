from typing import List, Optional
from pydantic import BaseModel, Field

class PatientBase(BaseModel):
    name: str = Field(..., description="Patient's full name")
    age: int = Field(..., ge=0, description="Patient's age")
    medical_history: Optional[List[str]] = []

class PatientCreate(PatientBase):
    pass

class Patient(PatientBase):
    id: str
    
    class Config:
        from_attributes = True

class Vital(BaseModel):
    heart_rate: float
    blood_pressure: str
    temperature: float
    oxygen_saturation: float
    timestamp: str

class RiskAssessment(BaseModel):
    patient_id: str
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: str
    factors: List[str]

class Alert(BaseModel):
    alert_id: str
    patient_id: str
    severity: str
    message: str
    timestamp: str

class Explanation(BaseModel):
    patient_id: str
    feature_importance: dict
    summary: str
