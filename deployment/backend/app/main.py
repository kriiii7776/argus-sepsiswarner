import asyncio, json, logging, os, random
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .schemas import VitalEvent, PredictionResponse, SimulatorRequest
from .service import runtime
from .store import init_db, Session, VitalRecord, PredictionRecord, AlertRecord

logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
log=logging.getLogger('sepsisguard.api')
app=FastAPI(title='SepsisGuard local inference', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(','),
                   allow_credentials=False, allow_methods=['*'], allow_headers=['*'])

@app.on_event('startup')
def startup(): init_db(); log.info('service_started model_demo=%s', runtime.demo)

async def broadcast(kind, patient_id, payload):
    message=json.dumps({'type':kind,'occurred_at':datetime.now(timezone.utc).isoformat(),'patient_id':patient_id,'payload':payload}, default=str)
    for ws in list(runtime.subscribers):
        try: await ws.send_text(message)
        except Exception: runtime.subscribers.discard(ws)

@app.get('/health')
def health(): return {'status':'ok','model_version':'development-fallback-v0' if runtime.demo else 'xgboost-tabular-v1','is_demo_model':runtime.demo}

@app.post('/v1/events/vitals', response_model=PredictionResponse, status_code=201)
async def ingest(event: VitalEvent):
    try: result=runtime.predict(event)
    except Exception as exc:
        log.exception('inference_failed patient_id=%s', event.patient_id); raise HTTPException(422, 'Event could not be processed; no prediction created.') from exc
    with Session.begin() as s:
        s.add(VitalRecord(patient_id=event.patient_id,timestamp=event.timestamp,payload=event.model_dump(mode='json'),source=event.source))
        s.add(PredictionRecord(patient_id=event.patient_id,timestamp=event.timestamp,risk=result['risk_probability'],payload=result,model_version=result['model_version']))
        if result['alert']['alert_emitted']: s.add(AlertRecord(patient_id=event.patient_id,timestamp=event.timestamp,severity=result['alert_severity'] or 'NONE',payload=result['alert']))
    await broadcast('prediction',event.patient_id,result)
    if result['alert']['alert_emitted']: await broadcast('alert',event.patient_id,result['alert'])
    return result

@app.get('/v1/patients/{patient_id}/latest', response_model=PredictionResponse)
def latest(patient_id:str):
    from sqlalchemy import select
    with Session() as s:
        row=s.scalars(select(PredictionRecord).where(PredictionRecord.patient_id==patient_id).order_by(PredictionRecord.timestamp.desc())).first()
    if not row: raise HTTPException(404,'No prediction found for patient.')
    return row.payload

@app.websocket('/v1/stream')
async def stream(ws:WebSocket):
    await ws.accept(); runtime.subscribers.add(ws)
    try:
        while True: await ws.receive_text()  # client keepalive / future subscription filters
    except WebSocketDisconnect: runtime.subscribers.discard(ws)

@app.post('/v1/simulator/start')
async def simulator(request:SimulatorRequest):
    asyncio.create_task(run_simulator(request)); return {'status':'started','disclaimer':'Synthetic development stream; not patient physiology.'}

async def run_simulator(request):
    """Synthetic trend generator for integration testing only, not physiology simulation."""
    for tick in range(max(1, request.duration_minutes*60//request.cadence_seconds)):
        for i in range(request.patient_count):
            phase=(tick/20+i*.7); worsening=max(0., min(1., (phase-2)/8)) if i%3==0 else 0.
            event=VitalEvent(patient_id=f'SIM-{i+1:03d}',timestamp=datetime.now(timezone.utc),heart_rate=78+32*worsening+random.gauss(0,3),map=74-24*worsening+random.gauss(0,3),resp_rate=16+9*worsening+random.gauss(0,1),spo2=97-4*worsening+random.gauss(0,.5),temperature_c=37+1.5*worsening+random.gauss(0,.1),lactate=None if random.random()<.25 else 1.2+2*worsening,source='simulator')
            try: await ingest(event)
            except Exception: log.exception('simulator_event_failed')
        await asyncio.sleep(request.cadence_seconds)
