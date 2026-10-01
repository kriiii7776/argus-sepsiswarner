import asyncio
import logging
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from src.backend.schemas.schemas import VitalEvent, PredictionResponse, SimulatorRequest
from src.backend.services.inference_service import InferenceService
from src.backend.core.security import require_api_key

log = logging.getLogger('sepsisguard.events')
router = APIRouter(tags=['events'])

@router.post('/events/vitals', response_model=PredictionResponse, status_code=201)
async def ingest_vitals(event: VitalEvent):
    try:
        return await InferenceService.ingest(event)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception('inference_failed patient_id=%s', event.patient_id)
        raise HTTPException(422, 'Event could not be processed; no prediction created.') from exc

@router.post('/simulator/start')
async def start_simulator(request: SimulatorRequest):
    asyncio.create_task(run_simulator(request))
    return {'status': 'started', 'disclaimer': 'Synthetic development stream; not patient physiology.'}

async def run_simulator(request: SimulatorRequest):
    """Synthetic trend generator for integration testing only."""
    for tick in range(max(1, request.duration_minutes * 60 // request.cadence_seconds)):
        for i in range(request.patient_count):
            phase = (tick / 20 + i * .7)
            worsening = max(0., min(1., (phase - 2) / 8)) if i % 3 == 0 else 0.
            event = VitalEvent(
                patient_id=f'SIM-{i+1:03d}',
                timestamp=datetime.now(timezone.utc),
                heart_rate=78 + 32 * worsening + random.gauss(0, 3),
                map=74 - 24 * worsening + random.gauss(0, 3),
                resp_rate=16 + 9 * worsening + random.gauss(0, 1),
                spo2=97 - 4 * worsening + random.gauss(0, .5),
                temperature_c=37 + 1.5 * worsening + random.gauss(0, .1),
                lactate=None if random.random() < .25 else 1.2 + 2 * worsening,
                source='simulator'
            )
            try:
                await ingest_vitals(event)
            except Exception:
                log.exception('simulator_event_failed')
        await asyncio.sleep(request.cadence_seconds)
