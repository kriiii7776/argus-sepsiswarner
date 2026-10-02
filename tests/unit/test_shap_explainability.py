import pytest
from datetime import datetime, timezone
import numpy as np
import shap
from src.backend.services.inference_runtime import Runtime, FEATURES
from src.backend.schemas.schemas import VitalEvent

def create_sample_event(patient_id: str = "P-SHAP-TEST", hr: float = 115.0, map_val: float = 62.0):
    return VitalEvent(
        patient_id=patient_id,
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        heart_rate=hr,
        map=map_val,
        resp_rate=24.0,
        spo2=94.0,
        temperature_c=39.1,
        source='simulator'
    )

def test_1_shap_explainer_initialization():
    rt = Runtime()
    assert rt.explainer is not None, "SHAP LinearExplainer failed to initialize."
    assert isinstance(rt.explainer, shap.LinearExplainer), f"Unexpected explainer type: {type(rt.explainer)}"

def test_2_logistic_regression_compatibility():
    rt = Runtime()
    assert hasattr(rt.model, 'coef_'), "Primary model is missing coef_ attribute."
    assert hasattr(rt.model, 'intercept_'), "Primary model is missing intercept_ attribute."
    assert rt.model_version_name == 'logistic-regression-v1'

def test_3_exact_31_feature_alignment():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    shap_exp = res['shap_explanation']
    assert shap_exp['explanation_available'] is True
    assert len(shap_exp['feature_attributions']) == 31, f"Attribution count {len(shap_exp['feature_attributions'])} != 31"

def test_4_exact_feature_name_alignment():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    attributions = res['shap_explanation']['feature_attributions']
    names_in_exp = {attr['feature_name'] for attr in attributions}
    assert names_in_exp == set(FEATURES), "Feature names in SHAP explanation do not match FEATURES list."

def test_5_shap_output_exists_for_valid_prediction():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    assert 'shap_explanation' in res
    assert res['shap_explanation']['explanation_available'] is True
    assert res['shap_explanation']['output_space'] == 'log-odds'

def test_6_number_of_shap_values_equals_31():
    rt = Runtime()
    event = create_sample_event("P-TEST-6")
    res = rt.predict(event)
    shap_exp = res['shap_explanation']
    assert len(shap_exp['feature_attributions']) == 31

def test_7_shap_values_are_numeric_and_finite():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    attributions = res['shap_explanation']['feature_attributions']
    for attr in attributions:
        assert isinstance(attr['shap_value'], float)
        assert np.isfinite(attr['shap_value'])
        assert isinstance(attr['feature_value'], float)
        assert np.isfinite(attr['feature_value'])

def test_8_positive_negative_contribution_direction_correct():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    attributions = res['shap_explanation']['feature_attributions']
    for attr in attributions:
        s_val = attr['shap_value']
        direction = attr['contribution_direction']
        if s_val > 0:
            assert direction == 'positive'
        elif s_val < 0:
            assert direction == 'negative'
        else:
            assert direction == 'neutral'

def test_9_absolute_contribution_calculated_correctly():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    attributions = res['shap_explanation']['feature_attributions']
    for attr in attributions:
        expected_abs = round(abs(attr['shap_value']), 6)
        assert pytest.approx(attr['absolute_contribution'], abs=1e-5) == expected_abs

def test_10_top_contribution_ranking_is_deterministic():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    attributions = res['shap_explanation']['feature_attributions']
    abs_vals = [a['absolute_contribution'] for a in attributions]
    assert abs_vals == sorted(abs_vals, reverse=True), "Attributions are not sorted by absolute contribution descending."

def test_11_model_version_is_logistic_regression_v1():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    assert res['model_version'] == 'logistic-regression-v1'
    assert res['shap_explanation']['model_version'] == 'logistic-regression-v1'

def test_12_explanation_generated_from_actual_model():
    rt = Runtime()
    event = create_sample_event()
    res = rt.predict(event)
    shap_exp = res['shap_explanation']
    base_val = shap_exp['base_value_log_odds']
    explained_output = shap_exp['explained_output_log_odds']
    sum_shap = sum(a['shap_value'] for a in shap_exp['feature_attributions'])
    assert pytest.approx(base_val + sum_shap, abs=1e-3) == explained_output

def test_13_no_hardcoded_explanation_values_used():
    rt = Runtime()
    event_normal = create_sample_event("P-NORM", hr=72.0, map_val=85.0)
    event_crisis = create_sample_event("P-CRIS", hr=145.0, map_val=45.0)
    res_normal = rt.predict(event_normal)
    res_crisis = rt.predict(event_crisis)
    
    attr_normal = {a['feature_name']: a['shap_value'] for a in res_normal['shap_explanation']['feature_attributions']}
    attr_crisis = {a['feature_name']: a['shap_value'] for a in res_crisis['shap_explanation']['feature_attributions']}
    
    # SHAP attributions for hr_curr and map_curr must dynamically differ between normal and crisis vitals
    assert attr_normal['hr_curr'] != attr_crisis['hr_curr']
    assert attr_normal['map_curr'] != attr_crisis['map_curr']

def test_14_shap_failure_does_not_produce_fake_values():
    rt = Runtime()
    rt.explainer = None  # Simulate SHAP failure
    event = create_sample_event("P-FAIL")
    res = rt.predict(event)
    
    shap_exp = res['shap_explanation']
    assert shap_exp['explanation_available'] is False
    assert shap_exp['reason'].startswith('SHAP explanation unavailable')
    assert shap_exp['feature_attributions'] == []
    assert res['contributing_factors'] == ["SHAP explanation unavailable for fallback model"]

def test_15_end_to_end_inference_produces_prediction_plus_shap():
    rt = Runtime()
    event = create_sample_event("P-E2E-SHAP")
    res = rt.predict(event)
    assert res['patient_id'] == "P-E2E-SHAP"
    assert res['is_demo_model'] is False
    assert res['model_version'] == 'logistic-regression-v1'
    assert 0.0 <= res['risk_probability'] <= 1.0
    assert res['shap_explanation']['explanation_available'] is True
    assert len(res['shap_explanation']['top_contributions']) == 5
    assert len(res['contributing_factors']) == 5
