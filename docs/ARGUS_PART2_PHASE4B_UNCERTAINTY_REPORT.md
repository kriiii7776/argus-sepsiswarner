# ARGUS Part 2 Phase 4B Uncertainty & Confidence Repair Report

## 1. Objective
The objective of Phase 4B is to audit, repair, and validate the uncertainty and confidence estimation layer in the ARGUS Part 2 backend. This phase eliminates the pseudo-uncertainty heuristic (`risk ± 0.20`), establishes a mathematically defensible uncertainty contract, and ensures that model predictions are not accompanied by false statistical coverage claims.

## 2. Previous Uncertainty Problem
Prior to Phase 4B, runtime inference in `src/backend/services/inference_runtime.py` calculated predictive uncertainty using an arbitrary fixed range:
```python
interval = (max(0., p - .20), min(1., p + .20))
conf = 'HIGH' if sq == 'HIGH' and .4 >= interval[1] - interval[0] else 'MEDIUM' if sq != 'LOW' else 'LOW'
```
This hardcoded a fixed 40% interval width ($p \pm 0.20$) for every prediction, misrepresenting an uncalibrated constant spread as statistical predictive uncertainty.

## 3. Existing Implementation Audit
Audit of the repository (`src/pipeline/09_uncertainty.py`, `docs/15_uncertainty_estimation.md`, `model/` directory) revealed:
1. **Conformal Class Definition**: `src/pipeline/09_uncertainty.py` defines `SplitConformalProbabilityInterval`, but it was never fitted, instantiated, or saved during training.
2. **Missing Calibration Artifacts**: No fitted conformal quantile artifact ($q_$) or calibration patient residual dataset exists in `model/` or anywhere in the workspace.
3. **Explicit Project Documentation**: `docs/15_uncertainty_estimation.md` (line 38) explicitly documents:
   > "This has not yet been measured because shared-split hybrid base predictions and a separate calibration/validation role are unavailable. No benefit claim should be made until that artifact exists."
4. **Existing Platt Calibrator**: `lr_calibrator.pkl` performs Platt probability calibration $P(Y=1 \mid \text{score})$ to output calibrated probability $p$, but does not estimate conformal quantiles or interval bounds.

## 4. Selected Uncertainty Method
Conformal prediction was NOT implemented because the available project evidence/data was insufficient to establish valid coverage. The heuristic $p \pm 0.20$ was completely removed, and statistical predictive uncertainty is explicitly reported as `UNAVAILABLE`. Reliability confidence is mapped directly to input signal quality (`sq`).

## 5. Mathematical Definition
Because no empirical conformal quantile $q_{1-\alpha}$ exists in project artifacts, no interval $[p - q, p + q]$ can be mathematically justified. Returning an arbitrary interval would violate statistical validity. Therefore:
$$\text{uncertainty\_available} = \text{false}$$
$$\text{method} = \text{"UNAVAILABLE"}$$

## 6. Data/Calibration Source
No conformal calibration dataset or quantile artifact exists in the repository.

## 7. Relationship with Calibrated Probability
The calibrated risk probability $p$ produced by `lr_model.pkl` + `scaler.pkl` + `lr_calibrator.pkl` is preserved completely unchanged. Uncertainty logic is strictly decoupled from risk prediction and does not alter $p$.

## 8. API/Output Structure
The runtime returns an explicit `uncertainty_summary` contract:
```json
{
  "uncertainty_available": false,
  "method": "UNAVAILABLE",
  "reason": "Conformal prediction calibration artifact unavailable in repository",
  "coverage_level": null,
  "interval_lower": null,
  "interval_upper": null,
  "model_version": "logistic-regression-v1"
}
```
`uncertainty_interval` is set to `null` instead of the fake $p \pm 0.20$ range.

## 9. Error/Fallback Behavior
When operating under fallback mode (`is_demo_model: true`) or when conformal data is missing:
- `uncertainty_available`: `false`
- `method`: `"UNAVAILABLE"`
- `reason`: `"Conformal prediction calibration artifact unavailable in repository"`

## 10. Tests Added
12 unit tests were created in `tests/unit/test_uncertainty.py`:
1. `test_1_real_model_loading`: Confirms real ML model loads cleanly.
2. `test_2_model_version_remains_logistic_regression_v1`: Asserts model version integrity.
3. `test_3_calibrated_risk_probability_unchanged`: Verifies calibrated risk probability $p$ remains in $[0, 1]$.
4. `test_4_uncertainty_output_is_deterministic`: Ensures deterministic output.
5. `test_5_uncertainty_method_correctly_reported`: Asserts method is reported as `UNAVAILABLE`.
6. `test_6_no_arbitrary_20_percent_heuristic_remains`: Verifies removal of $p \pm 0.20$ bounds.
7. `test_7_no_fake_confidence_values_produced`: Asserts explicit unavailable reason.
8. `test_8_missing_conformal_data_handled_safely`: Ensures safe runtime execution without crashing.
9. `test_9_demo_fallback_model_uncertainty_handling`: Tests fallback mode uncertainty contract.
10. `test_10_end_to_end_inference_returns_risk_and_uncertainty_separately`: Validates separation of risk and uncertainty payload fields.
11. `test_11_existing_shap_explanation_remains_unaffected`: Asserts SHAP attributions are 100% unaffected.
12. `test_12_alert_engine_receives_signal_quality_confidence`: Verifies `SmartAlertEngine` integration.

## 11. Full Test Results
Ran `python -m pytest tests/`:
- **63 passed / 0 failed** (100% pass rate across unit, model, safety, integration, and system test suites).

## 12. Live Verification
- `model_version`: `logistic-regression-v1`
- `is_demo_model`: `false`
- `risk_probability`: Calibrated risk probability preserved.
- `uncertainty_interval`: `null` (heuristic $p \pm 0.20$ removed).
- `uncertainty_summary.uncertainty_available`: `false`
- `uncertainty_summary.method`: `"UNAVAILABLE"`
- `shap_explanation.explanation_available`: `true` (31 real SHAP attributions active).

## 13. Files Changed
- `src/backend/services/inference_runtime.py`: Removed $p \pm 0.20$ heuristic, added `uncertainty_summary`.
- `src/backend/schemas/schemas.py`: Updated `PredictionResponse` schema to support `uncertainty_interval: None` and `uncertainty_summary: dict | None`.
- `tests/unit/test_uncertainty.py`: Created 12 new unit tests.
- `docs/ARGUS_PART2_PHASE4B_UNCERTAINTY_REPORT.md`: Created Phase 4B report.

## 14. Files Untouched
- `deployment/backend/`: Untouched.
- `src/frontend/`: Untouched.
- `model/`: Untouched.
- `src/pipeline/11_smart_alert_engine.py`: Untouched.

## 15. Known Limitations
- Conformal prediction was not implemented because the available project evidence/data was insufficient to establish valid coverage.
- ARGUS remains a prototype clinical decision-support system and requires formal clinical validation prior to real-world deployment.
