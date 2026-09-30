"""Leakage-safe late-fusion and stacking for SepsisGuard AI.

The trainer that creates the inputs to this module must emit *out-of-fold*
train predictions for each base model.  Never fit this module on predictions
made by a base model on the rows it was trained on.  Calibration and final
evaluation use separate patient-disjoint calibration and test partitions.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

EPS = 1e-6

def _clip(p): return np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
def _metric(y, p):
    return {"AUROC": roc_auc_score(y, p), "AUPRC": average_precision_score(y, p),
            "Brier": brier_score_loss(y, p), "LogLoss": log_loss(y, _clip(p))}

class Platt:
    """Small calibration map fit only on the calibration patients."""
    def fit(self, p, y):
        s = logit(_clip(p))
        f = lambda v: log_loss(y, expit(v[0] * s + v[1]))
        from scipy.optimize import minimize
        self.a_, self.b_ = minimize(f, (1., 0.), method="L-BFGS-B").x
        return self
    def predict(self, p): return expit(self.a_ * logit(_clip(p)) + self.b_)

def fusion_features(tabular_p, temporal_p):
    """Late-fusion features are probabilities only—no raw held-out features."""
    a, b = _clip(tabular_p), _clip(temporal_p)
    return np.c_[a, b, np.abs(a - b), (a + b) / 2]

@dataclass
class FusionResult:
    strategy: str
    validation: dict
    fitted_on: str

class HybridFusionSuite:
    """Evaluate averaging, learned weights, late fusion, and OOF stacking.

    `fit_oof` accepts one out-of-fold base probability per training window and
    group IDs.  It internally cross-fits fusion models by patient, then selects
    a strategy from those measured OOF validation estimates.  Feature-level
    fusion is intentionally not fit here: it needs a jointly trained encoder
    and is a distinct, higher-capacity experiment rather than an ensemble.
    """
    def fit_oof(self, tabular_oof, temporal_oof, y, patient_ids, folds=5):
        a, b, y, g = map(np.asarray, (tabular_oof, temporal_oof, y, patient_ids))
        if len(np.unique(g)) < folds: raise ValueError("Need at least one patient per fusion fold.")
        preds = {k: np.zeros(len(y)) for k in ("probability_average", "weighted_ensemble", "late_fusion", "stacking")}
        cv = GroupKFold(n_splits=folds)
        for tr, va in cv.split(a, y, g):
            # Weight is learned only from other patients in this OOF-training fold.
            objective = lambda w: log_loss(y[tr], _clip(w * a[tr] + (1 - w) * b[tr]))
            w = minimize_scalar(objective, bounds=(0, 1), method="bounded").x
            preds["probability_average"][va] = .5 * a[va] + .5 * b[va]
            preds["weighted_ensemble"][va] = w * a[va] + (1 - w) * b[va]
            # Late fusion: transparent logistic combination of probability and disagreement.
            late = LogisticRegression(class_weight="balanced", max_iter=1000).fit(fusion_features(a[tr], b[tr]), y[tr])
            preds["late_fusion"][va] = late.predict_proba(fusion_features(a[va], b[va]))[:, 1]
            # Stacking is deliberately regularized and sees only base OOF outputs.
            stack = LogisticRegression(C=.1, class_weight="balanced", max_iter=1000).fit(
                np.c_[logit(_clip(a[tr])), logit(_clip(b[tr]))], y[tr])
            preds["stacking"][va] = stack.predict_proba(np.c_[logit(_clip(a[va])), logit(_clip(b[va]))])[:, 1]
        self.oof_predictions_ = preds
        self.validation_ = {name: _metric(y, p) for name, p in preds.items()}
        # Prefer calibrated-probability quality after ranking; no test information is used.
        self.selected_ = sorted(self.validation_, key=lambda n: (-self.validation_[n]["AUPRC"], self.validation_[n]["Brier"]))[0]
        self.weight_ = minimize_scalar(lambda w: log_loss(y, _clip(w*a + (1-w)*b)), bounds=(0, 1), method="bounded").x
        self.late_ = LogisticRegression(class_weight="balanced", max_iter=1000).fit(fusion_features(a, b), y)
        self.stack_ = LogisticRegression(C=.1, class_weight="balanced", max_iter=1000).fit(
            np.c_[logit(_clip(a)), logit(_clip(b))], y)
        return self

    def raw_predict(self, tabular_p, temporal_p, strategy=None):
        strategy = strategy or self.selected_
        a, b = _clip(tabular_p), _clip(temporal_p)
        if strategy == "probability_average": return (a + b) / 2
        if strategy == "weighted_ensemble": return self.weight_ * a + (1-self.weight_) * b
        if strategy == "late_fusion": return self.late_.predict_proba(fusion_features(a, b))[:, 1]
        if strategy == "stacking": return self.stack_.predict_proba(np.c_[logit(a), logit(b)])[:, 1]
        raise ValueError(f"Unknown strategy: {strategy}")

    def calibrate(self, calibration_tabular_p, calibration_temporal_p, calibration_y):
        """Call once, after strategy selection, on distinct calibration patients."""
        self.calibrator_ = Platt().fit(self.raw_predict(calibration_tabular_p, calibration_temporal_p), calibration_y)
        return self

    def predict(self, tabular_p, temporal_p):
        raw = self.raw_predict(tabular_p, temporal_p)
        return self.calibrator_.predict(raw) if hasattr(self, "calibrator_") else raw

    def report(self):
        return pd.DataFrame(self.validation_).T.assign(selection_split="patient-level OOF train predictions")

    def risk_record(self, tabular_probability, temporal_probability, timestamp, horizon_hours,
                    tabular_factors=None, temporal_factors=None, signal_quality='HIGH',
                    predictive_uncertainty=None):
        """Clinical serving contract; factors must be computed from the same anchor."""
        p = float(self.predict([tabular_probability], [temporal_probability])[0])
        disagreement = abs(float(tabular_probability) - float(temporal_probability))
        entropy = -(p*np.log(p + EPS) + (1-p)*np.log(1-p + EPS)) / np.log(2)
        factors = (tabular_factors or []) + (temporal_factors or [])
        quality = str(signal_quality).upper()
        multiplier = {'HIGH': 1.0, 'MEDIUM': .75, 'LOW': .50}.get(quality, .50)
        # When a calibrated uncertainty layer supplies a confidence score it
        # takes precedence over entropy, which measures ambiguity only.
        uncertainty = predictive_uncertainty or {}
        reliability = float(uncertainty.get('confidence_score', 1 - entropy))
        adjusted_confidence = float(reliability * multiplier)
        confidence_label = uncertainty.get('confidence',
            'HIGH' if adjusted_confidence >= .70 else 'MEDIUM' if adjusted_confidence >= .40 else 'LOW')
        priority = ('URGENT' if p >= .70 and quality == 'HIGH' else
                    'HIGH' if p >= .35 and quality != 'LOW' else
                    'REVIEW_SIGNAL' if p >= .35 else 'ROUTINE')
        uncertainty_payload = {"base_model_disagreement": disagreement,
                               "probability_ambiguity": float(entropy),
                               "warning": "Review if base-model disagreement is high."}
        uncertainty_payload.update({k: v for k, v in uncertainty.items()
                                    if k not in {'risk_probability', 'confidence_score', 'confidence'}})
        return {"risk_probability": p, "prediction_timestamp": str(timestamp),
                "prediction_horizon_hours": horizon_hours, "fusion_strategy": self.selected_,
                "confidence": confidence_label, "confidence_score": adjusted_confidence,
                "signal_quality": quality, "alert_priority": priority,
                "uncertainty": uncertainty_payload,
                "contributing_factors": factors}

def clinical_comparison_template():
    """Never impute performance for a rule with incomplete required inputs."""
    return pd.DataFrame([
        ["SIRS", "requires train-fitted score-to-risk map", "Not measured: WBC unavailable in fallback cohort"],
        ["MEWS", "requires train-fitted score-to-risk map", "Not measured: SBP/GCS unavailable in fallback cohort"],
        ["NEWS/NEWS2", "requires train-fitted score-to-risk map", "Not measured: SBP/GCS/oxygen unavailable in fallback cohort"],
        ["Logistic Regression", "read model_selection_decision.json validation metrics", "Measured separately"],
        ["XGBoost/LightGBM", "read model_selection_decision.json validation metrics", "Measured separately"],
        ["Temporal model", "patient-disjoint temporal validation", "Measured separately; align split before head-to-head comparison"],
        ["Hybrid SepsisGuard", "OOF fusion + calibration holdout", "Run only after shared-split OOF base predictions exist"],
    ], columns=["System", "Evaluation protocol", "Evidence status"])

if __name__ == "__main__":
    clinical_comparison_template().to_csv("model/hybrid_comparison_protocol.csv", index=False)
