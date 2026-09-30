# Personalized Physiological Baselines

## Exact construction

`add_personalized_baseline_features` in
`data/03_feature_engineering.py` builds a baseline separately for every
`(subject_id, stay_id)` and measurement. It uses the original observed value,
not a carried-forward value.

For a prediction at hourly time `t`, the eligible reference history is:

```
[t - 25 hours, t - 2 hours]
```

The current bin and immediately preceding hour are excluded. Thus no
measurement at time `t` or later can affect the baseline used at `t`; the
one-hour exclusion also prevents immediate deterioration from redefining a
patient's normal state. The reference interval is capped at 24 hours so a
remote ICU state does not dominate the current admission state.

For eligible observed values `x`, the features are:

```
baseline               = median(x)
baseline_mad           = 1.4826 × median(|x - median(x)|)
deviation_from_baseline = current_value - baseline
baseline_z             = deviation_from_baseline / baseline_mad
```

Median/MAD is used rather than mean/standard deviation because ICU reference
history commonly contains outliers and early transient interventions. `z` is
not emitted when its denominator is too small or the history is unreliable.

## Measurements and reliability rules

| Measurement | Minimum observed history | Minimum robust scale for z-score |
|---|---:|---:|
| HR | 4 | 3 bpm |
| MAP | 4 | 2 mmHg |
| RR | 4 | 1 /min |
| SpO₂ | 4 | 0.5 percentage points |
| Temperature | 4 | 0.1 °C |
| Laboratory value | 3 | Near-zero numerical floor unless configured per assay |

The function supports HR, BP/MAP, RR, SpO₂, temperature, and any provided
laboratory columns (such as lactate, creatinine, WBC, or platelets). It emits
`baseline_n`, `baseline_age_hr`, `baseline_available`,
`baseline_insufficient`, `baseline_unstable`, and `baseline_state_shift` for
each measurement.

- Newly admitted / insufficient history: no usable baseline or z-score; flags
  remain visible to the model.
- Missing current measurement: baseline history may exist, but no current
  deviation is fabricated.
- Unstable baseline: fewer than required observations or MAD below the
  measurement floor; raw deviation may be present but z-score is missing.
- Changing state: the causal median from the preceding three hours is more
  than three robust scales from the reference baseline. This raises a flag; it
  does not silently move the baseline.

These choices prevent a sustained, worsening state from being treated as the
patient's new normal. No patient-level value is borrowed from another patient,
and no labels, interventions, outcome timestamps, future records, backfill, or
global distribution statistic enters construction.

## Ablation evaluation

`src/pipeline/08_personalized_baseline_ablation.py` compares XGBoost with the
same patient-level partitions in two arms: existing engineered features only,
then the same features plus personalized baseline features. Each arm tunes on
train patients, early-stops and calibrates on validation patients, and predicts
test once. The chosen arm is determined by validation AUPRC (with test results
reported only after choice).

Outputs are `model/personalized_baseline_ablation.csv` and
`model/personalized_baseline_ablation_decision.json`. Do not claim a benefit
until that run is completed with the intended real cohort; the fallback demo is
only a pipeline smoke test.
