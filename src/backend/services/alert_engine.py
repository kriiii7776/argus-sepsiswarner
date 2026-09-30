from src.backend.schemas.schemas import Alert
from src.backend.services.inference_service import InferenceService
from datetime import datetime
import uuid

class AlertEngine:
    @staticmethod
    def check_and_generate_alerts(patient_id: str) -> list[Alert]:
        risk = InferenceService.predict_risk(patient_id)
        alerts = []
        if risk.risk_score > 0.7:
            alerts.append(Alert(
                alert_id=str(uuid.uuid4()),
                patient_id=patient_id,
                severity="CRITICAL",
                message="High risk score detected.",
                timestamp=datetime.utcnow().isoformat()
            ))
        return alerts
