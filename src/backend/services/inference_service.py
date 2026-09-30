from src.backend.schemas.schemas import RiskAssessment, Explanation
from src.backend.core.exceptions import InferenceException
import random

class InferenceService:
    @staticmethod
    def predict_risk(patient_id: str) -> RiskAssessment:
        try:
            # Mock ML inference
            score = round(random.uniform(0.1, 0.9), 2)
            level = "HIGH" if score > 0.7 else "LOW"
            return RiskAssessment(
                patient_id=patient_id,
                risk_score=score,
                risk_level=level,
                factors=["elevated heart rate", "age"] if level == "HIGH" else ["normal vitals"]
            )
        except Exception as e:
            raise InferenceException(str(e))

    @staticmethod
    def explain_prediction(patient_id: str) -> Explanation:
        return Explanation(
            patient_id=patient_id,
            feature_importance={"heart_rate": 0.6, "blood_pressure": 0.4},
            summary="Heart rate is the primary driver for the current risk score."
        )
