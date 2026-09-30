"""Explainability engine for SepsisGuard AI.

Attributions explain a model's computation at a prediction anchor. They do not
identify physiological causes, establish diagnosis, or recommend treatment.
"""
from dataclasses import dataclass
import json
import os
import numpy as np
import pandas as pd

EPS = 1e-8

CLINICAL_LABELS = {
    'hr': 'heart rate', 'map': 'mean arterial pressure', 'sbp': 'systolic blood pressure',
    'rr': 'respiratory rate', 'spo2': 'oxygen saturation', 'temp': 'temperature',
    'lactate': 'lactate', 'creatinine': 'creatinine', 'wbc': 'white blood cell count',
    'platelet': 'platelet count', 'shock_index': 'shock index', 'qsofa': 'qSOFA proxy',
}

def _feature_label(feature):
    key = next((k for k in CLINICAL_LABELS if k in feature.lower()), None)
    return CLINICAL_LABELS.get(key, feature.replace('_', ' '))

def _direction(feature, value, contribution):
    if contribution > 0: return 'increased model-estimated risk'
    if contribution < 0: return 'decreased model-estimated risk'
    return 'had no material model contribution'

def _magnitude(value, values):
    a = abs(value)
    q75 = np.quantile(np.abs(values), .75) if len(values) else 0
    q25 = np.quantile(np.abs(values), .25) if len(values) else 0
    return 'large' if a >= q75 and a > 0 else 'moderate' if a >= q25 and a > 0 else 'small'

@dataclass
class LocalExplanation:
    base_value: float
    prediction_value: float
    contributions: pd.DataFrame

class TreeShapExplainer:
    """Exact TreeSHAP via supported native XGBoost/LightGBM contribution APIs.

    These APIs return per-feature additive contributions plus a bias term. This
    avoids silently falling back when the external `shap` package is unavailable.
    """
    def __init__(self, model, feature_names, kind):
        self.model, self.feature_names, self.kind = model, list(feature_names), kind.lower()
        if self.kind not in {'xgboost', 'lightgbm'}: raise ValueError('kind must be xgboost or lightgbm')

    def contributions(self, x):
        x = np.asarray(x)
        if x.ndim == 1: x = x[None, :]
        if self.kind == 'xgboost':
            import xgboost as xgb
            booster = self.model.get_booster() if hasattr(self.model, 'get_booster') else self.model
            raw = booster.predict(xgb.DMatrix(x, feature_names=self.feature_names), pred_contribs=True)
        else:
            booster = self.model.booster_ if hasattr(self.model, 'booster_') else self.model
            raw = booster.predict(x, pred_contrib=True)
        if raw.shape[1] != len(self.feature_names) + 1:
            raise RuntimeError('Unexpected native TreeSHAP contribution shape.')
        return raw[:, :-1], raw[:, -1]

    def global_importance(self, x):
        contrib, _ = self.contributions(x)
        result = pd.DataFrame({'feature': self.feature_names, 'mean_abs_shap': np.abs(contrib).mean(axis=0),
                               'mean_shap': contrib.mean(axis=0)})
        return result.sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)

    def local(self, x, risk_probability=None):
        c, base = self.contributions(x)
        row = c[0]
        table = pd.DataFrame({'feature': self.feature_names, 'shap_value_log_odds': row,
                              'direction': [_direction(f, None, v) for f, v in zip(self.feature_names, row)]})
        table['abs_shap'] = table.shap_value_log_odds.abs()
        table['magnitude'] = [_magnitude(v, row) for v in row]
        return LocalExplanation(float(base[0]), float(risk_probability) if risk_probability is not None else np.nan,
                                table.sort_values('abs_shap', ascending=False).reset_index(drop=True))

def temporal_integrated_gradients(model, sequence, baseline, steps=32, target_logit=True, device=None):
    """Time-dependent attribution for differentiable GRU/LSTM/TCN models.

    `baseline` must be a clinically declared reference (e.g. causal imputed
    neutral sequence), not a future patient state. Returns [time, feature]
    signed integrated-gradient values. This is an attribution, not causal effect.
    """
    import torch
    dev = device or next(model.parameters()).device
    x = torch.as_tensor(sequence, dtype=torch.float32, device=dev)
    ref = torch.as_tensor(baseline, dtype=torch.float32, device=dev)
    if x.ndim == 2: x, ref = x.unsqueeze(0), ref.unsqueeze(0)
    total = torch.zeros_like(x)
    was_training = model.training; model.eval()
    for alpha in torch.linspace(0, 1, steps, device=dev):
        z = (ref + alpha * (x-ref)).detach().requires_grad_(True)
        output = model(z)
        scalar = output.sum() if target_logit else torch.logit(torch.sigmoid(output).clamp(EPS, 1-EPS)).sum()
        scalar.backward(); total += z.grad
    model.train(was_training)
    return ((x-ref) * total / steps).detach().cpu().numpy()[0]

def temporal_summary(attribution, feature_names, timestamps=None, top_k=8):
    """Convert signed [time, feature] attribution to a ranked time-dependent table."""
    a = np.asarray(attribution)
    rows = []
    for t in range(a.shape[0]):
        for j, name in enumerate(feature_names):
            rows.append({'time_index': t, 'timestamp': timestamps[t] if timestamps is not None else t,
                         'feature': name, 'attribution': a[t, j], 'abs_attribution': abs(a[t, j]),
                         'direction': _direction(name, None, a[t, j])})
    result = pd.DataFrame(rows).sort_values('abs_attribution', ascending=False).head(top_k).reset_index(drop=True)
    result['magnitude'] = [_magnitude(v, a.ravel()) for v in result.attribution]
    return result

class ClinicalExplanationRenderer:
    """Plain-language, non-causal rendering of signed model contributions."""
    disclaimer = ('These factors contributed to this model prediction. They do not establish that they caused '
                  'patient deterioration, sepsis, or a need for a particular treatment.')
    def render(self, local_table, risk_probability, top_k=4):
        top = local_table.head(top_k)
        increased = top[top.shap_value_log_odds > 0]
        decreased = top[top.shap_value_log_odds < 0]
        lines = []
        if len(increased):
            lines.append('Risk increased in the model primarily because:')
            for _, r in increased.iterrows():
                lines.append(f"- {_feature_label(r.feature).capitalize()} contributed a {r.magnitude} increase to the model score.")
        if len(decreased):
            lines.append('Factors that reduced the model score:')
            for _, r in decreased.iterrows():
                lines.append(f"- {_feature_label(r.feature).capitalize()} contributed a {r.magnitude} decrease to the model score.")
        if not lines: lines.append('No material feature contribution was identified for this model prediction.')
        return {'risk_probability': float(risk_probability), 'plain_language': '\n'.join(lines),
                'disclaimer': self.disclaimer, 'top_contributions': top.to_dict(orient='records')}

def model_recourse_counterfactual(model_predict, current_row, feature_bounds, target_probability=.35,
                                  mutable_features=(), reference_rows=None, max_changes=3):
    """Conservative model-recourse search—not a clinical treatment recommendation.

    For each allowed feature, test observed reference values inside declared
    physiological/operational bounds. Report only a feasible model-input change
    that crosses the target. It neither asserts the change is achievable nor
    predicts a patient's causal response. Never use post-anchor values from the
    same patient as reference candidates.
    """
    x = pd.Series(current_row, dtype=float).copy()
    original = float(np.asarray(model_predict(pd.DataFrame([x])))[0])
    if original < target_probability: return {'status': 'already_below_target', 'original_probability': original}
    refs = pd.DataFrame(reference_rows) if reference_rows is not None else pd.DataFrame([x])
    candidates = []
    for feature in mutable_features:
        if feature not in x or feature not in feature_bounds or feature not in refs: continue
        low, high = feature_bounds[feature]
        values = np.unique(refs[feature].dropna().clip(low, high).to_numpy())
        for value in values:
            if value == x[feature]: continue
            trial = x.copy(); trial[feature] = value
            p = float(np.asarray(model_predict(pd.DataFrame([trial])))[0])
            if p < target_probability:
                candidates.append({'feature': feature, 'current_value': float(x[feature]), 'model_input_value': float(value),
                                   'probability': p, 'absolute_change': abs(float(value-x[feature]))})
    if not candidates: return {'status': 'no_single_feature_recourse_found', 'original_probability': original,
                               'warning': 'Not evidence that no clinical action could reduce risk.'}
    best = sorted(candidates, key=lambda z: (z['absolute_change'], z['probability']))[0]
    return {'status': 'model_recourse_candidate', 'original_probability': original, 'target_probability': target_probability,
            'candidate': best, 'warning': 'Model-input sensitivity only; not a causal, treatment, or clinical recommendation.'}
