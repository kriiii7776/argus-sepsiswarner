# SepsisGuard Smart-Alert Engine

## Purpose and boundary

The smart-alert engine is a stateful presentation policy over model outputs. It
does not diagnose sepsis, change the risk probability, or prescribe clinical
treatment. Its only output is an alert severity and a recommended **clinical
review level**. Thresholds are starting policy values, not validated clinical
standards; tune them solely on patient-disjoint validation data.

## Inputs

Each prediction window supplies calibrated AI risk, risk trajectory per hour,
predictive confidence, signal quality, available clinical-score context,
persistence count, alert history/state, timestamp, and non-causal contributing
factors. A clinical score that is unavailable or partial is labelled as such;
it cannot manufacture a severity increase.

## Alert levels

| Severity | Entry policy | Output review level |
|---|---|---|
| **YELLOW — WATCH** | Risk ≥ 25%, sustained for two windows | Watch — routine clinical review |
| **ORANGE — REVIEW** | Risk ≥ 35%, sustained for two windows; or YELLOW with risk rise ≥10%/hour | Review — prompt clinical review |
| **RED — URGENT** | Risk ≥ 70% | Urgent — urgent clinical review |

If confidence or signal quality is not HIGH, a RED alert below 85% risk is
presented as ORANGE with the reliability concern in the reason. This does not
decrease or hide the risk; it prevents an unqualified high-priority signal
where the input or model estimate is uncertain.

Reasons combine policy-band risk, trajectory, persistence, score context when
valid, confidence/signal-quality limitations, and model contributing factors.
Attributions are always described as contributions to the model prediction,
not causes of deterioration.

## Hysteresis and de-duplication

- Escalation to YELLOW/ORANGE requires two consecutive qualifying windows;
  RED escalates immediately.
- De-escalation or closure requires three consecutive windows below the active
  band, preventing risk around a boundary from toggling the alert.
- A stable alert is emitted once, then de-duplicated for six hours (two hours
  for RED). Escalation emits a new alert immediately.
- Repeated alerts retain their state and timestamp history; a suppressed alert
  includes a machine-readable reason such as `duplicate within repeat interval`
  or `hysteresis hold during improvement`.

The policy is implemented in `src/pipeline/11_smart_alert_engine.py`.

## Burden evaluation

Apply `evaluate_policy_stream` to a chronologically ordered, patient-level
validation stream. It reports:

- alerts per patient-day;
- false alerts and false-alert rate (with an outcome definition specified in
  advance);
- median active-alert duration;
- repeat alerts and repeat-alert rate;
- total alert count and review-signal burden.

Compare the smart policy with a risk-only policy at matched sensitivity.
Report sensitivity, PPV, alert rate, false alerts, alert duration, repeats,
and patient-day burden. A reduction in alerts is acceptable only if the
pre-specified sensitivity loss is acceptable; it must not be claimed from
unmeasured or test-tuned results.

## Output shape

```json
{
  "alert_severity": "ORANGE — REVIEW",
  "reason": ["AI risk 48% is in the review policy band", "deterioration persisted for 2 windows"],
  "contributing_factors": ["MAP trend contributed to the model prediction"],
  "trend": {"risk_trajectory_per_hour": 0.12, "persistent_windows": 2},
  "confidence": "MEDIUM",
  "timestamp": "2100-01-01T12:00:00Z",
  "recommended_clinical_review_level": "REVIEW — prompt clinical review"
}
```
