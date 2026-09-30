# Signal-Quality Layer

## Processing contract

```
raw value → causal quality assessment → usable value + quality features → model → confidence / alert priority
```

`data/04_signal_quality.py` preserves every `*_raw_value` for audit. It does
not remove physiologically abnormal but plausible observations. A plausible
SpO₂ of 72%, MAP of 35 mmHg, or HR of 180 bpm remains a usable model value;
the accompanying flags let the model and UI express uncertainty. Only values
outside broad physiological possibility bounds become `*_usable_value = NaN`.
The raw record and reason remain available for review.

## Causal heuristics where waveform data are unavailable

| Signal | Possible range | Abrupt-change flag | Stale exact value | Maximum measurement age |
|---|---:|---:|---:|---:|
| HR | 20–250 bpm | >50 bpm/hour | 4 hours | 2 hours |
| MAP | 15–200 mmHg | >40 mmHg/hour | 4 hours | 2 hours |
| SBP, if supplied | 30–300 mmHg | >60 mmHg/hour | 4 hours | 2 hours |
| SpO₂ | 50–100% | >8 percentage points/hour | 3 hours | 2 hours |
| RR | 4–60/min | >20/min/hour | 4 hours | 2 hours |
| Temperature | 30–43°C | >2°C/hour | 6 hours | 4 hours |

An optional within-bin standard deviation is consumed when multiple raw
observations were aggregated. Variability greater than half the signal's jump
threshold marks a soft concern. All rules inspect the current and prior values
only; they never use a subsequent stabilizing/rebounding observation, which
would cause temporal leakage.

## Quality classification

Each stream begins at score 2. An abrupt change, exact repeated feed, or high
within-bin variability removes one point. An over-age measurement removes two.
Missing or physiologically impossible values are LOW. Scores map to HIGH=2,
MEDIUM=1, LOW=0. The overall `signal_quality` is the lowest currently observed
vital score—conservative for alert presentation. Per-signal reasons are stored
as `*_quality_reason`; model features include score, impossible, abrupt,
stale, stale-or-missing, and high-variability flags.

## Confidence and alert priority

Risk probability is never mechanically reduced by signal quality. Quality
changes only presentation confidence and priority:

| Quality | Confidence multiplier | Risk ≥ 0.35 priority |
|---|---:|---|
| HIGH | 1.00 | HIGH; URGENT at ≥0.70 |
| MEDIUM | 0.75 | HIGH |
| LOW | 0.50 | REVIEW_SIGNAL |

This prevents a possible artifact from producing an unqualified page while
also avoiding suppression of a potentially real crisis. `REVIEW_SIGNAL` means
repeat/verify the measurement and review the patient; it is not a claim that
the patient is safe.

## Limitations

- Without waveforms, pleth quality, cuff status, lead-off telemetry, and
  clinician annotations, these are heuristics—not an artifact detector.
- True rapid deterioration can trigger an abrupt-change flag. The value is
  retained specifically for this reason.
- Repeated exact values can represent stable physiology or device rounding,
  not only a stale feed.
- Fixed broad ranges and thresholds require site-specific validation, monitor
  metadata, and subgroup audit before clinical deployment.
- Quality labels should not be used as sepsis labels or as a reason to discard
  low-quality windows from evaluation; report their coverage and performance
  separately.
