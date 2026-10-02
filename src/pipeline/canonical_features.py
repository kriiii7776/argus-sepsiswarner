"""Canonical causal feature definitions shared by training and inference."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any

FEATURES = [
    'hr_curr', 'map_curr', 'rr_curr', 'spo2_curr', 'temp_curr',
    'hr_mean_4h', 'hr_std_4h', 'hr_min_4h', 'hr_max_4h',
    'map_mean_4h', 'map_std_4h', 'map_min_4h',
    'rr_mean_4h', 'temp_mean_4h',
    'hr_delta_1h', 'hr_delta_4h', 'hr_slope_4h',
    'map_delta_1h', 'map_delta_4h', 'map_slope_4h',
    'rr_delta_1h', 'temp_delta_1h', 'hr_accel',
    'shock_index', 'resp_distress_idx', 'fever_response_idx',
    'lactate_missing', 'time_since_lactate',
    'qsofa_curr', 'map_time_low_4h', 'icu_hour',
]
VITALS = {
    'hr_curr': 'heart_rate', 'map_curr': 'map', 'rr_curr': 'resp_rate',
    'spo2_curr': 'spo2', 'temp_curr': 'temperature_c',
}


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def build_feature_row(history: list[dict[str, Any]]) -> dict[str, float]:
    """Build one causal vector from a patient's timestamped event history.

    Window: inclusive [t - 4 hours, t]. Baseline deltas use the latest
    observation at or before t-1h / t-4h; when the four-hour baseline is not
    yet available, use the first observation in the current four-hour window.
    Slopes divide by actual elapsed clinical hours.
    """
    if not history:
        raise ValueError('Cannot build features from empty history')
    events = sorted(history, key=lambda item: item['timestamp'])
    current = events[-1]
    now = current['timestamp']
    first = events[0]['timestamp']
    window_start = now - timedelta(hours=4)
    window = [e for e in events if window_start <= e['timestamp'] <= now]
    row: dict[str, float] = {
        feature: (_number(current.get(source)) if _number(current.get(source)) is not None else math.nan)
        for feature, source in VITALS.items()
    }

    def values(key: str, rows: list[dict[str, Any]]) -> list[float]:
        return [v for event in rows if (v := _number(event.get(key))) is not None]

    def stats(key: str) -> tuple[float, float, float, float]:
        vals = values(key, window)
        if not vals:
            fallback = row.get(key, math.nan)
            return fallback, 0.0, fallback, fallback
        mean = sum(vals) / len(vals)
        std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        return mean, std, min(vals), max(vals)

    hr_mean, hr_std, hr_min, hr_max = stats('heart_rate')
    map_mean, map_std, map_min, _ = stats('map')
    rr_mean, _, _, _ = stats('resp_rate')
    temp_mean, _, _, _ = stats('temperature_c')
    row.update({
        'hr_mean_4h': hr_mean, 'hr_std_4h': hr_std, 'hr_min_4h': hr_min, 'hr_max_4h': hr_max,
        'map_mean_4h': map_mean, 'map_std_4h': map_std, 'map_min_4h': map_min,
        'rr_mean_4h': rr_mean, 'temp_mean_4h': temp_mean,
    })

    def baseline(hours: int) -> dict[str, Any] | None:
        cutoff = now - timedelta(hours=hours)
        candidates = [e for e in events if e['timestamp'] <= cutoff]
        if candidates:
            return candidates[-1]
        if hours == 4 and len(window) > 1:
            return window[0]
        return None

    one_hour = baseline(1)
    four_hour = baseline(4)
    two_hour = baseline(2)

    def delta(key: str, event: dict[str, Any] | None) -> float:
        value, prior = _number(current.get(key)), _number(event.get(key)) if event else None
        return value - prior if value is not None and prior is not None else 0.0

    for key, feature in [('heart_rate', 'hr_delta_1h'), ('map', 'map_delta_1h'),
                         ('resp_rate', 'rr_delta_1h'), ('temperature_c', 'temp_delta_1h')]:
        row[feature] = delta(key, one_hour)
    elapsed_4h = max((now - four_hour['timestamp']).total_seconds() / 3600.0, 0.001) if four_hour else 4.0
    for key, delta_name, slope_name in [('heart_rate', 'hr_delta_4h', 'hr_slope_4h'),
                                        ('map', 'map_delta_4h', 'map_slope_4h')]:
        amount = delta(key, four_hour)
        row[delta_name] = amount
        row[slope_name] = amount / elapsed_4h
    current_hr = _number(current.get('heart_rate'))
    one_hour_hr = _number(one_hour.get('heart_rate')) if one_hour else None
    two_hour_hr = _number(two_hour.get('heart_rate')) if two_hour else None
    row['hr_accel'] = (
        (current_hr - one_hour_hr) - (one_hour_hr - two_hour_hr)
        if current_hr is not None and one_hour_hr is not None and two_hour_hr is not None
        else 0.0
    )

    def current_or_default(key: str, default: float) -> float:
        value = row[key]
        return value if math.isfinite(value) else default

    hr = current_or_default('hr_curr', 80.0)
    map_value = current_or_default('map_curr', 75.0)
    rr = current_or_default('rr_curr', 16.0)
    spo2 = current_or_default('spo2_curr', 98.0)
    temp = current_or_default('temp_curr', 37.0)
    row.update({
        'shock_index': hr / max(map_value, 1.0),
        'resp_distress_idx': rr / max(spo2, 1.0),
        'fever_response_idx': hr - 10.0 * (temp - 37.0),
        'qsofa_curr': float(int(rr >= 22) + int(map_value <= 65)),
        'lactate_missing': float(current.get('lactate') is None),
    })
    lactate_events = [e for e in events if _number(e.get('lactate')) is not None]
    elapsed = max(0.0, (now - first).total_seconds() / 3600.0)
    row['time_since_lactate'] = min(elapsed, 8.0) if not lactate_events else max(
        0.0, (now - lactate_events[-1]['timestamp']).total_seconds() / 3600.0)
    row['map_time_low_4h'] = float(sum(
        1 for event in window
        if (value := _number(event.get('map'))) is not None and value < 65
    ))
    row['icu_hour'] = elapsed
    return row
