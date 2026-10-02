import pytest
from datetime import datetime, timezone
import numpy as np
from src.backend.services.inference_runtime import Runtime
from src.backend.schemas.schemas import VitalEvent

def create_sample_event(patient_id: str = "P-UNC-TEST"):
    return VitalEvent(
        patient_id=patient_id,
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        heart_rate=115.0,
        map=62.0,
        resp_rate=24.0,
        spo2=94.0,
        temperature_c=39.1,
        source='simulator'
    )

def test_1_real_model_loading():
    rt = Runtime()
    assert rt.model is not None
    assert rt.demo is False

def test_2_model_version_remains_logistic_regression_v1():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    assert res['model_version'] == 'logistic-regression-v1'

def test_3_calibrated_risk_probability_unchanged():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    p = res['risk_probability']
    assert 0.0 <= p <= 1.0
    assert res['is_demo_model'] is False

def test_4_uncertainty_output_is_deterministic():
    rt = Runtime()
    event1 = create_sample_event("P-DET-1")
    event2 = create_sample_event("P-DET-2")
    res1 = rt.predict(event1)
    res2 = rt.predict(event2)
    assert res1['uncertainty_summary'] == res2['uncertainty_summary']

def test_5_uncertainty_method_correctly_reported():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    unc = res['uncertainty_summary']
    assert unc['uncertainty_available'] is False
    assert unc['method'] == 'UNAVAILABLE'

def test_6_no_arbitrary_20_percent_heuristic_remains():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    unc = res['uncertainty_summary']
    p = res['risk_probability']
    
    # Assert lower and upper bounds are None and no arbitrary (p - 0.20, p + 0.20) tuple is returned
    assert unc['interval_lower'] is None
    assert unc['interval_upper'] is None
    assert res['uncertainty_interval'] is None

def test_7_no_fake_confidence_values_produced():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    unc = res['uncertainty_summary']
    assert 'unavailable' in unc['reason'].lower()
    assert unc['coverage_level'] is None

def test_8_missing_conformal_data_handled_safely():
    rt = Runtime()
    event = create_sample_event()
    # Ensure prediction succeeds without raising exceptions despite missing conformal artifacts
    res = rt.predict(event)
    assert res['patient_id'] == "P-UNC-TEST"

def test_9_demo_fallback_model_uncertainty_handling():
    rt = Runtime()
    rt.demo = True
    rt.model = None
    event = create_sample_event("P-DEMO")
    res = rt.predict(event)
    unc = res['uncertainty_summary']
    assert unc['uncertainty_available'] is False
    assert unc['method'] == 'UNAVAILABLE'

def test_10_end_to_end_inference_returns_risk_and_uncertainty_separately():
    rt = Runtime()
    event = create_sample_event("P-E2E-UNC")
    res = rt.predict(event)
    assert 'risk_probability' in res
    assert 'uncertainty_summary' in res
    assert res['risk_probability'] != res['uncertainty_summary']

def test_11_existing_shap_explanation_remains_unaffected():
    rt = Runtime()
    event = create_sample_event("P-SHAP-UNC")
    res = rt.predict(event)
    assert 'shap_explanation' in res
    assert res['shap_explanation']['explanation_available'] is True
    assert len(res['shap_explanation']['feature_attributions']) == 31

def test_12_alert_engine_receives_signal_quality_confidence():
    rt = Runtime()
    event = create_sample_event("P-ALERT-UNC")
    res = rt.predict(event)
    assert 'alert' in res
    assert res['confidence'] in ['HIGH', 'MEDIUM', 'LOW']
    assert res['signal_quality'] in ['HIGH', 'MEDIUM', 'LOW']
