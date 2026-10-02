# ARGUS Part 2 Phase 4A SHAP Explainability Report

## 1. Objective
The objective of Phase 4A is to integrate genuine SHAP (SHapley Additive exPlanations) model attributions into the ARGUS Part 2 backend for the selected primary model (`logistic-regression-v1`). This replaces pseudo-explanation heuristics (which sorted three raw vital signs) with true, mathematically rigorous additive feature contributions.

## 2. Previous Explainability Problem
Prior to Phase 4A, the runtime inference pipeline generated contributing factors by executing a pseudo-explanation snippet:
```python
factors = [
    f'{name.replace("_curr", "").upper()} contributed to the model prediction'
    for name in sorted(['map_curr', 'hr_curr', 'rr_curr'], key=lambda k: abs(row.get(k, 0)), reverse=True)
]
```
This hardcoded three vital signs (`MAP`, `HR`, `RR`) and sorted them by raw numerical magnitude, misrepresenting raw physiological measurements as model feature attributions.

## 3. SHAP Implementation
`shap.LinearExplainer` was integrated into `src/backend/services/inference_runtime.py`. Upon loading `lr_model.pkl` and `scaler.pkl`, the runtime initializes a `shap.LinearExplainer` with a zero background vector in standardized feature space ($\mathbf{0}_{1 \times 31}$), representing the population mean baseline under `StandardScaler`.

## 4. Why LinearExplainer Was Used
`shap.LinearExplainer` was selected because:
1. **Model Architecture Alignment**: The primary model selected by empirical project evidence is `LogisticRegression` (`lr_model.pkl`), a linear classification model. `TreeExplainer` is strictly for decision tree models and is incompatible with Logistic Regression.
2. **Exact Additive Properties**: For linear models, `LinearExplainer` produces exact additive Shapley values in log-odds space:
   $$\text{log-odds}(x) = \text{base\_value} + \sum_{i=1}^{31} \phi_i$$
   where $\phi_i = w_i \cdot x_{\text{scaled}, i}$.

## 5. Model Input Space
The Logistic Regression model expects a 31-dimensional standardized vector:
$$x_{\text{scaled}} = \text{scaler.transform}(x_{\text{raw}})$$
SHAP attributions explain the exact 31-feature standardized vector fed directly into the model's decision function.

## 6. 31-Feature Alignment
All 31 features defined in `FEATURES` (`hr_curr`, `map_curr`, `rr_curr`, `spo2_curr`, `temp_curr`, `hr_mean_4h`, ..., `icu_hour`) are mapped 1-to-1 to their SHAP values:
- Number of features: Exactly 31.
- Ordering: Preserved in identical sequence as `FEATURES`.
- Missing values: Imputed safely via `np.nan_to_num(x[None, :], nan=0.0)`.

## 7. SHAP Output Structure
The runtime returns a structured `shap_explanation` dictionary containing:
```json
{
  "explanation_available": true,
  "output_space": "log-odds",
  "base_value_log_odds": -9.171826,
  "explained_output_log_odds": 61.238061,
  "feature_attributions": [
    {
      "feature_name": "temp_mean_4h",
      "feature_value": 39.1,
      "shap_value": 61.049236,
      "contribution_direction": "positive",
      "absolute_contribution": 61.049236,
      "model_version": "logistic-regression-v1"
    }
  ],
  "top_contributions": [...],
  "model_version": "logistic-regression-v1"
}
```
Top contributions are deterministically ranked by `absolute_contribution` descending and formatted into non-causal descriptions in `contributing_factors`.

## 8. Prediction/Explanation Consistency
SHAP additivity is verified at runtime for every inference call:
$$\text{base\_value\_log\_odds} + \sum_{i=1}^{31} \phi_i = \text{model.decision\_function}(x_{\text{scaled}})$$
If the absolute difference exceeds $10^{-3}$, additivity verification fails and the explanation is marked unavailable.

## 9. Error Handling
If SHAP fails to compute or if the system operates under demo fallback mode (`is_demo_model: true`):
- `explanation_available`: `false`
- `reason`: `"SHAP explanation unavailable for fallback/demo model"`
- `feature_attributions`: `[]`
- `contributing_factors`: `["SHAP explanation unavailable for fallback model"]`
No fake SHAP values or pseudo-explanation heuristics are generated.

## 10. Tests Added
15 unit tests were added in `tests/unit/test_shap_explainability.py`:
1. `test_1_shap_explainer_initialization`: Verifies `LinearExplainer` initialization.
2. `test_2_logistic_regression_compatibility`: Confirms scikit-learn model compatibility.
3. `test_3_exact_31_feature_alignment`: Validates 31 feature attributions generated.
4. `test_4_exact_feature_name_alignment`: Verifies feature names match `FEATURES`.
5. `test_5_shap_output_exists_for_valid_prediction`: Checks output structure & log-odds space.
6. `test_6_number_of_shap_values_equals_31`: Asserts exactly 31 SHAP values.
7. `test_7_shap_values_are_numeric_and_finite`: Verifies all SHAP values are finite floats.
8. `test_8_positive_negative_contribution_direction_correct`: Tests positive/negative direction labels.
9. `test_9_absolute_contribution_calculated_correctly`: Validates `absolute_contribution` calculation.
10. `test_10_top_contribution_ranking_is_deterministic`: Verifies descending ranking by absolute contribution.
11. `test_11_model_version_is_logistic_regression_v1`: Confirms model version tracking.
12. `test_12_explanation_generated_from_actual_model`: Validates exact log-odds additivity.
13. `test_13_no_hardcoded_explanation_values_used`: Verifies dynamic attributions change with patient vitals.
14. `test_14_shap_failure_does_not_produce_fake_values`: Asserts graceful unavailable state on failure.
15. `test_15_end_to_end_inference_produces_prediction_plus_shap`: Tests full prediction + SHAP pipeline.

## 11. Full Test Result
Ran `python -m pytest tests/`:
- **51 passed / 0 failed** (100% pass rate across unit, model, safety, integration, and system tests).

## 12. Live Verification
- `model_version`: `logistic-regression-v1`
- `is_demo_model`: `false`
- `risk_probability`: `0.9999` (calibrated probability)
- `shap_explanation.explanation_available`: `true`
- `shap_explanation.output_space`: `"log-odds"`
- `contributing_factors`: Top 5 feature attributions ranked by absolute SHAP contribution.

## 13. Files Changed
- `src/backend/services/inference_runtime.py`: Added `LinearExplainer` initialization, `compute_shap_explanation()` method, and removed pseudo-explanation sorting.
- `src/backend/services/inference_service.py`: Updated `explain_prediction()` to extract real SHAP attributions.
- `src/backend/schemas/schemas.py`: Added `shap_explanation: dict | None = None` to `PredictionResponse`.
- `tests/unit/test_shap_explainability.py`: Created 15 new unit tests.

## 14. Files Intentionally Untouched
- `deployment/backend/`: Untouched (legacy backend preserved).
- `src/frontend/`: Untouched.
- `model/`: Model artifacts (`lr_model.pkl`, `scaler.pkl`, `lr_calibrator.pkl`) untouched.

## 15. Remaining Limitations
- SHAP attributions explain model feature contributions in log-odds space; they do not identify physiological causation or clinical diagnosis.
- ARGUS remains a prototype clinical decision-support system and requires formal clinical validation prior to real-world deployment.
