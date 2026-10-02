"""
SepsisGuard AI - Model Training and Comparison Pipeline
=======================================================
Classifiers:
  1. Logistic Regression (L2, class_weight=balanced)
  2. XGBoost  (scale_pos_weight from TRAIN, early stopping on VAL)
  3. LightGBM (class_weight=balanced, early stopping on VAL)

Leakage controls (doc/09_train_val_test_strategy.md):
  - Patient-level GroupShuffleSplit: 70/15/15
  - StandardScaler fit only on TRAIN (Audit 4)
  - scale_pos_weight from TRAIN only (Audit 5)
  - RandomizedSearchCV + GroupKFold(5) on TRAIN only
  - Early stopping uses VAL, never TEST
  - Sigmoid calibration fitted on VAL holdout
  - TEST touched exactly once
"""
import os
import sys
import time
import logging
import warnings
import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None



from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, RandomizedSearchCV
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    roc_curve, precision_recall_curve, confusion_matrix,
)
from scipy.special import expit
from scipy.optimize import minimize
import xgboost as xgb
try:
    import lightgbm as lgb
except ImportError:
    lgb = None
import joblib
from src.pipeline.canonical_features import FEATURES, build_feature_row

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/05_train_models.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("SepsisGuardML")

SEED = 42
np.random.seed(SEED)
ALERT_THRESHOLD = 0.35


# ---------------------------------------------------------------------------
# 1. Data generation (used when real processed data is absent)
# ---------------------------------------------------------------------------
def generate_demo_dataset(n_patients=300, max_hours=72):
    """
    Synthetic ICU dataset matching the SepsisGuard feature engineering
    framework (doc/07_feature_engineering_framework.md).

    Features produced per hourly window:
      - Current vitals (HR, MAP, RR, SpO2, Temp)
      - Rolling 4-h stats (mean, std, min, max)
      - 1-h and 4-h deltas / slopes
      - HR acceleration (2nd derivative)
      - Cross-parameter interactions: Shock Index, Respiratory Distress Index,
        Fever Response Index
      - Missingness indicators and time-since-lactate
      - qSOFA proxy
      - MAP time-below-65 (cumulative hypoperfusion load)

    Label = 1 if window falls within 6 h before sepsis onset, else 0.
    Prevalence ~ 18-22 %.
    """
    log.info("Generating synthetic demo dataset (no processed parquet found).")
    rng = np.random.default_rng(SEED)
    records = []

    for sid in range(n_patients):
        feature_history = []
        admission_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        n_h = int(rng.integers(12, max_hours))
        is_sep = rng.random() < 0.20
        onset = int(rng.integers(n_h // 2, n_h)) if is_sep else -1

        bhr   = float(rng.normal(78, 12))
        bmap  = float(rng.normal(72, 9))
        brr   = float(rng.normal(16, 3))
        bspo2 = float(rng.normal(97, 1.5))
        btemp = float(rng.normal(37.0, 0.3))

        hr_h, map_h, rr_h, spo2_h, temp_h = [], [], [], [], []

        for h in range(n_h):
            t = min(1.0, max(0.0, (h - max(0, onset - 8)) / 8.0)) if is_sep else 0.0
            hrv   = bhr   + t * 35  + float(rng.normal(0, 4))
            mapv  = bmap  - t * 25  + float(rng.normal(0, 4))
            rrv   = brr   + t * 10  + float(rng.normal(0, 1.5))
            spo2v = bspo2 - t * 5   + float(rng.normal(0, 0.8))
            tmpv  = btemp + t * 1.8 + float(rng.normal(0, 0.15))

            hr_h.append(hrv); map_h.append(mapv); rr_h.append(rrv)
            spo2_h.append(spo2v); temp_h.append(tmpv)

            w      = slice(max(0, h - 3), h + 1)
            hrw    = hr_h[w]; mapw = map_h[w]; rrw = rr_h[w]; tmpw = temp_h[w]

            hd1    = hr_h[h]   - hr_h[h - 1]   if h >= 1 else 0.0
            md1    = map_h[h]  - map_h[h - 1]   if h >= 1 else 0.0
            rd1    = rr_h[h]   - rr_h[h - 1]   if h >= 1 else 0.0
            td1    = temp_h[h] - temp_h[h - 1]  if h >= 1 else 0.0
            hd4    = hr_h[h]   - hr_h[max(0, h - 4)]
            md4    = map_h[h]  - map_h[max(0, h - 4)]
            hacc   = (hr_h[h] - hr_h[h - 1] if h >= 1 else 0.0) - \
                     (hr_h[h - 1] - hr_h[h - 2] if h >= 2 else 0.0)

            shock_idx  = hrv / max(mapv, 1.0)
            resp_idx   = rrv / max(spo2v, 1.0)
            fever_idx  = hrv - 10.0 * (tmpv - 37.0)

            lmis   = 1 if rng.random() > 0.25 else 0
            tsl    = int(rng.integers(1, 8)) if lmis else 0
            qsf    = int(rrv >= 22) + int(mapv <= 65)
            mtl    = sum(1 for v in mapw if v < 65)

            lbl = 1 if (is_sep and 0 <= (onset - h) <= 6) else 0

            feature_history.append({
                'timestamp': admission_time + timedelta(hours=h),
                'heart_rate': hrv, 'map': mapv, 'resp_rate': rrv,
                'spo2': spo2v, 'temperature_c': tmpv,
                'lactate': None if lmis else 1.0,
            })
            canonical = build_feature_row(feature_history)

            record = {
                "subject_id": sid, "stay_id": sid + 10000, "hour": h,
                "hr_curr": hrv, "map_curr": mapv, "rr_curr": rrv,
                "spo2_curr": spo2v, "temp_curr": tmpv,
                "hr_mean_4h": np.mean(hrw), "hr_std_4h": np.std(hrw) if len(hrw) > 1 else 0.0,
                "hr_min_4h": np.min(hrw), "hr_max_4h": np.max(hrw),
                "map_mean_4h": np.mean(mapw), "map_std_4h": np.std(mapw) if len(mapw) > 1 else 0.0,
                "map_min_4h": np.min(mapw), "rr_mean_4h": np.mean(rrw),
                "temp_mean_4h": np.mean(tmpw),
                "hr_delta_1h": hd1, "hr_delta_4h": hd4, "hr_slope_4h": hd4 / 4.0,
                "map_delta_1h": md1, "map_delta_4h": md4, "map_slope_4h": md4 / 4.0,
                "rr_delta_1h": rd1, "temp_delta_1h": td1, "hr_accel": hacc,
                "shock_index": shock_idx, "resp_distress_idx": resp_idx,
                "fever_response_idx": fever_idx,
                "lactate_missing": lmis, "time_since_lactate": tsl,
                "qsofa_curr": qsf, "map_time_low_4h": mtl,
                "icu_hour": h, "label": lbl,
            }
            # The same causal, timestamp-defined 31-feature implementation is
            # used by online inference. Synthetic labels remain demo-only.
            record.update(canonical)
            records.append(record)

    df = pd.DataFrame(records)
    log.info(
        f"  Generated {len(df)} rows | {df['label'].sum()} positive "
        f"({100.0 * df['label'].mean():.1f}%) | {n_patients} patients"
    )
    return df


# ---------------------------------------------------------------------------
# 2. Patient-level split with leakage audit
# ---------------------------------------------------------------------------
def patient_split(df):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=SEED)
    tri, tmpi = next(gss.split(df, groups=df["subject_id"]))
    dtr = df.iloc[tri].copy()
    dtemp = df.iloc[tmpi].copy()

    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=SEED)
    vi, tsi = next(gss2.split(dtemp, groups=dtemp["subject_id"]))
    dv  = dtemp.iloc[vi].copy()
    dte = dtemp.iloc[tsi].copy()

    trp = set(dtr["subject_id"])
    vp  = set(dv["subject_id"])
    tsp = set(dte["subject_id"])

    # Audit 1: zero patient overlap across all partitions
    assert len(trp & vp)  == 0, "LEAKAGE: train/val patient overlap"
    assert len(trp & tsp) == 0, "LEAKAGE: train/test patient overlap"
    assert len(vp  & tsp) == 0, "LEAKAGE: val/test patient overlap"

    log.info(
        f"Split — Train: {len(dtr)} rows / {len(trp)} pts | "
        f"Val: {len(dv)} rows / {len(vp)} pts | "
        f"Test: {len(dte)} rows / {len(tsp)} pts"
    )
    log.info(
        f"  Prevalence — Train: {100.0*dtr['label'].mean():.1f}% | "
        f"Val: {100.0*dv['label'].mean():.1f}% | "
        f"Test: {100.0*dte['label'].mean():.1f}%"
    )
    return dtr, dv, dte


# ---------------------------------------------------------------------------
# 3. Sigmoid (Platt) calibration on validation holdout
# ---------------------------------------------------------------------------
class SigmoidCalibrator:
    """
    Fits a logistic sigmoid to raw model scores using the validation set.
    Calibration never touches the test set.
    """
    def fit(self, scores, labels):
        def nll(params):
            a, b = params
            p = np.clip(expit(a * scores + b), 1e-7, 1 - 1e-7)
            return -np.mean(labels * np.log(p) + (1 - labels) * np.log(1 - p))
        res = minimize(nll, [1.0, 0.0], method="L-BFGS-B")
        self.a_, self.b_ = res.x
        return self

    def predict_proba(self, scores):
        return expit(self.a_ * scores + self.b_)


# ---------------------------------------------------------------------------
# 4. Metric computation (same suite as clinical baseline)
# ---------------------------------------------------------------------------
def compute_metrics(y_true, proba, name):
    auroc = roc_auc_score(y_true, proba)
    auprc = average_precision_score(y_true, proba)
    brier = brier_score_loss(y_true, proba)

    yp = (proba >= ALERT_THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, yp, labels=[0, 1]).ravel()
    sens = tp / max(tp + fn, 1)
    spec = tn / max(tn + fp, 1)
    ppv  = tp / max(tp + fp, 1)
    npv  = tn / max(tn + fn, 1)
    ar   = (tp + fp) / max(len(y_true), 1)
    fap  = fp / max(fp + tn, 1)

    log.info(
        f"[{name}] AUROC={auroc:.4f}  AUPRC={auprc:.4f}  Brier={brier:.4f}  "
        f"Sens={sens:.3f}  Spec={spec:.3f}  PPV={ppv:.3f}  NPV={npv:.3f}  "
        f"AlertRate={ar:.3f}  FalseAlert%={fap*100:.1f}"
    )
    return dict(
        model=name, AUROC=auroc, AUPRC=auprc, Brier=brier,
        Sensitivity=sens, Specificity=spec, PPV=ppv, NPV=npv,
        AlertRate=ar, FalseAlertPct=fap,
        TP=int(tp), FP=int(fp), TN=int(tn), FN=int(fn),
    )


# ---------------------------------------------------------------------------
# 5. Model training
# ---------------------------------------------------------------------------
def train_lr(Xts, yt, Xvs, yv, gt):
    """Logistic Regression with class_weight=balanced and CV-tuned C."""
    log.info("Training Logistic Regression...")
    t0 = time.time()
    cv = GroupKFold(n_splits=5)
    base = LogisticRegression(
        solver="lbfgs", max_iter=2000,
        class_weight="balanced", random_state=SEED
    )
    search = RandomizedSearchCV(
        base, {"C": np.logspace(-3, 2, 30)}, n_iter=15,
        scoring="roc_auc", cv=cv, refit=True, random_state=SEED, n_jobs=-1
    )
    search.fit(Xts, yt, groups=gt)
    best = search.best_estimator_
    log.info(f"  Best C={search.best_params_['C']:.4f}  CV AUROC={search.best_score_:.4f}")
    raw_val = best.predict_proba(Xvs)[:, 1]
    cal = SigmoidCalibrator().fit(raw_val, yv.values)
    return best, cal, time.time() - t0, search.best_score_


def train_xgboost(Xt, yt, Xv, yv, gt, spw):
    """
    XGBoost with scale_pos_weight (TRAIN-derived).
    Phase 1: RandomizedSearchCV + GroupKFold on TRAIN.
    Phase 2: Refit n_estimators=500 with early_stopping on VAL.
    """
    log.info("Training XGBoost...")
    t0 = time.time()
    cv = GroupKFold(n_splits=5)
    base = xgb.XGBClassifier(
        n_estimators=200, scale_pos_weight=spw,
        eval_metric="aucpr", random_state=SEED, verbosity=0,
    )
    param_dist = {
        "max_depth":        [3, 4, 5, 6],
        "learning_rate":    [0.01, 0.05, 0.1, 0.2],
        "subsample":        [0.6, 0.75, 0.9, 1.0],
        "colsample_bytree": [0.5, 0.7, 0.9, 1.0],
        "min_child_weight": [1, 3, 5, 10],
        "gamma":            [0, 0.1, 0.3, 0.5],
        "reg_alpha":        [0, 0.1, 1.0],
        "reg_lambda":       [1, 1.5, 2.0],
    }
    search = RandomizedSearchCV(
        base, param_dist, n_iter=30, scoring="roc_auc",
        cv=cv, refit=True, random_state=SEED, n_jobs=-1
    )
    search.fit(Xt, yt, groups=gt)
    log.info(f"  CV AUROC={search.best_score_:.4f}  params={search.best_params_}")

    # Refit with more trees + early stopping on VAL
    final = xgb.XGBClassifier(
        n_estimators=500, scale_pos_weight=spw,
        eval_metric="aucpr", random_state=SEED, verbosity=0,
        early_stopping_rounds=30,
        **search.best_params_,
    )
    final.fit(Xt, yt, eval_set=[(Xv, yv)], verbose=False)
    log.info(f"  Best iteration={final.best_iteration}  val_score={final.best_score:.4f}")

    cal = SigmoidCalibrator().fit(final.predict_proba(Xv)[:, 1], yv.values)
    return final, cal, time.time() - t0, search.best_score_


def train_lightgbm(Xt, yt, Xv, yv, gt):
    if lgb is None:
        return None, None, 0.0, 0.0
    """
    LightGBM with class_weight=balanced.
    Phase 1: RandomizedSearchCV + GroupKFold on TRAIN.
    Phase 2: Refit n_estimators=500 with early_stopping on VAL.
    """
    log.info("Training LightGBM...")
    t0 = time.time()
    cv = GroupKFold(n_splits=5)
    base = lgb.LGBMClassifier(
        n_estimators=200, class_weight="balanced",
        random_state=SEED, verbose=-1,
    )
    param_dist = {
        "num_leaves":        [15, 31, 63, 127],
        "max_depth":         [-1, 5, 8, 12],
        "learning_rate":     [0.01, 0.05, 0.1, 0.2],
        "subsample":         [0.6, 0.75, 0.9, 1.0],
        "colsample_bytree":  [0.5, 0.7, 0.9, 1.0],
        "min_child_samples": [5, 10, 20, 50],
        "reg_alpha":         [0, 0.1, 1.0],
        "reg_lambda":        [0, 0.1, 1.0],
    }
    search = RandomizedSearchCV(
        base, param_dist, n_iter=30, scoring="roc_auc",
        cv=cv, refit=True, random_state=SEED, n_jobs=-1
    )
    search.fit(Xt, yt, groups=gt)
    log.info(f"  CV AUROC={search.best_score_:.4f}  params={search.best_params_}")

    final = lgb.LGBMClassifier(
        n_estimators=500, class_weight="balanced",
        random_state=SEED, verbose=-1,
        **search.best_params_,
    )
    cbs = [lgb.early_stopping(stopping_rounds=30, verbose=False), lgb.log_evaluation(-1)]
    final.fit(Xt, yt, eval_set=[(Xv, yv)], callbacks=cbs)
    log.info(f"  Best iteration={final.best_iteration_}")

    cal = SigmoidCalibrator().fit(final.predict_proba(Xv)[:, 1], yv.values)
    return final, cal, time.time() - t0, search.best_score_


# ---------------------------------------------------------------------------
# 6. Feature importance
# ---------------------------------------------------------------------------
def plot_feat_imp(model, feats, name, out_dir):
    if plt is None:
        return None
    if not hasattr(model, "feature_importances_"):
        return None
    imp = pd.Series(model.feature_importances_, index=feats)
    top = imp.nlargest(20).sort_values()
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = plt.cm.viridis(np.linspace(0.3, 0.85, len(top)))
    top.plot(kind="barh", ax=ax, color=colors)
    ax.set_title(f"{name} — Top-20 Feature Importances", fontsize=13)
    ax.set_xlabel("Importance (gain)")
    plt.tight_layout()
    path = os.path.join(out_dir, f"feat_imp_{name.replace(' ', '_')}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info(f"  Saved feature importance: {path}")
    log.info(f"  Top-5 [{name}]: {list(imp.nlargest(5).index)}")
    return imp


# ---------------------------------------------------------------------------
# 7. Calibration reliability diagram
# ---------------------------------------------------------------------------
def plot_calibration(results, y_test, out_dir):
    if plt is None:
        return None
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="Perfect calibration")
    for r in results:
        pt, pp = calibration_curve(y_test, r["proba"], n_bins=10)
        ax.plot(pp, pt, marker="o", lw=2,
                label=f"{r['name']} (Brier={r['metrics']['Brier']:.3f})")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Reliability Diagram — Calibration")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "calibration_plot.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info(f"Calibration plot saved: {path}")


# ---------------------------------------------------------------------------
# 8. ROC / PR curves
# ---------------------------------------------------------------------------
def plot_roc_pr(results, y_test, out_dir):
    if plt is None:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    palette = ["#2196F3", "#FF5722", "#4CAF50"]
    for i, r in enumerate(results):
        fpr, tpr, _ = roc_curve(y_test, r["proba"])
        pr, rc, _   = precision_recall_curve(y_test, r["proba"])
        c  = palette[i]
        nm = r["name"]
        axes[0].plot(fpr, tpr, lw=2, color=c,
                     label=f"{nm} AUROC={r['metrics']['AUROC']:.3f}")
        axes[1].plot(rc, pr, lw=2, color=c,
                     label=f"{nm} AUPRC={r['metrics']['AUPRC']:.3f}")
    axes[0].plot([0, 1], [0, 1], "k--", lw=1)
    axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR")
    axes[0].set_title("ROC Curves"); axes[0].legend(loc="lower right"); axes[0].grid(alpha=0.3)
    axes[1].axhline(y_test.mean(), color="k", ls="--", lw=1,
                    label=f"No-skill ({y_test.mean():.2f})")
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
    axes[1].set_title("PR Curves"); axes[1].legend(loc="upper right"); axes[1].grid(alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "roc_pr_curves.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info(f"ROC/PR curves saved: {path}")


# ---------------------------------------------------------------------------
# 9. Comparison table
# ---------------------------------------------------------------------------
INTERP = {
    "Logistic Regression": "High  — global coefficients, monotone, GDPR-ready",
    "XGBoost":             "Medium — SHAP explanations available per prediction",
    "LightGBM":            "Medium — SHAP explanations available per prediction",
}

def build_comparison_table(results, meta):
    rows = []
    for r in results:
        m  = r["metrics"]
        nm = r["name"]
        mt = meta[nm]
        rows.append({
            "Model":           nm,
            # Performance
            "AUROC":           round(m["AUROC"], 4),
            "AUPRC":           round(m["AUPRC"], 4),
            "Sensitivity":     round(m["Sensitivity"], 3),
            "Specificity":     round(m["Specificity"], 3),
            "PPV":             round(m["PPV"], 3),
            "NPV":             round(m["NPV"], 3),
            # Calibration
            "Brier Score":     round(m["Brier"], 4),
            "Calibration":     "Sigmoid/Platt (val holdout)",
            # Computational cost
            "Train Time (s)":  round(mt["tt"], 1),
            "CV AUROC":        round(mt["cv"], 4),
            # Alert burden
            "Alert Rate":      round(m["AlertRate"], 3),
            "False Alert %":   round(m["FalseAlertPct"] * 100, 1),
            # Qualitative
            "Interpretability": INTERP[nm],
            "Imbalance":       ("class_weight=balanced"
                                if nm != "XGBoost"
                                else f"scale_pos_weight={mt.get('spw', 0):.1f}"),
        })
    return pd.DataFrame(rows).set_index("Model")


# ---------------------------------------------------------------------------
# 10. Evidence-based primary model selection
# ---------------------------------------------------------------------------
def select_primary(df):
    """
    Composite rank across four clinical-priority criteria from validation
    evidence.  This function must never be passed the final test table:
    selection is frozen before the one-shot test evaluation.
      1. AUPRC      — most informative for imbalanced detection tasks
      2. Brier Score — calibration quality (lower is better)
      3. Sensitivity — clinical cost of missed sepsis >> alert fatigue
      4. Alert Rate  — operational burden on ICU nursing staff
    """
    d = df.copy()
    d["_rank"] = (
        d["AUPRC"].rank(ascending=False)
        + d["Brier Score"].rank(ascending=True)
        + d["Sensitivity"].rank(ascending=False)
        + d["Alert Rate"].rank(ascending=True)
    )
    winner = d["_rank"].idxmin()
    log.info(f"Primary model selected: {winner}  "
             f"(composite rank={d.loc[winner, '_rank']:.1f})")
    return winner


# ---------------------------------------------------------------------------
# 11. Main orchestration
# ---------------------------------------------------------------------------
def main(allow_synthetic_demo=False):
    log.info("=" * 65)
    log.info("  SepsisGuard AI — Model Training and Comparison Pipeline")
    log.info("=" * 65)

    # Data
    dp = "data/processed/aligned_cohort.parquet"
    synthetic_demo = not os.path.exists(dp)
    if synthetic_demo and not allow_synthetic_demo:
        raise FileNotFoundError(
            f"Required labeled cohort is missing: {dp}. "
            "Synthetic demo training requires --allow-synthetic-demo and is not clinical evaluation."
        )
    df = pd.read_parquet(dp) if not synthetic_demo else generate_demo_dataset()
    out_dir = os.path.join("model", "synthetic_demo_candidate" if synthetic_demo else "training_candidate")
    os.makedirs(out_dir, exist_ok=True)

    absent_features = [name for name in FEATURES if name not in df.columns]
    if absent_features:
        raise ValueError(f"Training cohort is missing canonical features: {absent_features}")
    feats = list(FEATURES)
    log.info(f"Feature set: {len(feats)} features — {feats}")

    # Split
    dtr, dv, dte = patient_split(df)

    Xt  = dtr[feats].values;  yt = dtr["label"];  gt = dtr["subject_id"].values
    Xv  = dv[feats].values;   yv = dv["label"]
    Xte = dte[feats].values;  yte = dte["label"].values

    # StandardScaler fit only on TRAIN (Audit 4)
    sc    = StandardScaler()
    Xts   = sc.fit_transform(Xt)
    Xvs   = sc.transform(Xv)
    Xtes  = sc.transform(Xte)
    assert sc.n_samples_seen_ == len(Xt), "Scaler leakage detected!"
    log.info(f"Scaler fit on {sc.n_samples_seen_} TRAIN rows only (Audit 4 passed)")

    # Class imbalance — scale_pos_weight from TRAIN only (Audit 5)
    n_neg = int((yt == 0).sum())
    n_pos = int((yt == 1).sum())
    spw   = n_neg / max(n_pos, 1)
    log.info(f"scale_pos_weight = {n_neg}/{n_pos} = {spw:.2f}  (Audit 5: TRAIN only)")

    # Train
    lrm, lrc, lrt, lrcv  = train_lr(Xts, yt, Xvs, yv, gt)
    xm,  xc,  xt,  xcv   = train_xgboost(Xt, yt, Xv, yv, gt, spw)
    lm,  lc,  lt,  lcv   = train_lightgbm(Xt, yt, Xv, yv, gt)

    meta = {
        "Logistic Regression": {"tt": lrt, "cv": lrcv},
        "XGBoost":             {"tt": xt,  "cv": xcv, "spw": spw},
        "LightGBM":            {"tt": lt,  "cv": lcv},
    }

    # Feature importance (tree models only)
    log.info("\n--- Feature Importance ---")
    plot_feat_imp(xm, feats, "XGBoost", out_dir)
    plot_feat_imp(lm, feats, "LightGBM", out_dir)

    # Select from validation evidence only.  Calibration is fit on this holdout;
    # on a production-sized cohort reserve a separate calibration sub-holdout.
    val_results = []
    for nm, mdl, cal, Xe in [
        ("Logistic Regression", lrm, lrc, Xvs),
        ("XGBoost",             xm,  xc,  Xv),
        ("LightGBM",            lm,  lc,  Xv),
    ]:
        if mdl is None:
            continue
        prob = cal.predict_proba(mdl.predict_proba(Xe)[:, 1])
        val_results.append({"name": nm, "metrics": compute_metrics(yv.values, prob, f"{nm} validation")})
    val_selection_table = build_comparison_table(
        [{"name": r["name"], "metrics": r["metrics"]} for r in val_results], meta
    )
    primary = select_primary(val_selection_table)
    log.info("Primary model frozen from validation evidence before test evaluation: %s", primary)

    # Test evaluation — TEST SET TOUCHED ONCE, after selection is frozen
    log.info("\n--- Test Set Evaluation (FINAL) ---")
    results = []
    for nm, mdl, cal, Xe in [
        ("Logistic Regression", lrm, lrc, Xtes),
        ("XGBoost",             xm,  xc,  Xte),
        ("LightGBM",            lm,  lc,  Xte),
    ]:
        if mdl is None:
            continue
        raw  = mdl.predict_proba(Xe)[:, 1]
        prob = cal.predict_proba(raw)
        met  = compute_metrics(yte, prob, nm)
        results.append({"name": nm, "proba": prob, "metrics": met})

    # Plots
    log.info("\n--- Generating Plots ---")
    plot_roc_pr(results, yte, out_dir)
    plot_calibration(results, yte, out_dir)

    # Comparison table
    cdf = build_comparison_table(results, meta)
    csv_path = os.path.join(out_dir, "model_comparison.csv")
    cdf.to_csv(csv_path)
    log.info(f"\nModel Comparison:\n{cdf.to_string()}")
    log.info(f"Comparison table saved: {csv_path}")

    # Primary model selection was already performed on validation evidence.
    log.info(f"\n{'=' * 65}")
    log.info(f"  PRIMARY MODEL: {primary}")
    log.info(f"{'=' * 65}")

    # Save artifacts
    joblib.dump(sc,  os.path.join(out_dir, "scaler.pkl"))
    joblib.dump(lrm, os.path.join(out_dir, "lr_model.pkl"))
    joblib.dump(lrc, os.path.join(out_dir, "lr_calibrator.pkl"))
    xm.get_booster().save_model(os.path.join(out_dir, "xgb_model.json"))
    joblib.dump(xc,  os.path.join(out_dir, "xgb_calibrator.pkl"))
    if lm is not None:
        lm.booster_.save_model(os.path.join(out_dir, "lgb_model.txt"))
        joblib.dump(lc,  os.path.join(out_dir, "lgb_calibrator.pkl"))

    decision = {
        "primary_model": primary,
        "alert_threshold": ALERT_THRESHOLD,
        "selection_criteria": [
            "1. AUPRC (primary — most informative for imbalanced tasks)",
            "2. Brier Score (calibration quality, lower is better)",
            "3. Sensitivity (missed sepsis >> alert fatigue clinically)",
            "4. Alert Rate (ICU nursing operational burden)",
        ],
        "selection_split": "validation only (test excluded from all selection decisions)",
        "validation_metrics_used_for_selection": {
            r["name"]: {k: v for k, v in r["metrics"].items() if k != "model"}
            for r in val_results
        },
        "test_metrics": {
            r["name"]: {k: v for k, v in r["metrics"].items() if k != "model"}
            for r in results
        },
    }
    dec_path = os.path.join(out_dir, "model_selection_decision.json")
    with open(dec_path, "w") as f:
        json.dump(decision, f, indent=2)
    log.info(f"Decision record saved: {dec_path}")
    log.info("Pipeline complete.")
    return primary, cdf


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train an ARGUS model candidate.")
    parser.add_argument(
        "--allow-synthetic-demo", action="store_true",
        help="Explicitly train a synthetic demonstration candidate; not clinical evaluation.",
    )
    args = parser.parse_args()
    primary, cdf = main(allow_synthetic_demo=args.allow_synthetic_demo)
