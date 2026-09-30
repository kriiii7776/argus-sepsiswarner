"""Causal signal-quality features for binned ICU vital signs.

This is not an outlier-deletion routine. Raw observations remain untouched;
quality flags tell the model and clinical interface how much to trust them.
"""
import numpy as np
import pandas as pd

QUALITY_HIGH, QUALITY_MEDIUM, QUALITY_LOW = 'HIGH', 'MEDIUM', 'LOW'

# Physiologically impossible bounds are intentionally broad. Values inside the
# bounds can be very abnormal and are retained as possible true deterioration.
VITAL_SPECS = {
    'hr_curr':   {'low': 20., 'high': 250., 'jump': 50., 'stale_hours': 4, 'max_age': 2},
    'map_curr':  {'low': 15., 'high': 200., 'jump': 40., 'stale_hours': 4, 'max_age': 2},
    'sbp':       {'low': 30., 'high': 300., 'jump': 60., 'stale_hours': 4, 'max_age': 2},
    'spo2_curr': {'low': 50., 'high': 100., 'jump': 8.,  'stale_hours': 3, 'max_age': 2},
    'rr_curr':   {'low': 4.,  'high': 60.,  'jump': 20., 'stale_hours': 4, 'max_age': 2},
    'temp_curr': {'low': 30., 'high': 43.,  'jump': 2.,  'stale_hours': 6, 'max_age': 4},
}

def _quality_from_score(score):
    return QUALITY_LOW if score <= 0 else QUALITY_MEDIUM if score == 1 else QUALITY_HIGH

def add_signal_quality_features(df, vital_specs=None, group_col='stay_id', time_col='hour'):
    """Add causal quality indicators and usable values to hourly observations.

    Inputs should be chronologically ordered hourly bins. Optional columns
    `<vital>_obs_count`, `<vital>_within_bin_std`, and
    `time_since_<vital>_hr` are consumed when available. No later observation
    is inspected, so quality can be calculated identically at serving time.

    `*_raw_value` preserves the source. `*_usable_value` equals the raw value
    for every plausible reading, including a LOW-quality plausible extreme;
    only physically impossible values become NaN for model consumption.
    """
    specs = vital_specs or VITAL_SPECS
    out = df.copy()
    if group_col not in out or time_col not in out:
        raise ValueError(f'Require {group_col!r} and {time_col!r} for causal signal quality.')
    out['_quality_order'] = np.arange(len(out))
    out = out.sort_values([group_col, time_col]).copy()
    available = {v: s for v, s in specs.items() if v in out.columns}

    for vital, spec in available.items():
        raw = pd.to_numeric(out[vital], errors='coerce')
        out[f'{vital}_raw_value'] = raw
        out[f'{vital}_quality_score'] = 2
        out[f'{vital}_quality_reason'] = ''
        out[f'{vital}_physiologically_impossible'] = ((raw < spec['low']) | (raw > spec['high'])).astype('int8')
        out[f'{vital}_abrupt_change'] = 0
        out[f'{vital}_stale_signal'] = 0
        out[f'{vital}_stale_or_missing'] = 0
        out[f'{vital}_high_variability'] = 0
        out[f'{vital}_usable_value'] = raw.where(out[f'{vital}_physiologically_impossible'].eq(0))

        for _, idx in out.groupby(group_col, sort=False).groups.items():
            vals = raw.loc[idx].to_numpy(dtype=float)
            ages = (pd.to_numeric(out.loc[idx, f'time_since_{vital}_hr'], errors='coerce').to_numpy(dtype=float)
                    if f'time_since_{vital}_hr' in out else np.where(np.isfinite(vals), 0., np.inf))
            variability = (pd.to_numeric(out.loc[idx, f'{vital}_within_bin_std'], errors='coerce').to_numpy(dtype=float)
                           if f'{vital}_within_bin_std' in out else np.zeros(len(idx)))
            for pos, row in enumerate(idx):
                reasons, score = [], 2
                impossible = not np.isfinite(vals[pos]) or vals[pos] < spec['low'] or vals[pos] > spec['high']
                if impossible:
                    score = 0; reasons.append('missing_or_physiologically_impossible')
                else:
                    if pos and np.isfinite(vals[pos-1]) and abs(vals[pos] - vals[pos-1]) > spec['jump']:
                        score -= 1; reasons.append('abrupt_change')
                        out.at[row, f'{vital}_abrupt_change'] = 1
                    # Identical hourly values often represent a stale monitor
                    # feed. They are not erased, because stable physiology is
                    # also possible.
                    start = max(0, pos - spec['stale_hours'] + 1)
                    recent = vals[start:pos+1]
                    if len(recent) == spec['stale_hours'] and np.isfinite(recent).all() and np.ptp(recent) == 0:
                        score -= 1; reasons.append('repeated_exact_value')
                        out.at[row, f'{vital}_stale_signal'] = 1
                    if np.isfinite(variability[pos]) and variability[pos] > spec['jump'] / 2:
                        score -= 1; reasons.append('high_within_bin_variability')
                        out.at[row, f'{vital}_high_variability'] = 1
                    if not np.isfinite(ages[pos]) or ages[pos] > spec['max_age']:
                        score -= 2; reasons.append('stale_measurement')
                        out.at[row, f'{vital}_stale_or_missing'] = 1
                out.at[row, f'{vital}_quality_score'] = max(0, score)
                out.at[row, f'{vital}_quality_reason'] = '|'.join(reasons) or 'no_quality_concern'
        out[f'{vital}_signal_quality'] = out[f'{vital}_quality_score'].map(_quality_from_score)

    quality_cols = [f'{v}_quality_score' for v in available]
    if quality_cols:
        # Conservative patient-level interface signal: the least reliable
        # currently available stream governs overall quality.
        out['signal_quality_score'] = out[quality_cols].min(axis=1)
        out['signal_quality'] = out['signal_quality_score'].map(_quality_from_score)
    return out.sort_values('_quality_order').drop(columns='_quality_order')

def adjust_confidence_and_priority(model_confidence, risk_probability, signal_quality):
    """Apply a transparent interface modifier; never change the risk itself."""
    quality = str(signal_quality).upper()
    factor = {QUALITY_HIGH: 1.0, QUALITY_MEDIUM: .75, QUALITY_LOW: .50}.get(quality, .50)
    adjusted = float(np.clip(model_confidence * factor, 0., 1.))
    if risk_probability >= .70 and quality == QUALITY_HIGH: priority = 'URGENT'
    elif risk_probability >= .35 and quality != QUALITY_LOW: priority = 'HIGH'
    elif risk_probability >= .35: priority = 'REVIEW_SIGNAL'
    else: priority = 'ROUTINE'
    return {'signal_quality': quality, 'confidence_multiplier': factor,
            'adjusted_confidence': adjusted, 'alert_priority': priority}
