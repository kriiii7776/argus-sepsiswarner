# ARGUS Part 2 Phase 3B Model and Calibration Report

## 1. Objective
The objective of Phase 3B was to audit and repair the ML model and calibration loading pipeline so that training evidence, saved model artifacts, calibration objects, and runtime execution all refer to the **SAME primary model** (`logistic-regression-v1`) with 100% feature schema compatibility and zero reliance on demo/fallback mode.

---

## 2. Previous Model Architecture
In the previous implementation ([`deployment/backend/app/service.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/deployment/backend/app/service.py#L20-L30)):
- Runtime attempted to load `xgb_model.json` and `xgb_calibrator.pkl`.
- `joblib.load('xgb_calibrator.pkl')` threw `AttributeError: Can't get attribute 'SigmoidCalibrator' on <module '__main__'>` (Issue R-01).
- The exception handler caught this failure and silently set `self.model = None` and `self.demo = True`, falling back to a deterministic heuristic logit formula while reporting status `"ok"`.

---

## 3. Model Selection Evidence Audit
A thorough audit of project evidence established that **Logistic Regression** is the officially selected primary model:

1. **Decision Record ([`model/model_selection_decision.json`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/model/model_selection_decision.json#L2)):**
   Explicitly declares `"primary_model": "Logistic Regression"`.
2. **Pipeline Execution Log ([`logs/05_train_models.log`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/logs/05_train_models.log#L40-L45)):**
   Records `Primary model selected: Logistic Regression (composite rank=6.0)` and `PRIMARY MODEL: Logistic Regression`.
3. **Comparison Table ([`model/model_comparison.csv`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/model/model_comparison.csv)):**
   Logistic Regression achieved highest validation/test AUPRC (0.963 val / 0.973 test), lowest Brier score (0.0053 val / 0.0049 test), and highest Sensitivity (0.984 val / 0.968 test).
4. **Project Documentation ([`docs/10_primary_model_selection.md`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/docs/10_primary_model_selection.md) §10, §11):**
   Documents Logistic Regression as the primary regulatory baseline model.

---

## 4. Model Consistency Audit Table

| Component | Pre-Phase 3B State | Post-Phase 3B State |
|-----------|--------------------|---------------------|
| **Documentation** | Logistic Regression | Logistic Regression |
| **Training Code** | Logistic Regression | Logistic Regression |
| **Model Selection Result** | Logistic Regression | Logistic Regression |
| **Saved Artifacts** | `lr_model.pkl`, `lr_calibrator.pkl`, `scaler.pkl` | `lr_model.pkl`, `lr_calibrator.pkl`, `scaler.pkl` |
| **Runtime Loader** | XGBoost (Attempted) | Logistic Regression (`logistic-regression-v1`) |
| **Calibration Artifact** | `xgb_calibrator.pkl` (Failed) | `lr_calibrator.pkl` (Loaded) |
| **Online Inference Status** | Heuristic Fallback (`is_demo_model: true`) | Real Calibrated ML (`is_demo_model: false`) |

---

## 5. Feature Schema Consistency
- **Feature Vector Length:** Scaler (`scaler.pkl`), Model (`lr_model.pkl`), and Runtime (`FEATURES`) all expect exactly **31 features**.
- **Preprocessing Alignment:** `StandardScaler` (`scaler.pkl`) transforms the 31-feature vector before passing it into `LogisticRegression` (`lr_model.pkl`).
- **Feature Order Alignment:** Runtime `FEATURES` list matches the exact order fit during training (`hr_curr`, `map_curr`, `rr_curr`, ..., `icu_hour`).

---

## 6. Calibration Artifact Audit & Root Cause of R-01

### Inspection Findings
- `model/lr_calibrator.pkl` and `model/xgb_calibrator.pkl` both exist and contain valid fitted Platt sigmoid parameters ($a = 10.8169, b = -8.9815$ for Logistic Regression).

### Root Cause Analysis
During training ([`src/pipeline/05_train_models.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/pipeline/05_train_models.py#L205)), `SigmoidCalibrator` was defined inside the main script (`__main__`). Pickling stored the class reference as `__main__.SigmoidCalibrator`. When unpickled in runtime scripts where `__main__` is `uvicorn` or `pytest`, Python failed to resolve `__main__.SigmoidCalibrator`, raising `AttributeError`.

---

## 7. Fix Implemented (Issue R-01 Resolution)
In [`src/backend/services/inference_runtime.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/services/inference_runtime.py#L14-L21):
1. Defined `SigmoidCalibrator` class matching fitted attributes (`a_`, `b_`).
2. Registered `SigmoidCalibrator` into `sys.modules['__main__']` prior to `joblib.load()` execution:
   ```python
   setattr(sys.modules['__main__'], 'SigmoidCalibrator', SigmoidCalibrator)
   ```
3. This minimal compatibility fix resolved R-01 without modifying or retraining any model artifacts.

---

## 8. Runtime Model Loading & Inference Pipeline

```
[VitalEvent Input]
       ↓
[Timestamp Windowing & 31-Feature Extraction]
       ↓
[StandardScaler (model/scaler.pkl)]
       ↓
[LogisticRegression (model/lr_model.pkl)]  →  Raw Probability (raw_p)
       ↓
[SigmoidCalibrator (model/lr_calibrator.pkl)]  →  Calibrated Probability (cal_p)
       ↓
[SmartAlertEngine & Risk Envelope Output]  →  is_demo_model: false
```

- **Primary Model Artifact:** `model/lr_model.pkl`
- **Scaler Artifact:** `model/scaler.pkl`
- **Calibrator Artifact:** `model/lr_calibrator.pkl`
- **Model Version Tag:** `logistic-regression-v1`
- **Demo Status:** `is_demo_model: false`

---

## 9. Fallback Behavior
If model artifacts are missing or corrupted, the runtime safely falls back to demo mode, explicitly setting:
- `is_demo_model: true`
- `model_version: 'development-fallback-v0'`

No heuristic output is ever disguised as a real ML prediction.

---

## 10. Tests Added
Created [`tests/unit/test_model_calibration.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/tests/unit/test_model_calibration.py) containing 10 unit tests:

1. `test_1_model_artifact_loading`: Verifies `lr_model.pkl` loads and `is_demo_model` is `False`.
2. `test_2_calibrator_loading`: Verifies `lr_calibrator.pkl` loads without `AttributeError`.
3. `test_3_feature_count_compatibility`: Verifies 31-feature length across scaler, model, and runtime.
4. `test_4_feature_order_compatibility`: Verifies exact feature ordering.
5. `test_5_prediction_generation`: Verifies risk probability generation between 0.0 and 1.0.
6. `test_6_calibrated_probability_generation`: Verifies Platt calibration probability output.
7. `test_7_real_model_status`: Verifies `is_demo_model` is `False` and `model_version` is `'logistic-regression-v1'`.
8. `test_8_fallback_status_when_artifact_unavailable`: Verifies safe fallback status when model is set to `None`.
9. `test_9_missing_calibrator_graceful_handling`: Verifies uncalibrated model output when calibrator is missing.
10. `test_10_pipeline_end_to_end_verification`: Verifies full end-to-end inference payload.

---

## 11. Test Results

- **Command:** `python -m pytest tests/`
- **Total Tests Collected:** 36
- **Passed:** **36**
- **Failed:** **0**
- **Pass Rate:** **100%**

```
tests\integration\test_integration.py ...                                [  8%]
tests\model\test_model.py ...                                            [ 16%]
tests\safety\test_safety.py ...                                          [ 25%]
tests\system\test_system.py ..                                           [ 30%]
tests\unit\test_model_calibration.py ..........                          [ 58%]
tests\unit\test_timestamp_windowing.py ............                      [ 91%]
tests\unit\test_unit.py ...                                              [100%]
====================== 36 passed, 200 warnings in 4.60s =======================
```

---

## 12. Runtime Verification Result
Live inference execution verified via `InferenceService.ingest()`:

```
VERIFICATION RESULT:
Patient ID: P-VERIFY-REAL
Risk Probability: 0.0001264588785705142
Confidence: HIGH
Signal Quality: HIGH
Model Version: logistic-regression-v1
Is Demo Model: False
Alert Severity: None
```

---

## 13. Remaining Model Issues
- None for tabular model selection, loading, and calibration. The primary model is fully aligned, calibrated, and operational.

---

## 14. Verification Summary

| Verification Check | Target / Rule | Result | Status |
|---|---|---|---|
| **Model Selection Alignment** | Use primary model selected by project evidence | Logistic Regression selected | **PASSED** |
| **Model Artifact Loading** | `lr_model.pkl` & `scaler.pkl` load | Loaded successfully | **PASSED** |
| **R-01 Calibrator Fix** | `lr_calibrator.pkl` loads without `AttributeError` | Loaded successfully | **PASSED** |
| **Real Model Status** | `is_demo_model: false` | Confirmed `False` | **PASSED** |
| **New Unit Tests** | 10 model calibration tests | 10 / 10 PASSED | **PASSED** |
| **Full Test Suite** | 36 total tests | 36 / 36 PASSED (100%) | **PASSED** |
| **Deployment Backend Preserved** | `deployment/backend/app/` untouched | 0 files modified | **PASSED** |
| **Frontend Preserved** | `src/frontend/` untouched | 0 files modified | **PASSED** |
| **Model Retraining** | Retraining performed | NO retraining required | **PASSED** |
