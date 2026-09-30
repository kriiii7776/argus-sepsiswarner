from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from src.backend.schemas.schemas import Patient, PatientCreate, RiskAssessment, Explanation, Alert, Vital
from src.backend.services.patient_service import PatientService
from src.backend.services.inference_service import InferenceService
from src.backend.services.alert_engine import AlertEngine
from src.backend.core.security import get_current_user

router = APIRouter()

@router.post("/patients", response_model=Patient)
def create_patient(patient: PatientCreate, current_user=Depends(get_current_user)):
    return PatientService.create_patient(patient)

@router.get("/patients/{id}", response_model=Patient)
def get_patient(id: str, current_user=Depends(get_current_user)):
    return PatientService.get_patient(id)

@router.get("/patients/{id}/vitals", response_model=list[Vital])
def get_vitals(id: str, current_user=Depends(get_current_user)):
    return PatientService.get_vitals(id)

@router.get("/patients/{id}/trajectory")
def get_trajectory(id: str, current_user=Depends(get_current_user)):
    return PatientService.get_trajectory(id)

@router.get("/patients/{id}/risk", response_model=RiskAssessment)
def get_risk(id: str, current_user=Depends(get_current_user)):
    return InferenceService.predict_risk(id)

@router.get("/patients/{id}/explanation", response_model=Explanation)
def get_explanation(id: str, current_user=Depends(get_current_user)):
    return InferenceService.explain_prediction(id)

@router.get("/patients/{id}/alerts", response_model=list[Alert])
def get_alerts(id: str, current_user=Depends(get_current_user)):
    return AlertEngine.check_and_generate_alerts(id)

# Connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Message text was: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
