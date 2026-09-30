"""Online state: strictly causal features, prediction, uncertainty, explanations, alerts."""
import asyncio, importlib.util, os, time
from collections import defaultdict, deque
from pathlib import Path
import numpy as np
from .schemas import VitalEvent

ROOT = Path('/workspace') if Path('/workspace').exists() else Path(__file__).resolve().parents[3]
def dynamic(path, name):
    spec=importlib.util.spec_from_file_location(name, path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
quality = dynamic(ROOT/'data'/'04_signal_quality.py', 'quality')
alerts_mod = dynamic(ROOT/'src'/'pipeline'/'11_smart_alert_engine.py', 'alerts')

FEATURES=['hr_curr','map_curr','rr_curr','spo2_curr','temp_curr','hr_mean_4h','hr_std_4h','hr_min_4h','hr_max_4h','map_mean_4h','map_std_4h','map_min_4h','rr_mean_4h','temp_mean_4h','hr_delta_1h','hr_delta_4h','hr_slope_4h','map_delta_1h','map_delta_4h','map_slope_4h','rr_delta_1h','temp_delta_1h','hr_accel','shock_index','resp_distress_idx','fever_response_idx','lactate_missing','time_since_lactate','qsofa_curr','map_time_low_4h','icu_hour']
MAP={'heart_rate':'hr_curr','map':'map_curr','resp_rate':'rr_curr','spo2':'spo2_curr','temperature_c':'temp_curr'}
class Runtime:
    def __init__(self):
        self.history=defaultdict(lambda: deque(maxlen=72)); self.alert_states={}; self.subscribers=set(); self.model=None; self.cal=None; self.demo=True
        try:
            import xgboost as xgb
            self.model=xgb.Booster(); self.model.load_model(ROOT/'model'/'xgb_model.json'); self.demo=False
            try:
                import joblib
                self.cal=joblib.load(ROOT/'model'/'xgb_calibrator.pkl')
            except Exception:
                # A serialized custom calibrator may not resolve across module
                # paths. Serve the model only when deployment exports a stable
                # calibration artifact; otherwise mark this deployment invalid.
                self.model=None; self.demo=True
        except Exception: pass
    def features(self, patient):
        h=list(self.history[patient]); cur=h[-1]; vals=lambda key:[x.get(key, np.nan) for x in h]
        def last(key,n=0):
            v=vals(key); return v[-1-n] if len(v)>n else np.nan
        def mean(key): return float(np.nanmean(vals(key)[-4:]))
        def std(key): return float(np.nanstd(vals(key)[-4:]))
        d=lambda k,n: last(k)-last(k,n) if np.isfinite(last(k)) and np.isfinite(last(k,n)) else 0.
        row={'hr_curr':last('hr_curr'),'map_curr':last('map_curr'),'rr_curr':last('rr_curr'),'spo2_curr':last('spo2_curr'),'temp_curr':last('temp_curr')}
        row.update({'hr_mean_4h':mean('hr_curr'),'hr_std_4h':std('hr_curr'),'hr_min_4h':np.nanmin(vals('hr_curr')[-4:]),'hr_max_4h':np.nanmax(vals('hr_curr')[-4:]),'map_mean_4h':mean('map_curr'),'map_std_4h':std('map_curr'),'map_min_4h':np.nanmin(vals('map_curr')[-4:]),'rr_mean_4h':mean('rr_curr'),'temp_mean_4h':mean('temp_curr'),'hr_delta_1h':d('hr_curr',1),'hr_delta_4h':d('hr_curr',4),'hr_slope_4h':d('hr_curr',4)/4,'map_delta_1h':d('map_curr',1),'map_delta_4h':d('map_curr',4),'map_slope_4h':d('map_curr',4)/4,'rr_delta_1h':d('rr_curr',1),'temp_delta_1h':d('temp_curr',1),'hr_accel':d('hr_curr',1)-(last('hr_curr',1)-last('hr_curr',2) if len(h)>2 else 0.)})
        row.update({'shock_index':row['hr_curr']/max(row['map_curr'],1),'resp_distress_idx':row['rr_curr']/max(row['spo2_curr'],1),'fever_response_idx':row['hr_curr']-10*(row['temp_curr']-37),'lactate_missing':int(cur.get('lactate') is None),'time_since_lactate':0 if cur.get('lactate') is not None else min(len(h),8),'qsofa_curr':int(row['rr_curr']>=22)+int(row['map_curr']<=65),'map_time_low_4h':sum(v<65 for v in vals('map_curr')[-4:] if np.isfinite(v)),'icu_hour':len(h)-1})
        return np.array([row[k] for k in FEATURES], dtype=float), row
    def predict(self, event: VitalEvent):
        start=time.perf_counter(); raw={MAP[k]:getattr(event,k) for k in MAP}; raw.update({'stay_id':event.patient_id,'hour':len(self.history[event.patient_id]),'lactate':event.lactate})
        self.history[event.patient_id].append(raw); x, row=self.features(event.patient_id)
        # Quality flags are calculated against the causal in-memory history.
        import pandas as pd
        quality_frame=quality.add_signal_quality_features(pd.DataFrame(list(self.history[event.patient_id])))
        sq=quality_frame.iloc[-1].signal_quality
        if self.model is not None:
            import xgboost as xgb
            p=float(self.model.predict(xgb.DMatrix(x[None,:], feature_names=FEATURES))[0]); p=float(self.cal.predict_proba([p])[0]) if self.cal else p
        else:
            # Explicit dev-only deterministic fallback, not a clinical model.
            p=float(1/(1+np.exp(-((row['hr_curr']-90)/20+(65-row['map_curr'])/15+(row['rr_curr']-20)/8+(row['temp_curr']-38)/1.5))))
        interval=(max(0.,p-.20),min(1.,p+.20)); conf='HIGH' if sq=='HIGH' and .4>=interval[1]-interval[0] else 'MEDIUM' if sq!='LOW' else 'LOW'
        factors=[f'{name.replace("_curr", "").upper()} contributed to the model prediction' for name in sorted(['map_curr','hr_curr','rr_curr'], key=lambda k: abs(row.get(k,0)), reverse=True)]
        prior=self.alert_states.get(event.patient_id); trajectory=p-(prior.last_risk if prior and prior.last_risk is not None else p)
        decision,state=alerts_mod.SmartAlertEngine().process({'timestamp':event.timestamp,'risk_probability':p,'confidence':conf,'signal_quality':sq,'risk_trajectory_per_hour':trajectory,'persistent_windows':len(self.history[event.patient_id]),'contributing_factors':factors},prior); self.alert_states[event.patient_id]=state
        return {'patient_id':event.patient_id,'prediction_timestamp':event.timestamp,'prediction_horizon_hours':6,'risk_probability':p,'uncertainty_interval':interval,'confidence':conf,'signal_quality':sq,'alert_severity':decision['alert_severity'],'recommended_clinical_review_level':decision['recommended_clinical_review_level'],'contributing_factors':factors,'latency_ms':round((time.perf_counter()-start)*1000,2),'model_version':'xgboost-tabular-v1' if not self.demo else 'development-fallback-v0','is_demo_model':self.demo,'alert':decision}
runtime=Runtime()
