import pytest
from datetime import datetime, timezone, timedelta
import numpy as np
from src.backend.services.inference_runtime import Runtime, FEATURES
from src.backend.schemas.schemas import VitalEvent
from src.pipeline.canonical_features import FEATURES as CANONICAL_FEATURES, build_feature_row

def create_event(patient_id: str, ts: datetime, hr: float = 80.0, map_val: float = 75.0, rr: float = 16.0, spo2: float = 98.0, temp: float = 37.0):
    return VitalEvent(
        patient_id=patient_id,
        timestamp=ts,
        heart_rate=hr,
        map=map_val,
        resp_rate=rr,
        spo2=spo2,
        temperature_c=temp,
        source='simulator'
    )

def test_1_rapid_events_not_interpreted_as_four_hours():
    rt = Runtime()
    patient = "P-RAPID"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Send 4 events 5 seconds apart
    for i in range(4):
        event = create_event(patient, start_time + timedelta(seconds=i * 5), hr=80.0 + i * 5)
        rt.predict(event)
        
    _, row = rt.features(patient)
    # Elapsed time is 15 seconds (0.00416 hours), NOT 4 hours
    assert abs(row['icu_hour'] - (15.0 / 3600.0)) < 1e-4
    # 1-hour delta must be 0.0 because no baseline event >= 1 hour ago exists
    assert row['hr_delta_1h'] == 0.0
    # 4-hour slope must use actual 15-second elapsed time
    assert row['hr_slope_4h'] > 0.0  # (95 - 80) / (15 / 3600)

def test_2_exact_four_clinical_hours_window():
    rt = Runtime()
    patient = "P-4H-EXACT"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Send events every hour for 4 hours
    for h in range(5):
        event = create_event(patient, start_time + timedelta(hours=h), hr=80.0 + h * 10)
        rt.predict(event)
        
    _, row = rt.features(patient)
    assert abs(row['icu_hour'] - 4.0) < 1e-4
    assert row['hr_curr'] == 120.0
    assert row['hr_delta_4h'] == 40.0
    assert abs(row['hr_slope_4h'] - 10.0) < 1e-3  # 40 / 4h = 10 bpm/h

def test_3_five_minute_interval_window():
    rt = Runtime()
    patient = "P-5MIN"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Events every 5 minutes for 4 hours -> 49 events (0 to 48 * 5m = 240m = 4h)
    for i in range(49):
        event = create_event(patient, start_time + timedelta(minutes=i * 5), hr=80.0)
        rt.predict(event)
        
    h_4h = [x for x in rt.history[patient] if x['timestamp'] >= start_time]
    assert len(h_4h) == 49
    _, row = rt.features(patient)
    assert abs(row['icu_hour'] - 4.0) < 1e-4

def test_4_fifteen_minute_interval_window():
    rt = Runtime()
    patient = "P-15MIN"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Events every 15 minutes for 4 hours -> 17 events (0 to 16 * 15m = 240m = 4h)
    for i in range(17):
        event = create_event(patient, start_time + timedelta(minutes=i * 15), hr=80.0)
        rt.predict(event)
        
    h_4h = [x for x in rt.history[patient] if x['timestamp'] >= start_time]
    assert len(h_4h) == 17
    _, row = rt.features(patient)
    assert abs(row['icu_hour'] - 4.0) < 1e-4

def test_5_irregular_event_intervals():
    rt = Runtime()
    patient = "P-IRREGULAR"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    intervals = [0, 10, 45, 120, 240]  # minutes
    hrs = [70, 75, 80, 90, 110]
    for min_offset, hr in zip(intervals, hrs):
        event = create_event(patient, start_time + timedelta(minutes=min_offset), hr=hr)
        rt.predict(event)
        
    _, row = rt.features(patient)
    assert abs(row['icu_hour'] - 4.0) < 1e-4
    assert row['hr_delta_4h'] == 40.0
    assert abs(row['hr_slope_4h'] - 10.0) < 1e-3

def test_6_out_of_order_event_sorting():
    rt = Runtime()
    patient = "P-OUT-OF-ORDER"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Send event at 13:00 first, then event at 12:00
    e2 = create_event(patient, start_time + timedelta(hours=1), hr=100.0)
    e1 = create_event(patient, start_time, hr=80.0)
    
    rt.predict(e2)
    rt.predict(e1)
    
    # History must be sorted chronologically by timestamp
    assert rt.history[patient][0]['timestamp'] == start_time
    assert rt.history[patient][1]['timestamp'] == start_time + timedelta(hours=1)
    assert rt.history[patient][-1]['hr_curr'] == 100.0

def test_7_duplicate_timestamps_deterministic_handling():
    rt = Runtime()
    patient = "P-DUP"
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    e1 = create_event(patient, ts, hr=80.0)
    e2 = create_event(patient, ts, hr=95.0)  # Duplicate timestamp, updated payload
    
    rt.predict(e1)
    rt.predict(e2)
    
    # Should deduplicate and keep latest update
    assert len(rt.history[patient]) == 1
    assert rt.history[patient][0]['hr_curr'] == 95.0

def test_8_old_events_excluded_from_4h_window():
    rt = Runtime()
    patient = "P-EXCLUDE-OLD"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Event 6 hours ago (HR=180), Event 2 hours ago (HR=80), Event now (HR=80)
    rt.predict(create_event(patient, start_time, hr=180.0))
    rt.predict(create_event(patient, start_time + timedelta(hours=4), hr=80.0))
    rt.predict(create_event(patient, start_time + timedelta(hours=6), hr=80.0))
    
    _, row = rt.features(patient)
    # 6h ago event (HR=180) must be excluded from 4h mean calculation
    assert row['hr_mean_4h'] == 80.0
    assert row['hr_max_4h'] == 80.0

def test_9_inclusive_boundary_rule():
    rt = Runtime()
    patient = "P-BOUNDARY"
    t_now = datetime(2026, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
    t_boundary = t_now - timedelta(hours=4)  # 12:00:00
    
    rt.predict(create_event(patient, t_boundary, hr=100.0))
    rt.predict(create_event(patient, t_now, hr=80.0))
    
    _, row = rt.features(patient)
    # Event exactly at t_now - 4h must be included in 4h statistics
    assert row['hr_max_4h'] == 100.0

def test_10_slope_uses_elapsed_clinical_time():
    rt = Runtime()
    patient = "P-SLOPE"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # 20 bpm increase over 2 clinical hours
    rt.predict(create_event(patient, start_time, hr=80.0))
    rt.predict(create_event(patient, start_time + timedelta(hours=2), hr=100.0))
    
    _, row = rt.features(patient)
    # Slope must be 20 bpm / 2 hours = 10 bpm/h
    assert abs(row['hr_slope_4h'] - 10.0) < 1e-3

def test_11_sparse_data_no_fake_history():
    rt = Runtime()
    patient = "P-SPARSE"
    start_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Only 2 events 10 minutes apart
    rt.predict(create_event(patient, start_time, hr=80.0))
    rt.predict(create_event(patient, start_time + timedelta(minutes=10), hr=85.0))
    
    _, row = rt.features(patient)
    assert abs(row['icu_hour'] - (10.0 / 60.0)) < 1e-4
    assert row['hr_delta_1h'] == 0.0  # No 1h baseline event yet

def test_12_future_and_late_arrival_timestamps():
    rt = Runtime()
    patient = "P-LATE"
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)
    t2 = t0 + timedelta(hours=2)
    
    rt.predict(create_event(patient, t0, hr=80.0))
    rt.predict(create_event(patient, t2, hr=100.0))  # Event at 14:00
    rt.predict(create_event(patient, t1, hr=90.0))   # Late arriving event at 13:00
    
    # Chronological history must order: t0 (80), t1 (90), t2 (100)
    h_ts = [x['timestamp'] for x in rt.history[patient]]
    assert h_ts == [t0, t1, t2]
    assert rt.history[patient][-1]['hr_curr'] == 100.0


@pytest.mark.parametrize('pattern', ['stable', 'deteriorating', 'recovering', 'irregular', 'missing'])
def test_13_runtime_and_canonical_training_features_match(pattern):
    rt = Runtime()
    patient = f'PARITY-{pattern}'
    start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    offsets = [0, 1, 2, 3, 4] if pattern != 'irregular' else [0, 0.5, 2.25, 3, 4]
    history = []
    for index, hours in enumerate(offsets):
        trend = {'stable': 0, 'deteriorating': index * 5, 'recovering': (4-index) * 5,
                 'irregular': index * 2, 'missing': index * 3}[pattern]
        history.append({
            'timestamp': start + timedelta(hours=hours),
            'heart_rate': None if pattern == 'missing' and index == 2 else 80 + trend,
            'map': 75 - trend / 2, 'resp_rate': 16 + trend / 5,
            'spo2': 98 - trend / 10, 'temperature_c': 37 + trend / 50,
            'lactate': 1.2 if index == 0 else None,
        })
    rt.history[patient] = [{
        'timestamp': event['timestamp'], 'hr_curr': event['heart_rate'],
        'map_curr': event['map'], 'rr_curr': event['resp_rate'],
        'spo2_curr': event['spo2'], 'temp_curr': event['temperature_c'],
        'lactate': event['lactate'],
    } for event in history]
    expected = build_feature_row(history)
    actual_vector, actual_row = rt.features(patient)
    expected_vector = np.array([expected[name] for name in CANONICAL_FEATURES])
    assert CANONICAL_FEATURES == FEATURES
    assert np.allclose(actual_vector, expected_vector, rtol=0, atol=1e-12, equal_nan=True)
    assert set(actual_row) == set(expected)
