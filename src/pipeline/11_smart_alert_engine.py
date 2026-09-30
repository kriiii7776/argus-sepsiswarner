"""Stateful, non-prescriptive smart alerts for SepsisGuard AI.

The engine is a policy layer. It does not alter risk, diagnose sepsis, or
recommend treatment. Tune policy parameters on validation patients only.
"""
from dataclasses import dataclass, field
from datetime import timedelta
import numpy as np
import pandas as pd

YELLOW, ORANGE, RED = 'YELLOW — WATCH', 'ORANGE — REVIEW', 'RED — URGENT'
RANK = {None: 0, YELLOW: 1, ORANGE: 2, RED: 3}

@dataclass
class AlertState:
    severity: str | None = None
    started_at: object | None = None
    last_emitted_at: object | None = None
    last_risk: float | None = None
    consecutive_risk_windows: int = 0
    below_current_windows: int = 0
    alert_history: list = field(default_factory=list)

@dataclass
class AlertPolicy:
    """Predeclared default thresholds; calibrate only on patient validation data."""
    yellow_risk: float = .25
    orange_risk: float = .35
    red_risk: float = .70
    escalation_windows: int = 2
    deescalation_windows: int = 3
    repeat_hours: float = 6.
    red_repeat_hours: float = 2.
    escalation_delta: float = .10
    low_confidence_red_floor: float = .85

class SmartAlertEngine:
    def __init__(self, policy=None): self.policy = policy or AlertPolicy()

    def _candidate(self, event):
        """Risk + evidence; LOW confidence/quality limits but never hides risk."""
        risk = float(event['risk_probability'])
        conf = str(event.get('confidence', 'LOW')).upper()
        quality = str(event.get('signal_quality', 'LOW')).upper()
        trajectory = float(event.get('risk_trajectory_per_hour', 0.))
        persistence = int(event.get('persistent_windows', 0))
        score = event.get('clinical_score_level', 'UNAVAILABLE')
        factors = event.get('contributing_factors', [])
        reasons = []
        if risk >= self.policy.red_risk: severity = RED; reasons.append(f'AI risk {risk:.0%} is in the urgent policy band')
        elif risk >= self.policy.orange_risk: severity = ORANGE; reasons.append(f'AI risk {risk:.0%} is in the review policy band')
        elif risk >= self.policy.yellow_risk: severity = YELLOW; reasons.append(f'AI risk {risk:.0%} is in the watch policy band')
        else: severity = None
        if trajectory >= self.policy.escalation_delta:
            reasons.append(f'risk increased by {trajectory:.0%} per hour')
            if severity == YELLOW: severity = ORANGE
        if persistence >= self.policy.escalation_windows:
            reasons.append(f'deterioration persisted for {persistence} windows')
        if score not in (None, 'UNAVAILABLE', 'PARTIAL'):
            reasons.append(f'clinical-score context: {score}')
        if conf != 'HIGH' or quality != 'HIGH':
            reasons.append(f'predictive confidence {conf}; signal quality {quality}')
            # A high-risk but unreliable signal becomes review rather than an
            # unqualified urgent page unless risk crosses a stricter floor.
            if severity == RED and risk < self.policy.low_confidence_red_floor: severity = ORANGE
        if not factors: factors = ['No feature-level explanation available at this prediction anchor.']
        review = {YELLOW: 'WATCH — routine clinical review', ORANGE: 'REVIEW — prompt clinical review',
                  RED: 'URGENT — urgent clinical review'}.get(severity, 'No alert')
        return severity, reasons, factors, review

    def process(self, event, state=None):
        """Return a policy decision and updated state for a single patient window."""
        state = state or AlertState()
        now = pd.Timestamp(event['timestamp'])
        risk = float(event['risk_probability'])
        candidate, reasons, factors, review = self._candidate(event)
        if risk >= self.policy.yellow_risk: state.consecutive_risk_windows += 1
        else: state.consecutive_risk_windows = 0
        emitted, suppressed_reason = False, None
        current = state.severity
        # Hysteresis: escalation is immediate for RED or sustained for lower
        # bands; de-escalation requires consecutive windows below the band.
        if RANK[candidate] > RANK[current]:
            state.below_current_windows = 0
            if candidate == RED or state.consecutive_risk_windows >= self.policy.escalation_windows:
                state.severity, state.started_at, emitted = candidate, now, True
            else: suppressed_reason = 'awaiting persistence before escalation'
        elif candidate and RANK[candidate] == RANK[current]:
            state.below_current_windows = 0
            interval = self.policy.red_repeat_hours if candidate == RED else self.policy.repeat_hours
            if state.last_emitted_at is None or now - state.last_emitted_at >= pd.Timedelta(hours=interval): emitted = True
            else: suppressed_reason = 'duplicate within repeat interval'
        elif RANK[candidate] < RANK[current]:
            # Require a sustained drop below current band before closing/downgrading.
            state.below_current_windows += 1
            if state.below_current_windows >= self.policy.deescalation_windows:
                state.severity, state.started_at, emitted = candidate, (now if candidate else None), bool(candidate)
                state.below_current_windows = 0
            else: suppressed_reason = 'hysteresis hold during improvement'
        else:
            suppressed_reason = 'risk below watch threshold'
            state.below_current_windows = 0
        if emitted:
            state.last_emitted_at = now
            state.alert_history.append({'timestamp': now, 'severity': state.severity})
        state.last_risk = risk
        return {'alert_emitted': emitted, 'alert_severity': state.severity if emitted else candidate,
                'active_severity': state.severity, 'reason': reasons, 'contributing_factors': factors,
                'trend': {'risk_trajectory_per_hour': event.get('risk_trajectory_per_hour', 0.),
                          'persistent_windows': event.get('persistent_windows', 0)},
                'confidence': event.get('confidence', 'LOW'), 'signal_quality': event.get('signal_quality', 'LOW'),
                'timestamp': str(now), 'recommended_clinical_review_level': review,
                'suppression_reason': suppressed_reason, 'state': state}, state

def evaluate_alert_burden(events, patient_col='subject_id', time_col='timestamp', label_col='label'):
    """Compute patient-day burden on a validation/test event stream.

    A false alert is an emitted alert on a label-negative prediction window;
    use a prospectively specified event-level or patient-level outcome mapping
    in real evaluation, not this convenience definition alone.
    """
    d = pd.DataFrame(events).copy()
    if not len(d): return {}
    d[time_col] = pd.to_datetime(d[time_col]); emitted = d[d.alert_emitted.astype(bool)].copy()
    patient_days = max((d.groupby(patient_col)[time_col].max() - d.groupby(patient_col)[time_col].min()).dt.total_seconds().sum()/86400, 1.)
    false = emitted[label_col].eq(0).sum() if label_col in emitted else np.nan
    durations = []
    for _, group in d.groupby(patient_col):
        active = group[group.active_severity.notna()].sort_values(time_col)
        if len(active): durations.append((active[time_col].max()-active[time_col].min()).total_seconds()/3600)
    repeats = max(len(emitted) - emitted.groupby(patient_col).size().size, 0)
    return {'alerts': int(len(emitted)), 'alerts_per_patient_day': float(len(emitted)/patient_days),
            'false_alerts': None if pd.isna(false) else int(false),
            'false_alert_rate': None if pd.isna(false) else float(false/max(len(emitted), 1)),
            'median_alert_duration_hours': float(np.median(durations)) if durations else 0.,
            'repeat_alerts': int(repeats), 'repeat_alert_rate': float(repeats/max(len(emitted), 1)),
            'alert_burden_note': 'Compare with risk-only policy at matched sensitivity on validation patients.'}

def evaluate_policy_stream(event_rows, policy=None):
    """Apply per-patient state in chronological order and return decisions + burden."""
    d = pd.DataFrame(event_rows).sort_values(['subject_id', 'timestamp']).copy(); output = []
    for patient, group in d.groupby('subject_id', sort=False):
        engine, state = SmartAlertEngine(policy), AlertState()
        for row in group.to_dict('records'):
            decision, state = engine.process(row, state)
            output.append({**row, **{k: v for k, v in decision.items() if k != 'state'}})
    return pd.DataFrame(output), evaluate_alert_burden(output)
