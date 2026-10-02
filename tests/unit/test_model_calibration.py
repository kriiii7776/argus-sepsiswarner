import pytest
import os
from datetime import datetime, timezone
import numpy as np
import joblib
from src.backend.services.inference_runtime import Runtime, FEATURES, SigmoidCalibrator
from src.backend.schemas.schemas import VitalEvent

def create_sample_event(patient_id: str = "P-CAL-TEST"):
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

def test_1_model_artifact_loading():
    rt = Runtime()
    assert rt.model is not None, "Real ML model failed to load."
    assert not rt.demo, "Runtime incorrectly flagged as demo mode."

def test_2_calibrator_loading():
    rt = Runtime()
    assert rt.cal is not None, "Sigmoid calibrator artifact failed to load."
    assert hasattr(rt.cal, 'a_') and hasattr(rt.cal, 'b_'), "Calibrator missing fitted parameters."

def test_3_feature_count_compatibility():
    rt = Runtime()
    assert len(FEATURES) == 31, "Runtime FEATURES list length mismatch."
    assert getattr(rt.model, 'n_features_in_', 31) == 31, "Model n_features_in_ mismatch."
    assert getattr(rt.scaler, 'n_features_in_', 31) == 31, "Scaler n_features_in_ mismatch."

def test_4_feature_order_compatibility():
    assert FEATURES[0] == 'hr_curr'
    assert FEATURES[1] == 'map_curr'
    assert FEATURES[2] == 'rr_curr'
    assert FEATURES[3] == 'spo2_curr'
    assert FEATURES[4] == 'temp_curr'
    assert FEATURES[-1] == 'icu_hour'

def test_5_prediction_generation():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    assert 0.0 <= res['risk_probability'] <= 1.0, "Risk probability out of bounds."
    assert isinstance(res['latency_ms'], float), "Latency measurement invalid."

def test_6_calibrated_probability_generation():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    prob = res['risk_probability']
    assert 0.0 <= prob <= 1.0, "Calibrated probability out of bounds."

def test_7_real_model_status():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    assert res['is_demo_model'] is False, "is_demo_model must be False for real ML model."
    assert res['model_version'] == 'logistic-regression-v1', f"Unexpected model version: {res['model_version']}"

def test_8_fallback_status_when_artifact_unavailable():
    rt = Runtime()
    # Intentionally remove model to test fallback
    rt.model = None
    rt.demo = True
    rt.model_version_name = 'development-fallback-v0'
    
    event = create_sample_event()
    res = rt.predict(event)
    assert res['is_demo_model'] is True
    assert res['model_version'] == 'development-fallback-v0'
    assert 0.0 <= res['risk_probability'] <= 1.0

def test_9_missing_calibrator_graceful_handling():
    rt = Runtime()
    rt.cal = None  # Intentionally clear calibrator
    event = create_sample_event()
    res = rt.predict(event)
    # Must still produce valid probability using uncalibrated raw model output
    assert 0.0 <= res['risk_probability'] <= 1.0

def test_10_pipeline_end_to_end_verification():
    rt = Runtime()
    event = create_sample_event("P-E2E")
    res = rt.predict(event)
    assert res['patient_id'] == "P-E2E"
    assert res['confidence'] in ['HIGH', 'MEDIUM', 'LOW']
    assert res['signal_quality'] in ['HIGH', 'MEDIUM', 'LOW']
    assert 'contributing_factors' in res
    assert len(res['contributing_factors']) > 0
