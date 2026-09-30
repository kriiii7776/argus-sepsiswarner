# Hybrid SepsisGuard AI

## Decision boundary

The hybrid combines a calibrated tree model (XGBoost or LightGBM) with a
calibrated temporal encoder (GRU or TCN). It is an experiment, not a default
replacement for either base model. It may be selected only if its **measured,
patient-level validation** AUPRC and calibration improve on the selected base
model without an unacceptable alert increase. Test data are never used to set
weights, fit a stacker, calibrate, choose a strategy, or choose a threshold.

## Fusion approaches

| Approach | Practicality | Leakage-safe training | Assessment |
|---|---|---|---|
| Probability average | High | No fitted parameters | Required reference: robust, transparent fallback. |
| Weighted ensemble | High | Fit one weight from patient-grouped OOF train predictions | Recommended first learned fusion; easy to audit. |
| Late fusion | Medium-high | Fit regularized logistic model on OOF probabilities and disagreement | Useful when models have complementary failure modes; preserves model provenance. |
| Stacking | Medium | Fit regularized meta-learner on OOF base predictions only | Evaluate, but penalize complexity; never feed in-sample base predictions. |
| Feature-level fusion | Low for current cohort | Joint training of temporal representation and tabular features, with all preprocessing fit within each fold | Deferred. It changes the model class, has highest overfitting risk, and needs more patients/external validation. |

The implementation is [07_hybrid_fusion.py](../src/pipeline/07_hybrid_fusion.py).
It cross-fits average, weighted, late-fusion, and stacking candidates using
`GroupKFold` on patient IDs, then chooses from their OOF validation metrics.
It fits a Platt map only on a separate patient-disjoint calibration holdout.

## Required split protocol

```
Train patients ── GroupKFold ──> OOF tree + temporal probabilities ──> fusion selection
                                                     |
Validation calibration patients ────────────────────> Platt calibration
                                                     |
Frozen test patients ───────────────────────────────> one final evaluation
```

Base models must use the identical prediction anchors and horizon before their
probabilities are fused. The temporal window ends at the same timestamp as the
tabular feature row. All scalers, imputers, class weights, early stopping, and
feature encoders are fit inside the corresponding training fold.

## Serving response

Every prediction returns a JSON-compatible record:

```json
{
  "risk_probability": 0.18,
  "prediction_timestamp": "2100-01-01T12:00:00Z",
  "prediction_horizon_hours": 6,
  "fusion_strategy": "weighted_ensemble",
  "confidence": 0.32,
  "uncertainty": {
    "base_model_disagreement": 0.07,
    "probability_ambiguity": 0.68
  },
  "contributing_factors": []
}
```

`confidence` is a probability-ambiguity indicator, not clinical certainty.
`base_model_disagreement` exposes ensemble instability. Contributing factors
must be generated at the same prediction anchor: tree SHAP/feature-gain
factors plus temporal attribution factors (for example integrated gradients).
They are explanations, not causal claims.

## Evidence-aware comparison

The project currently has measured validation results for Logistic Regression,
XGBoost, and LightGBM in `model/model_selection_decision.json`; temporal
results are in `model/temporal_model_comparison.csv`. Those runs have different
validation role structures, so they are not a valid head-to-head hybrid claim.
SIRS, MEWS, and NEWS2 have no measured fallback-cohort performance because
required inputs are absent (WBC; SBP/GCS; and oxygen status respectively).
The comparison protocol deliberately records these as **not measured**, rather
than rank them. NEWS2 is now implemented with partial-validity reporting in
`clinical_scores.py` for when the required variables are available.

Produce a final comparative table only after a common patient split emits OOF
base predictions and valid clinical-score coverage. Include AUROC, AUPRC,
Brier score, sensitivity, specificity, PPV, NPV, alert rate, false-alert rate,
coverage, calibration method, compute cost, and explanation availability.
