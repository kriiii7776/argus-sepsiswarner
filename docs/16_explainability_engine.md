# Explainability Engine

## Scope and language boundary

SepsisGuard explanations report which model inputs **contributed to the model prediction** at a specified prediction timestamp. They do not show what **caused patient deterioration**, diagnose sepsis, establish mechanisms, or recommend treatment. Every rendered explanation includes this boundary.

## Methods by model component

| Component | Global explanation | Local explanation | Time-dependent explanation |
|---|---|---|---|
| XGBoost / LightGBM | Mean absolute TreeSHAP values | Exact native TreeSHAP contributions in log-odds | Not applicable: tabular features summarize the anchor history. |
| Logistic Regression | Absolute standardized coefficient | Signed coefficient × feature contribution | Not applicable. |
| GRU / LSTM / TCN | Mean absolute integrated gradients across validation windows | Integrated gradients for one sequence | Signed attribution for every `(time bin, feature)` pair. |
| Hybrid | Base-model explanations displayed separately, plus fusion weight/disagreement | Preserve source model provenance | Temporal attribution remains time indexed. |

`src/pipeline/10_explainability.py` uses XGBoost and LightGBM native
`pred_contrib` APIs for TreeSHAP, avoiding a silent fallback. In this current
environment the external SHAP package cannot import because a system policy
blocks Numba; the native TreeSHAP path is the supported implementation for
fitted tree artifacts. Do not label gain importance as SHAP.

## Output contract

Local explanations provide the base score, local signed contribution, absolute magnitude, ranking, feature name, and direction. Positive TreeSHAP values increased the model log-odds; negative values decreased them. Magnitude is relative to that prediction's attribution distribution (`small`, `moderate`, `large`) and not a measure of biological importance.

Example renderer output:

```text
Risk increased in the model primarily because:
- Mean arterial pressure contributed a large increase to the model score.
- Heart rate contributed a moderate increase to the model score.
- Respiratory rate contributed a moderate increase to the model score.
- Lactate contributed a moderate increase to the model score.

These factors contributed to this model prediction. They do not establish that
they caused patient deterioration, sepsis, or a need for a particular treatment.
```

The renderer deliberately does not say “MAP decreased” unless an upstream
feature has already encoded a causal-past trend such as `map_delta_4h`; it
still calls that a model-input contribution rather than a causal explanation.

## Temporal explanation

Integrated gradients compares the observed causal sequence with a declared
reference sequence such as an all-causal-imputed neutral reference. The
reference must be defined before evaluation and cannot contain future data.
The output table lists time index/timestamp, feature, signed attribution, and
magnitude, allowing a clinician to see whether a recent versus earlier value
contributed to a temporal prediction. Attribution stability should be assessed
on validation windows before display.

## Counterfactual / model recourse

`model_recourse_counterfactual` is deliberately limited to **model-input
sensitivity**. It searches declared mutable features against observed,
pre-anchor reference values within physiological/operational bounds and reports
the smallest single input change that would move the model probability below a
target. It must never use future values from the same patient as candidates.

The output is defensible only as: “under this model, changing this valid input
to this reference value would change the prediction.” It is not a treatment
recommendation, an achievable intervention claim, a prediction of response, or
evidence of causation. Do not generate counterfactuals for immutable features,
features without a clinically vetted feasible range, missing inputs, or models
outside their validated population.

## Validation requirements

Before clinical display, evaluate explanation completeness (additive TreeSHAP
sum vs model score), stability across nearby windows, feature-missingness
behavior, subgroup consistency, and clinician review for misleading language.
Store prediction timestamp, model version, feature values, attribution method,
reference background/version, and explanation output for audit. Evaluate
counterfactual coverage and plausibility separately; do not rank models by how
persuasive their explanations sound.
