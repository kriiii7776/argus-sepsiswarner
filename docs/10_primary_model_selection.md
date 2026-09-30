# SepsisGuard AI: Primary ML Model — Training & Comparison Strategy

## 1. Objective

Select the primary tabular machine-learning model for real-time sepsis early warning from a rigorous, evidence-based comparison of three candidate classifiers. All model selection decisions are made exclusively from **validation-set** evidence; the test set is touched **exactly once** at the end for final reporting.

---

## 2. Candidate Models

| # | Model | Class-Imbalance Strategy | Hyperparameter Tuning |
|---|-------|--------------------------|----------------------|
| 1 | **Logistic Regression (L2)** | `class_weight='balanced'` | `RandomizedSearchCV` over C (log-uniform) |
| 2 | **XGBoost** | `scale_pos_weight` (TRAIN-only Audit 5) | `RandomizedSearchCV` n_iter=30 |
| 3 | **LightGBM** | `class_weight='balanced'` | `RandomizedSearchCV` n_iter=30 |

---

## 3. Data Partitioning

Per `doc/09_train_val_test_strategy.md` §2:

```
TRAIN (70%)  →  Fit all model weights, scaler, class weights
VAL   (15%)  →  Early stopping, calibration, threshold selection
TEST  (15%)  →  Final reporting only (one-shot)
```

**Splitting method:** `GroupShuffleSplit` on `subject_id` (patient-level).  
**Leakage audit** (§5 Audits 1–5) passes programmatically before training begins.

---

## 4. Leakage Prevention Implementation

| Audit | Check | Implementation |
|-------|-------|----------------|
| 1 | Zero patient overlap across partitions | `assert len(train_pts & test_pts) == 0` |
| 2 | No leaky features | Feature name filter (no `culture`, `antibiotic`, `abx`, `vaso`) |
| 3 | No future peeking | Temporal labeling strategy (Phase 3 doc) |
| 4 | Scaler isolation | `assert scaler.n_samples_seen_ == len(X_train)` |
| 5 | Class weight from TRAIN only | `spw = n_neg_train / n_pos_train` before split |

---

## 5. Hyperparameter Tuning Protocol

All tuning is conducted **entirely on TRAIN** using `GroupKFold(5)`.

### Logistic Regression
- **Search space:** `C ∈ logspace(-3, 2, 30)`
- **n_iter:** 15

### XGBoost
```yaml
max_depth:        [3, 4, 5, 6]
learning_rate:    [0.01, 0.05, 0.1, 0.2]
subsample:        [0.6, 0.75, 0.9, 1.0]
colsample_bytree: [0.5, 0.7, 0.9, 1.0]
min_child_weight: [1, 3, 5, 10]
gamma:            [0, 0.1, 0.3, 0.5]
reg_alpha:        [0, 0.1, 1.0]
reg_lambda:       [1, 1.5, 2.0]
n_iter: 30
```

### LightGBM
```yaml
num_leaves:        [15, 31, 63, 127]
max_depth:         [-1, 5, 8, 12]
learning_rate:     [0.01, 0.05, 0.1, 0.2]
subsample:         [0.6, 0.75, 0.9, 1.0]
colsample_bytree:  [0.5, 0.7, 0.9, 1.0]
min_child_samples: [5, 10, 20, 50]
reg_alpha:         [0, 0.1, 1.0]
reg_lambda:        [0, 0.1, 1.0]
n_iter: 30
```

After best hyperparameters are found, both XGBoost and LightGBM are **refit with n_estimators=500** and **early stopping (30 rounds)** evaluated on the VAL set.

---

## 6. Probability Calibration

**Method:** Platt/Sigmoid scaling (custom `SigmoidCalibrator`).  
**Fitted on:** VAL holdout only (never test).  
**Rationale:** Tree ensembles often produce over-confident probabilities. Calibrated probabilities are essential for clinical threshold setting and Brier score evaluation.

---

## 7. Evaluation Metrics

All metrics computed identically to the clinical baseline evaluation:

| Metric | Why |
|--------|-----|
| **AUROC** | Threshold-free ranking quality |
| **AUPRC** | Most informative for imbalanced detection (≈ 20% prevalence) |
| **Brier Score** | Probabilistic calibration loss |
| **Sensitivity** | Clinical cost of missed sepsis is very high |
| **Specificity** | Alert fatigue reduction |
| **PPV / NPV** | Positive/negative predictive value at operating threshold |
| **Alert Rate** | Operational burden on nursing staff |
| **False Alert %** | Proportion of non-sepsis windows that trigger an alert |

**Operating threshold:** 0.35 (chosen for clinical sensitivity; adjustable post-deployment).

---

## 8. Feature Engineering Integration

All 28 temporal features from `doc/07_feature_engineering_framework.md` are used:
- **Current values:** `hr_curr`, `map_curr`, `rr_curr`, `spo2_curr`, `temp_curr`
- **Rolling 4-h stats:** mean, std, min, max per vital
- **Trend features:** 1-h/4-h deltas, 4-h slopes
- **Acceleration:** 2nd derivative of HR
- **Cross-parameter interactions:** Shock Index, Respiratory Distress Index, Fever Response Index
- **Missingness:** `lactate_missing`, `time_since_lactate`
- **Clinical score proxy:** `qsofa_curr`
- **Cumulative hypoperfusion:** `map_time_low_4h`

---

## 9. Primary Model Selection Criteria

Evidence-based composite rank from **validation-set metrics**. The choice is
frozen before the test set is evaluated; test metrics are final reporting only.

| Priority | Criterion | Rationale |
|----------|-----------|-----------|
| 1 | **AUPRC ↑** | More informative than AUROC for 80/20 imbalanced tasks |
| 2 | **Brier Score ↓** | Probabilistic quality; required for calibrated alerts |
| 3 | **Sensitivity ↑** | A missed sepsis diagnosis has far higher clinical cost than a false alert |
| 4 | **Alert Rate ↓** | Excess alerts degrade trust and nurse responsiveness |

Model with the **lowest composite rank** across these four criteria is designated as the primary model. If two models tie, AUPRC is the tiebreaker.

---

## 10. Artifacts Produced

| Artifact | Path | Description |
|----------|------|-------------|
| `scaler.pkl` | `model/` | StandardScaler fit on TRAIN only |
| `lr_model.pkl` | `model/` | Best LR estimator |
| `lr_calibrator.pkl` | `model/` | Sigmoid calibrator (val-fitted) |
| `xgb_model.json` | `model/` | XGBoost final model |
| `xgb_calibrator.pkl` | `model/` | XGBoost sigmoid calibrator |
| `lgb_model.txt` | `model/` | LightGBM final model |
| `lgb_calibrator.pkl` | `model/` | LightGBM sigmoid calibrator |
| `model_comparison.csv` | `model/` | Full comparison table (all metrics) |
| `model_selection_decision.json` | `model/` | Evidence record for primary model choice |
| `roc_pr_curves.png` | `model/` | ROC and PR curves for all 3 models |
| `calibration_plot.png` | `model/` | Reliability diagram (calibration) |
| `feat_imp_XGBoost.png` | `model/` | Top-20 XGBoost feature importances |
| `feat_imp_LightGBM.png` | `model/` | Top-20 LightGBM feature importances |
| `05_train_models.log` | `logs/` | Full execution log with all metrics |

---

## 11. Qualitative Comparison Dimensions

| Dimension | Logistic Regression | XGBoost | LightGBM |
|-----------|-------------------|---------|----------|
| **Performance** | Good baseline; linear boundary limits | Strong; handles nonlinear interactions | Comparable to XGBoost; faster training |
| **Computational Cost** | < 5s | 30–120s (with CV) | 20–90s (with CV) |
| **Interpretability** | High — global coefficients | Medium — SHAP per-prediction explanations | Medium — SHAP per-prediction explanations |
| **Calibration** | Good (linear output) | Moderate (needs Platt) | Moderate (needs Platt) |
| **Clinical Usefulness** | Safe regulatory baseline | High predictive power | High predictive power |
| **Alert Burden** | Higher false alert rate (linear boundary) | Lower with tuning | Lower with tuning |
| **Imbalance Handling** | `class_weight=balanced` | `scale_pos_weight` | `class_weight=balanced` |

---

*Implementation:* [`src/pipeline/05_train_models.py`](../src/pipeline/05_train_models.py)  
*Evaluation log:* `logs/05_train_models.log`  
*Decision record:* `model/model_selection_decision.json`
