"""Model-pipeline isolation check using explicitly simulated vital streams."""
from datetime import datetime, timedelta, timezone

from src.backend.schemas.schemas import VitalEvent
from src.backend.services.inference_runtime import FEATURES, Runtime


def test_four_simulated_patient_streams_keep_independent_features_predictions_and_shap():
    runtime = Runtime()
    start = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    profiles = {
        'SIM-STABLE': (80, 75, 16, 98, 37.0, 0),
        'SIM-WORSENING': (80, 75, 16, 98, 37.0, 1),
        'SIM-RECOVERING': (120, 55, 28, 91, 39.0, -1),
        'SIM-NOISY': (82, 74, 17, 97, 37.1, 2),
    }
    latest = {}

    # Interleave all four patient event histories through the same production Runtime.
    for step in range(5):
        for patient_id, (hr0, map0, rr0, spo20, temp0, direction) in profiles.items():
            jitter = (-1) ** step * (3 if direction == 2 else 0)
            event = VitalEvent(
                patient_id=patient_id,
                session_id=f'SESSION-{patient_id}',
                timestamp=start + timedelta(hours=step),
                heart_rate=hr0 + direction * step * 6 + jitter,
                map=map0 - direction * step * 3 - jitter,
                resp_rate=rr0 + direction * step,
                spo2=spo20 - direction * step * 0.5,
                temperature_c=temp0 + direction * step * 0.15,
                source='simulator',
            )
            latest[patient_id] = runtime.predict(event)

    assert set(runtime.history) == set(profiles)
    assert set(runtime.alert_states).issubset(set(profiles))
    assert set(latest) == set(profiles)
    for patient_id, result in latest.items():
        assert result['patient_id'] == patient_id
        assert result['session_id'] == f'SESSION-{patient_id}'
        assert 0.0 <= result['risk_probability'] <= 1.0
        explanation = result['shap_explanation']
        assert explanation['explanation_available'] is True
        attributions = explanation['feature_attributions']
        assert len(attributions) == len(FEATURES) == 31
        assert {item['feature_name'] for item in attributions} == set(FEATURES)
        assert all(item['model_version'] == 'logistic-regression-v1' for item in attributions)
    assert all(len(runtime.history[patient_id]) == 5 for patient_id in profiles)
