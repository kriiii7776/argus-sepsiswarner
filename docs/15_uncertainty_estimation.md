# Predictive Uncertainty in SepsisGuard AI

## Meaning

SepsisGuard reports **predictive confidence**, not clinical certainty.

- Risk is the calibrated model estimate for the defined six-hour prediction target (for example, `78%`).
- Uncertainty describes instability or limited reliability of that estimate (for example, `78% ± 14%`, interval `[64%, 92%]`).
- Confidence (`HIGH`, `MEDIUM`, `LOW`) is a readable reliability category derived from interval width and input signal quality.
- None of these establishes infection, diagnosis, treatment need, or clinical certainty. Clinical assessment and repeat measurement remain required, especially for a high-risk/low-confidence alert.

## Practical methods

| Method | Where used | Output | Status |
|---|---|---|---|
| Ensemble variance | Tree and temporal probabilities, or independent base models | Mean, standard deviation, disagreement | Practical hybrid default. |
| Monte Carlo dropout | GRU/TCN with dropout active for 30 draws | Draw mean/standard deviation | Optional; tree models do not support it. |
| Split conformal prediction | Patient-disjoint calibration patients after probability calibration | Outcome-compatible interval | Recommended; report empirical coverage. |
| Calibrated probability interval | Calibrated mean plus conformal residual interval | `p ± half-width`, `[lower, upper]` | Serving format, not an individual true-probability CI. |

`src/pipeline/09_uncertainty.py` implements these methods. The conformal score is `|y − p|` on calibration patients. Its residual quantile is fixed before validation/test. Under exchangeability the resulting interval has marginal outcome coverage, not a guarantee for an individual patient, subgroup, or distribution shift.

## Leakage-safe fitting protocol

```
Train patients       → base-model fitting / OOF ensemble selection
Calibration patients → Platt calibration and conformal quantile
Validation patients  → choose uncertainty alert-priority policy
Frozen test patients → final interval coverage and triage reporting
```

Patient IDs must be disjoint across roles. Do not use test coverage, PPV, sensitivity, or interval width to set a conformal level, uncertainty cut-off, or alert policy. MC-dropout draws use the same causal sequence and train-fitted normalizer.

## Alert-priority evaluation

`evaluate_alert_prioritization` compares validation risk-only alerts with high-priority alerts meeting both the risk threshold and a predeclared maximum interval width. Excluded alerts are counted as `REVIEW_SIGNAL`, not dropped. It reports PPV change, sensitivity change, review-alert rate, and positives in review alerts.

Uncertainty improves prioritization only when validation shows a useful PPV increase at an acceptable sensitivity loss and review burden. This has not yet been measured because shared-split hybrid base predictions and a separate calibration/validation role are unavailable. No benefit claim should be made until that artifact exists.

## Serving example

```json
{
  "risk_probability": 0.78,
  "uncertainty": {
    "interval_lower": 0.64,
    "interval_upper": 0.92,
    "uncertainty_plus_minus": 0.14,
    "ensemble_std": 0.07
  },
  "confidence": "MEDIUM",
  "alert_priority": "HIGH"
}
```

The hybrid serving contract accepts this uncertainty summary and combines its confidence score with signal quality. A high risk with a wide interval or LOW signal quality can become `REVIEW_SIGNAL`; the risk probability is never reduced or hidden.
