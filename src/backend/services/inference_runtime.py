"""Online state: strictly causal features, prediction, uncertainty, explanations, alerts with timestamp-based windowing."""
import asyncio
import importlib.util
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit

from src.backend.schemas.schemas import VitalEvent
from src.pipeline.canonical_features import FEATURES, build_feature_row

# Register SigmoidCalibrator in __main__ to fix joblib unpickling path mismatch (R-01)
class SigmoidCalibrator:
    def fit(self, scores, labels):
        pass
    def predict_proba(self, scores):
        scores = np.asarray(scores)
        return expit(self.a_ * scores + self.b_)

setattr(sys.modules['__main__'], 'SigmoidCalibrator', SigmoidCalibrator)

ROOT = Path(__file__).resolve().parents[3]

def _import_dynamic(path, name):
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# Try direct import first, then dynamic path loading
try:
    from src.pipeline.smart_alert_engine import SmartAlertEngine
    alerts_mod = type('AlertsMod', (), {'SmartAlertEngine': SmartAlertEngine})
except Exception:
    alerts_mod = _import_dynamic(ROOT / 'src' / 'pipeline' / '11_smart_alert_engine.py', 'alerts')

try:
    import data.signal_quality as quality
except Exception:
    quality = _import_dynamic(ROOT / 'data' / '04_signal_quality.py', 'quality')

FEATURES = list(FEATURES)

MAP = {
    'heart_rate': 'hr_curr',
    'map': 'map_curr',
    'resp_rate': 'rr_curr',
    'spo2': 'spo2_curr',
    'temperature_c': 'temp_curr'
}

def ensure_utc(dt):
    if isinstance(dt, str):
        dt = pd.to_datetime(dt).to_pydatetime()
    if getattr(dt, 'tzinfo', None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class Runtime:
    def __init__(self):
        self.history = defaultdict(list)
        self.alert_states = {}
        self.subscribers = set()
        self.scaler = None
        self.model = None
        self.cal = None
        self.explainer = None
        self.demo = True
        self.model_version_name = 'development-fallback-v0'

        # Load primary model selected by project evidence (Logistic Regression + Sigmoid Calibrator)
        try:
            import joblib
            scaler_path = ROOT / 'model' / 'scaler.pkl'
            lr_model_path = ROOT / 'model' / 'lr_model.pkl'
            lr_cal_path = ROOT / 'model' / 'lr_calibrator.pkl'

            if lr_model_path.exists():
                self.model = joblib.load(str(lr_model_path))
                if scaler_path.exists():
                    self.scaler = joblib.load(str(scaler_path))
                if lr_cal_path.exists():
                    self.cal = joblib.load(str(lr_cal_path))
                self.demo = False
                self.model_version_name = 'logistic-regression-v1'

                # Initialize LinearExplainer for Logistic Regression using background mean (zero vector in standardized space)
                try:
                    import shap
                    background_zero = np.zeros((1, len(FEATURES)), dtype=float)
                    self.explainer = shap.LinearExplainer(self.model, background_zero)
                except Exception:
                    self.explainer = None
            else:
                # Secondary fallback to XGBoost if LR artifact is missing
                import xgboost as xgb
                xgb_model_path = ROOT / 'model' / 'xgb_model.json'
                xgb_cal_path = ROOT / 'model' / 'xgb_calibrator.pkl'
                if xgb_model_path.exists():
                    self.model = xgb.Booster()
                    self.model.load_model(str(xgb_model_path))
                    if xgb_cal_path.exists():
                        self.cal = joblib.load(str(xgb_cal_path))
                    self.demo = False
                    self.model_version_name = 'xgboost-tabular-v1'
                    try:
                        import shap
                        self.explainer = shap.TreeExplainer(self.model)
                    except Exception:
                        self.explainer = None
        except Exception as exc:
            # Mark runtime as demo fallback if artifacts fail to load
            self.model = None
            self.scaler = None
            self.cal = None
            self.explainer = None
            self.demo = True
            self.model_version_name = 'development-fallback-v0'

    def features(self, patient: str):
        raw_history = self.history[patient]
        canonical_history = [{
            'timestamp': event['timestamp'],
            'heart_rate': event.get('hr_curr'),
            'map': event.get('map_curr'),
            'resp_rate': event.get('rr_curr'),
            'spo2': event.get('spo2_curr'),
            'temperature_c': event.get('temp_curr'),
            'lactate': event.get('lactate'),
        } for event in raw_history]
        row = build_feature_row(canonical_history)
        return np.array([row[name] for name in FEATURES], dtype=float), row

    def compute_shap_explanation(self, x_raw: np.ndarray) -> tuple[dict, list[str]]:
        if self.demo or self.model is None or self.explainer is None or self.scaler is None:
            return {
                'explanation_available': False,
                'reason': 'SHAP explanation unavailable for fallback/demo model',
                'output_space': 'log-odds',
                'base_value_log_odds': None,
                'explained_output_log_odds': None,
                'feature_attributions': [],
                'top_contributions': [],
                'model_version': self.model_version_name
            }, ["SHAP explanation unavailable for fallback model"]

        try:
            x_in = np.nan_to_num(x_raw.reshape(1, -1), nan=0.0)
            x_scaled = self.scaler.transform(x_in)
            sv = self.explainer(x_scaled)

            base_val = float(sv.base_values[0])
            shap_vals = np.asarray(sv.values[0], dtype=float)
            explained_log_odds = float(base_val + np.sum(shap_vals))

            if hasattr(self.model, 'decision_function'):
                decision_log_odds = float(self.model.decision_function(x_scaled)[0])
                if abs(explained_log_odds - decision_log_odds) > 1e-3:
                    return {
                        'explanation_available': False,
                        'reason': 'SHAP additivity verification failed',
                        'output_space': 'log-odds',
                        'base_value_log_odds': round(base_val, 6),
                        'explained_output_log_odds': round(explained_log_odds, 6),
                        'feature_attributions': [],
                        'top_contributions': [],
                        'model_version': self.model_version_name
                    }, ["SHAP additivity verification failed"]

            attributions = []
            x_flat = x_raw.ravel()
            for i, feat_name in enumerate(FEATURES):
                f_val = float(x_flat[i]) if np.isfinite(x_flat[i]) else 0.0
                s_val = float(shap_vals[i])
                abs_val = float(abs(s_val))
                direction = 'positive' if s_val > 0 else ('negative' if s_val < 0 else 'neutral')
                attributions.append({
                    'feature_name': feat_name,
                    'feature_value': f_val,
                    'shap_value': round(s_val, 6),
                    'contribution_direction': direction,
                    'absolute_contribution': round(abs_val, 6),
                    'model_version': self.model_version_name
                })

            attributions.sort(key=lambda a: a['absolute_contribution'], reverse=True)
            top_5 = attributions[:5]

            factors = []
            for a in top_5:
                sign_str = f"+{a['shap_value']:.3f}" if a['shap_value'] > 0 else f"{a['shap_value']:.3f}"
                factors.append(
                    f"{a['feature_name']} (val={a['feature_value']:.2f}): {a['contribution_direction']} model contribution ({sign_str} log-odds)"
                )

            shap_dict = {
                'explanation_available': True,
                'output_space': 'log-odds',
                'base_value_log_odds': round(base_val, 6),
                'explained_output_log_odds': round(explained_log_odds, 6),
                'feature_attributions': attributions,
                'top_contributions': top_5,
                'model_version': self.model_version_name
            }
            return shap_dict, factors
        except Exception as exc:
            return {
                'explanation_available': False,
                'reason': f'SHAP calculation error: {str(exc)}',
                'output_space': 'log-odds',
                'base_value_log_odds': None,
                'explained_output_log_odds': None,
                'feature_attributions': [],
                'top_contributions': [],
                'model_version': self.model_version_name
            }, [f"SHAP calculation failed: {str(exc)}"]

    def predict(self, event: VitalEvent):
        start = time.perf_counter()
        ts = ensure_utc(event.timestamp)
        raw = {MAP[k]: getattr(event, k) for k in MAP}
        raw.update({
            'stay_id': event.patient_id,
            'timestamp': ts,
            'received_at': time.perf_counter(),
            'lactate': event.lactate
        })

        patient_hist = self.history[event.patient_id]
        
        # Deduplicate identical timestamps for the same patient deterministically
        patient_hist = [x for x in patient_hist if x['timestamp'] != ts]
        patient_hist.append(raw)
        
        # Chronological sorting by clinical timestamp
        patient_hist.sort(key=lambda x: (x['timestamp'], x['received_at']))

        # Trim history to max 72 clinical hours from latest timestamp
        latest_ts = patient_hist[-1]['timestamp']
        cutoff_ts = latest_ts - timedelta(hours=72)
        patient_hist = [x for x in patient_hist if x['timestamp'] >= cutoff_ts]

        self.history[event.patient_id] = patient_hist

        x, row = self.features(event.patient_id)

        sq = 'HIGH'
        if quality and hasattr(quality, 'add_signal_quality_features'):
            try:
                hist_df = pd.DataFrame([dict(e, hour=int((e['timestamp'] - patient_hist[0]['timestamp']).total_seconds() / 3600.0)) for e in patient_hist])
                quality_frame = quality.add_signal_quality_features(hist_df)
                sq = quality_frame.iloc[-1].signal_quality
            except Exception:
                sq = 'HIGH'

        if self.model is not None:
            # Handle scikit-learn LogisticRegression model vs XGBoost Booster
            if hasattr(self.model, 'predict_proba'):
                x_in = np.nan_to_num(x[None, :], nan=0.0)
                if self.scaler is not None:
                    x_in = self.scaler.transform(x_in)
                raw_p = float(self.model.predict_proba(x_in)[0, 1])
            else:
                import xgboost as xgb
                raw_p = float(self.model.predict(xgb.DMatrix(x[None, :], feature_names=FEATURES))[0])
            
            p = float(self.cal.predict_proba([raw_p])[0]) if self.cal else raw_p
        else:
            hr_val = row['hr_curr'] if np.isfinite(row['hr_curr']) else 80.0
            map_val = row['map_curr'] if np.isfinite(row['map_curr']) else 75.0
            rr_val = row['rr_curr'] if np.isfinite(row['rr_curr']) else 16.0
            temp_val = row['temp_curr'] if np.isfinite(row['temp_curr']) else 37.0
            p = float(1 / (1 + np.exp(-((hr_val - 90) / 20 + (65 - map_val) / 15 + (rr_val - 20) / 8 + (temp_val - 38) / 1.5))))

        # Conformal predictive uncertainty is unavailable (no conformal calibration artifact exists)
        uncertainty_summary = {
            'uncertainty_available': False,
            'method': 'UNAVAILABLE',
            'reason': 'Conformal prediction calibration artifact unavailable in repository',
            'coverage_level': None,
            'interval_lower': None,
            'interval_upper': None,
            'model_version': self.model_version_name if not self.demo else 'development-fallback-v0'
        }
        interval = None
        conf = sq  # Reliability confidence maps directly to input signal quality
        
        # Real SHAP feature attributions
        shap_explanation, factors = self.compute_shap_explanation(x)
        
        prior = self.alert_states.get(event.patient_id)
        trajectory = p - (prior.last_risk if prior and prior.last_risk is not None else p)

        decision = {'alert_severity': None, 'recommended_clinical_review_level': 'No alert', 'alert_emitted': False}
        if alerts_mod and hasattr(alerts_mod, 'SmartAlertEngine'):
            try:
                engine = alerts_mod.SmartAlertEngine()
                
                decision, state = engine.process({
                    'timestamp': ts,
                    'risk_probability': p,
                    'confidence': conf,
                    'signal_quality': sq,
                    'risk_trajectory_per_hour': trajectory,
                    'contributing_factors': factors
                }, prior)
                self.alert_states[event.patient_id] = state
            except Exception:
                pass

        return {
            'patient_id': event.patient_id,
            'session_id': event.session_id,
            'prediction_timestamp': ts,
            'prediction_horizon_hours': 6,
            'risk_probability': p,
            'uncertainty_interval': interval,
            'uncertainty_summary': uncertainty_summary,
            'confidence': conf,
            'signal_quality': sq,
            'alert_severity': decision.get('alert_severity'),
            'recommended_clinical_review_level': decision.get('recommended_clinical_review_level', 'No alert'),
            'contributing_factors': factors,
            'shap_explanation': shap_explanation,
            'latency_ms': round((time.perf_counter() - start) * 1000, 2),
            'model_version': self.model_version_name if not self.demo else 'development-fallback-v0',
            'is_demo_model': self.demo,
            'alert': decision
        }

runtime = Runtime()
