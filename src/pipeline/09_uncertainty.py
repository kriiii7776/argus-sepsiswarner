"""Leakage-safe predictive uncertainty for SepsisGuard AI.

Uncertainty is about the reliability of a model probability under the observed
data. It is not evidence about whether a patient clinically has sepsis.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, precision_score, recall_score

EPS = 1e-6

def _as_2d(predictions):
    p = np.asarray(predictions, dtype=float)
    if p.ndim == 1: p = p[:, None]
    if p.ndim != 2: raise ValueError('Expected [samples, draws/models] probabilities.')
    return np.clip(p, EPS, 1 - EPS)

class SplitConformalProbabilityInterval:
    """Distribution-free, calibration-split residual interval for a probability.

    Given calibration pairs (p, y), q is the finite-sample quantile of |y-p|.
    The interval [p-q, p+q] has marginal outcome coverage at least 1-alpha
    under exchangeability. It is an outcome-compatible interval, not a
    confidence interval for the unknown true probability.
    """
    def __init__(self, alpha=.10): self.alpha = alpha
    def fit(self, probabilities, labels):
        p, y = np.asarray(probabilities, float), np.asarray(labels, int)
        if len(p) != len(y) or len(p) == 0: raise ValueError('Need non-empty aligned calibration pairs.')
        residuals = np.abs(y - p)
        rank = int(np.ceil((len(residuals) + 1) * (1 - self.alpha)))
        self.q_ = float(np.partition(residuals, min(rank, len(residuals)) - 1)[min(rank, len(residuals)) - 1])
        self.n_calibration_ = len(y)
        return self
    def predict(self, probabilities):
        p = np.asarray(probabilities, float)
        return np.c_[np.clip(p-self.q_, 0, 1), np.clip(p+self.q_, 0, 1)]

def mc_dropout_probabilities(model, inputs, draws=30, device=None, predict_logits=None):
    """Temporal-only epistemic uncertainty from dropout samples.

    Activate dropout but leave batch-normalisation layers in evaluation mode.
    The model must have been trained with dropout. Tree models cannot use this;
    use ensemble disagreement instead. `predict_logits` receives (model, batch)
    and returns logits, which makes this independent of tensor framework APIs.
    """
    if predict_logits is None: raise ValueError('Supply a framework-specific predict_logits callable.')
    import torch
    was_training = model.training
    model.eval()
    dropout_types = (torch.nn.Dropout, torch.nn.Dropout1d, torch.nn.Dropout2d, torch.nn.Dropout3d)
    for module in model.modules():
        if isinstance(module, dropout_types): module.train()
    results = []
    with torch.no_grad():
        for _ in range(draws):
            logits = predict_logits(model, inputs)
            results.append(torch.sigmoid(logits).detach().cpu().numpy())
    model.train(was_training)
    return np.stack(results, axis=1)

def summarize_predictive_uncertainty(ensemble_probabilities, conformal=None, signal_quality='HIGH'):
    """Combine base/MC draws without modifying the calibrated mean risk."""
    draws = _as_2d(ensemble_probabilities)
    mean = draws.mean(axis=1)
    std = draws.std(axis=1, ddof=1) if draws.shape[1] > 1 else np.zeros(len(mean))
    lo_hi = conformal.predict(mean) if conformal is not None else np.c_[np.clip(mean - 1.96*std, 0, 1), np.clip(mean + 1.96*std, 0, 1)]
    width = lo_hi[:, 1] - lo_hi[:, 0]
    quality_factor = {'HIGH': 1., 'MEDIUM': .75, 'LOW': .5}.get(str(signal_quality).upper(), .5)
    # Reliability confidence combines narrow predictive spread and input quality.
    confidence_score = np.clip((1 - width) * quality_factor, 0, 1)
    label = np.where(confidence_score >= .70, 'HIGH', np.where(confidence_score >= .40, 'MEDIUM', 'LOW'))
    return pd.DataFrame({'risk_probability': mean, 'ensemble_std': std, 'interval_lower': lo_hi[:, 0],
                         'interval_upper': lo_hi[:, 1], 'uncertainty_plus_minus': width / 2,
                         'confidence_score': confidence_score, 'confidence': label})

def evaluate_alert_prioritization(y, risks, uncertainty_summary, risk_threshold=.35, uncertain_width=.40):
    """Validation-only evidence for whether uncertainty triage helps.

    Compares risk-only alerts against alerts retained as HIGH priority when the
    risk crosses threshold and the interval is no wider than `uncertain_width`.
    Review-signal alerts are not counted as dropped: their coverage is reported.
    """
    y, risk = np.asarray(y, int), np.asarray(risks, float)
    width = np.asarray(uncertainty_summary['interval_upper'] - uncertainty_summary['interval_lower'])
    risk_alert = risk >= risk_threshold
    high_priority = risk_alert & (width <= uncertain_width)
    review = risk_alert & ~high_priority
    def score(mask):
        return {'n': int(mask.sum()), 'PPV': precision_score(y, mask, zero_division=0),
                'Sensitivity': recall_score(y, mask, zero_division=0),
                'AlertRate': float(mask.mean())}
    base, prioritized = score(risk_alert), score(high_priority)
    return {'risk_only': base, 'high_priority_only': prioritized,
            'review_signal_rate': float(review.mean()), 'review_signal_positive_count': int(y[review].sum()),
            'ppv_change': prioritized['PPV'] - base['PPV'],
            'sensitivity_change': prioritized['Sensitivity'] - base['Sensitivity'],
            'interpretation': 'Positive PPV change with acceptable sensitivity loss is required; do not assume benefit.'}

def evaluation_template():
    return pd.DataFrame([
        ['Ensemble variance', 'Tree + temporal base probabilities at identical prediction anchors', 'Evaluate on validation'],
        ['MC dropout', 'Temporal model with trained dropout; 30 draws', 'Evaluate on validation'],
        ['Split conformal interval', 'Patient-disjoint calibration split after calibration', 'Evaluate empirical coverage on validation/test'],
        ['Calibrated probability interval', 'Calibrated mean plus conformal residual interval', 'Evaluate width, coverage, and alert triage'],
    ], columns=['Method', 'Inputs', 'Required evidence'])
