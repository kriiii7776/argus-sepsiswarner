import json
import logging
from fastapi import HTTPException
from src.backend.services.inference_runtime import runtime
from src.backend.db.store import Session, VitalRecord, PredictionRecord, AlertRecord
from src.backend.services.event_broker import broker
from src.backend.services.patient_service import patient_service
from src.backend.schemas.schemas import RiskAssessment, Explanation, VitalEvent

log = logging.getLogger('sepsisguard.inference')

class InferenceService:
    @staticmethod
    async def ingest(event: VitalEvent) -> dict:
        patient_service.require(event.patient_id)
        result = runtime.predict(event)
        
        # Serialize result payload safely for JSON column storage
        json_payload = json.loads(json.dumps(result, default=str))
        json_payload['vitals'] = event.model_dump(mode='json')
        alert_payload = json.loads(json.dumps({
            **result.get('alert', {}),
            'patient_id': event.patient_id,
            'session_id': event.session_id,
            'prediction_timestamp': event.timestamp,
        }, default=str))
        
        with Session.begin() as s:
            s.add(VitalRecord(
                patient_id=event.patient_id,
                session_id=event.session_id,
                timestamp=event.timestamp,
                payload=event.model_dump(mode='json'),
                source=event.source
            ))
            s.add(PredictionRecord(
                patient_id=event.patient_id,
                session_id=event.session_id,
                timestamp=event.timestamp,
                risk=result['risk_probability'],
                payload=json_payload,
                model_version=result['model_version']
            ))
            if result.get('alert', {}).get('alert_emitted'):
                s.add(AlertRecord(
                    patient_id=event.patient_id,
                    session_id=event.session_id,
                    timestamp=event.timestamp,
                    severity=result['alert_severity'] or 'NONE',
                    payload=alert_payload
                ))
                
        await broker.publish('prediction', event.patient_id, json_payload)
        if result.get('alert', {}).get('alert_emitted'):
            await broker.publish('alert', event.patient_id, alert_payload)
            try:
                from src.backend.services.alert_router import alert_router
                await alert_router.route_alert(event.patient_id, alert_payload)
            except Exception as exc:
                log.warning("Alert routing exception: %s", exc)
            
        return result

    @staticmethod
    def predict_risk(patient_id: str) -> RiskAssessment:
        rows = patient_service.get_predictions(patient_id)
        if not rows:
            from datetime import datetime, timezone
            dummy = VitalEvent(patient_id=patient_id, timestamp=datetime.now(timezone.utc), heart_rate=80.0, map=75.0, resp_rate=16.0, spo2=98.0, temperature_c=37.0)
            res = runtime.predict(dummy)
            score = res['risk_probability']
            level = "HIGH" if score > 0.7 else "LOW"
            factors = res['contributing_factors']
        else:
            r = rows[0]
            score = r.risk
            level = "HIGH" if score > 0.7 else "LOW"
            factors = r.payload.get('contributing_factors', []) if isinstance(r.payload, dict) else []
            
        return RiskAssessment(
            patient_id=patient_id,
            risk_score=score,
            risk_level=level,
            factors=factors
        )

    @staticmethod
    def explain_prediction(patient_id: str) -> Explanation:
        rows = patient_service.get_predictions(patient_id)
        if not rows:
            return Explanation(
                patient_id=patient_id,
                feature_importance={},
                summary="No prior prediction record found; SHAP explanation unavailable."
            )
        r = rows[0]
        payload = r.payload if isinstance(r.payload, dict) else {}
        shap_exp = payload.get('shap_explanation', {})
        if shap_exp.get('explanation_available'):
            feat_imp = {attr['feature_name']: attr['shap_value'] for attr in shap_exp.get('feature_attributions', [])}
            summary = f"Real SHAP model attributions (log-odds space) derived from {r.model_version}."
        else:
            factors = payload.get('contributing_factors', [])
            feat_imp = {}
            summary = "SHAP model explanation unavailable for this prediction record."
            
        return Explanation(
            patient_id=patient_id,
            feature_importance=feat_imp,
            summary=summary
        )

inference_service = InferenceService()
