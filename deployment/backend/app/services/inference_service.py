import logging
from ..service import runtime
from ..store import Session, VitalRecord, PredictionRecord, AlertRecord
from .event_broker import broker
from .patient_service import patient_service

log=logging.getLogger('sepsisguard.inference')
class InferenceService:
    async def ingest(self, event):
        patient_service.require(event.patient_id)
        result=runtime.predict(event)
        with Session.begin() as s:
            s.add(VitalRecord(patient_id=event.patient_id,timestamp=event.timestamp,payload=event.model_dump(mode='json'),source=event.source))
            s.add(PredictionRecord(patient_id=event.patient_id,timestamp=event.timestamp,risk=result['risk_probability'],payload=result,model_version=result['model_version']))
            if result['alert']['alert_emitted']: s.add(AlertRecord(patient_id=event.patient_id,timestamp=event.timestamp,severity=result['alert_severity'] or 'NONE',payload=result['alert']))
        await broker.publish('prediction',event.patient_id,result)
        if result['alert']['alert_emitted']: await broker.publish('alert',event.patient_id,result['alert'])
        return result
inference_service=InferenceService()
