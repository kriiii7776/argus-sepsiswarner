from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from ..auth import require_api_key
from ..schemas import VitalEvent, PredictionResponse, ModelVersionResponse
from ..service import runtime
from ..services.inference_service import inference_service
from ..services.event_broker import broker

router=APIRouter(tags=['inference'])
@router.get('/health')
def health(): return {'status':'ok','model_version':'development-fallback-v0' if runtime.demo else 'xgboost-tabular-v1','is_demo_model':runtime.demo}
@router.get('/model-version',response_model=ModelVersionResponse,dependencies=[Depends(require_api_key)])
def model_version(): return ModelVersionResponse(model_version='development-fallback-v0' if runtime.demo else 'xgboost-tabular-v1',is_demo_model=runtime.demo)
@router.post('/events/vitals',response_model=PredictionResponse,status_code=201,dependencies=[Depends(require_api_key)])
async def ingest_vitals(event:VitalEvent): return await inference_service.ingest(event)
@router.websocket('/ws/updates')
async def websocket_updates(ws:WebSocket):
    # Browser/WebSocket token validation must be implemented through a secure
    # subprotocol or short-lived signed token in non-development environments.
    await ws.accept(); broker.subscribers.add(ws)
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: broker.subscribers.discard(ws)
