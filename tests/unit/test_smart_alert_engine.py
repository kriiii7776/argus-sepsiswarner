import pytest
import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
from src.backend.services.inference_runtime import Runtime
from src.backend.schemas.schemas import VitalEvent

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('alerts', ROOT / 'src' / 'pipeline' / '11_smart_alert_engine.py')
alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alerts)

SmartAlertEngine = alerts.SmartAlertEngine
AlertPolicy = alerts.AlertPolicy
AlertState = alerts.AlertState
YELLOW = alerts.YELLOW
ORANGE = alerts.ORANGE
RED = alerts.RED

def create_event(patient_id: str, ts: datetime, risk: float, conf: str = 'HIGH', sq: str = 'HIGH', trajectory: float = 0.0):
    return {
        'patient_id': patient_id,
        'timestamp': ts,
        'risk_probability': risk,
        'confidence': conf,
        'signal_quality': sq,
        'risk_trajectory_per_hour': trajectory,
        'contributing_factors': ['hr_curr (115.00): positive model contribution (+0.842 log-odds)']
    }

def test_1_normal_state():
    engine = SmartAlertEngine()
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    evt = create_event("P-1", ts, risk=0.15)
    decision, state = engine.process(evt)
    assert decision['alert_emitted'] is False
    assert decision['alert_severity'] is None
    assert decision['active_severity'] is None

def test_2_watch_activation():
    engine = SmartAlertEngine()
    ts1 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 14, 1, tzinfo=timezone.utc)
    state = AlertState()
    
    # Event 1: Initial crossing (requires persistence = 2 hours)
    d1, state = engine.process(create_event("P-2", ts1, risk=0.28), state)
    assert d1['alert_emitted'] is False
    assert d1['suppression_reason'] == 'awaiting persistence before escalation'
    
    # Event 2: 2.01 hours later -> persistence satisfied -> WATCH emitted
    d2, state = engine.process(create_event("P-2", ts2, risk=0.28), state)
    assert d2['alert_emitted'] is True
    assert d2['alert_severity'] == YELLOW

def test_3_review_activation():
    engine = SmartAlertEngine()
    ts1 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 14, 1, tzinfo=timezone.utc)
    state = AlertState()
    
    d1, state = engine.process(create_event("P-3", ts1, risk=0.40), state)
    assert d1['alert_emitted'] is False
    d2, state = engine.process(create_event("P-3", ts2, risk=0.40), state)
    assert d2['alert_emitted'] is True
    assert d2['alert_severity'] == ORANGE

def test_4_urgent_activation():
    engine = SmartAlertEngine()
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    evt = create_event("P-4", ts, risk=0.75, conf='HIGH', sq='HIGH')
    decision, state = engine.process(evt)
    assert decision['alert_emitted'] is True
    assert decision['alert_severity'] == RED

def test_5_timestamp_based_persistence():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = AlertState()
    
    # 4 events in 20 seconds
    for delta in [0, 5, 10, 20]:
        ts = t0 + timedelta(seconds=delta)
        d, state = engine.process(create_event("P-5", ts, risk=0.28), state)
        assert d['alert_emitted'] is False
        assert state.consecutive_risk_windows == 1

def test_6_sparse_event_handling():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = AlertState()
    
    d1, state = engine.process(create_event("P-6", t0, risk=0.28), state)
    assert d1['alert_emitted'] is False
    
    # Event 2 hours 30 mins later
    t1 = t0 + timedelta(hours=2, minutes=30)
    d2, state = engine.process(create_event("P-6", t1, risk=0.28), state)
    assert d2['alert_emitted'] is True
    assert state.consecutive_risk_windows == 3

def test_7_high_frequency_event_handling():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = AlertState()
    
    for i in range(10):
        ts = t0 + timedelta(seconds=i * 5)
        d, state = engine.process(create_event("P-7", ts, risk=0.30), state)
        assert d['alert_emitted'] is False
        assert state.consecutive_risk_windows == 1

def test_8_watch_to_review_escalation():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=2, minutes=5)
    state = AlertState()
    
    engine.process(create_event("P-8", t0, risk=0.28), state)
    d1, state = engine.process(create_event("P-8", t1, risk=0.28), state)
    assert d1['alert_severity'] == YELLOW
    
    # Trajectory jump +15%/hr escalates to REVIEW
    t2 = t1 + timedelta(hours=1)
    d2, state = engine.process(create_event("P-8", t2, risk=0.32, trajectory=0.15), state)
    assert d2['active_severity'] == ORANGE

def test_9_review_to_urgent_escalation():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=2, minutes=5)
    state = AlertState()
    
    engine.process(create_event("P-9", t0, risk=0.40), state)
    d1, state = engine.process(create_event("P-9", t1, risk=0.40), state)
    assert d1['alert_severity'] == ORANGE
    
    t2 = t1 + timedelta(minutes=30)
    d2, state = engine.process(create_event("P-9", t2, risk=0.75, conf='HIGH', sq='HIGH'), state)
    assert d2['alert_emitted'] is True
    assert d2['alert_severity'] == RED

def test_10_recovery_deescalation():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = AlertState()
    
    # Immediate RED alert
    d1, state = engine.process(create_event("P-10", t0, risk=0.75, conf='HIGH', sq='HIGH'), state)
    assert d1['active_severity'] == RED
    
    # Patient recovers to 0.15 (below watch threshold)
    t1 = t0 + timedelta(hours=1)
    d2, state = engine.process(create_event("P-10", t1, risk=0.15), state)
    assert d2['active_severity'] == RED  # Hysteresis hold
    
    # 3.1 hours below threshold -> de-escalate cleanly
    t2 = t0 + timedelta(hours=4, minutes=10)
    d3, state = engine.process(create_event("P-10", t2, risk=0.15), state)
    assert d3['active_severity'] is None

def test_11_hysteresis():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=2, minutes=5)
    state = AlertState()
    
    engine.process(create_event("P-11", t0, risk=0.40), state)
    d1, state = engine.process(create_event("P-11", t1, risk=0.40), state)
    assert d1['active_severity'] == ORANGE
    
    # Drop below 0.35 for 1 hour -> hysteresis holds active_severity at ORANGE
    t2 = t1 + timedelta(hours=1)
    d2, state = engine.process(create_event("P-11", t2, risk=0.20), state)
    assert d2['active_severity'] == ORANGE
    assert d2['suppression_reason'] == 'hysteresis hold during improvement'

def test_12_duplicate_alert_prevention():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = AlertState()
    
    d1, state = engine.process(create_event("P-12", t0, risk=0.75, conf='HIGH', sq='HIGH'), state)
    assert d1['alert_emitted'] is True
    
    # Repeat event 30 mins later (< 2h red_repeat_hours) -> suppressed
    t1 = t0 + timedelta(minutes=30)
    d2, state = engine.process(create_event("P-12", t1, risk=0.75, conf='HIGH', sq='HIGH'), state)
    assert d2['alert_emitted'] is False
    assert d2['suppression_reason'] == 'duplicate within repeat interval'

def test_13_repeated_identical_events():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state = AlertState()
    
    d1, state = engine.process(create_event("P-13", t0, risk=0.75, conf='HIGH', sq='HIGH'), state)
    assert d1['alert_emitted'] is True
    
    # Repeat event 2.1 hours later (>= 2h red_repeat_hours) -> repeat alert emitted
    t1 = t0 + timedelta(hours=2, minutes=6)
    d2, state = engine.process(create_event("P-13", t1, risk=0.75, conf='HIGH', sq='HIGH'), state)
    assert d2['alert_emitted'] is True

def test_14_high_signal_quality():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    d, state = engine.process(create_event("P-14", t0, risk=0.72, conf='HIGH', sq='HIGH'))
    assert d['alert_severity'] == RED

def test_15_medium_signal_quality():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # Risk 0.72 with MEDIUM confidence/quality is capped at ORANGE (floor is 0.85)
    d, state = engine.process(create_event("P-15", t0, risk=0.72, conf='MEDIUM', sq='MEDIUM'))
    assert d['alert_severity'] == ORANGE

def test_16_low_signal_quality():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # Risk 0.72 with LOW confidence/quality is capped at ORANGE
    d, state = engine.process(create_event("P-16", t0, risk=0.72, conf='LOW', sq='LOW'))
    assert d['alert_severity'] == ORANGE

def test_17_missing_data():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    evt = {'timestamp': t0, 'risk_probability': 0.75}
    d, state = engine.process(evt)
    assert d['alert_severity'] == ORANGE  # Candidate severity capped at ORANGE due to default conf=LOW
    assert d['alert_emitted'] is False     # Awaiting persistence

def test_18_stale_data():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    d, state = engine.process(create_event("P-18", str(t0), risk=0.75, conf='HIGH', sq='HIGH'))
    assert d['alert_emitted'] is True

def test_19_invalid_noisy_data():
    engine = SmartAlertEngine()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    d, state = engine.process(create_event("P-19", t0, risk=0.90, conf='LOW', sq='LOW'))
    assert d['alert_severity'] == RED  # Risk >= 0.85 floor overcomes LOW confidence limit

def test_20_model_version_remains_logistic_regression_v1():
    rt = Runtime()
    assert rt.model_version_name == 'logistic-regression-v1'

def test_21_shap_remains_available():
    rt = Runtime()
    event = VitalEvent(
        patient_id="P-21",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        heart_rate=115.0, map=62.0, resp_rate=24.0, spo2=94.0, temperature_c=39.1
    )
    res = rt.predict(event)
    assert res['shap_explanation']['explanation_available'] is True

def test_22_uncertainty_remains_explicitly_unavailable():
    rt = Runtime()
    event = VitalEvent(
        patient_id="P-22",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        heart_rate=115.0, map=62.0, resp_rate=24.0, spo2=94.0, temperature_c=39.1
    )
    res = rt.predict(event)
    assert res['uncertainty_summary']['uncertainty_available'] is False

def test_23_end_to_end_inference_to_alert_behavior():
    rt = Runtime()
    event = VitalEvent(
        patient_id="P-E2E-ALERT",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        heart_rate=145.0, map=45.0, resp_rate=32.0, spo2=88.0, temperature_c=39.8
    )
    res = rt.predict(event)
    assert 'alert' in res
    assert res['patient_id'] == "P-E2E-ALERT"
    assert res['is_demo_model'] is False
    assert res['model_version'] == 'logistic-regression-v1'
