"""SepsisGuard temporal-model benchmark.

This module intentionally compares only three compact sequence encoders (GRU,
LSTM, and dilated TCN).  A transformer is excluded: the demo cohort has only
300 patients and 6 hourly steps/window, where self-attention adds parameters
without enough independent patient trajectories to justify it.

Protocol
--------
* Patient-disjoint 70/15/15 train/validation/test split.
* The validation patients are split again by patient into early-stopping and
  calibration sets.  Thus calibration never learns from an early-stopping
  score and neither process sees test patients.
* Values are forward-filled causally *within* each sequence; no value at t+k
  is used at t.  Missingness masks and time-since-observation channels remain
  visible to the models.
* Normalisation, BCE positive weight, threshold choice, and all architecture
  decisions are derived without test data.

Run after 05_train_models.py so model/model_comparison.csv can provide the
same-split XGBoost reference for the final combined comparison.
"""
import importlib.util
import json
import logging
import os
import random
import time

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import GroupShuffleSplit
from scipy.optimize import minimize
from scipy.special import expit

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except ImportError as exc:  # makes the module importable in non-DL environments
    raise RuntimeError("Temporal training requires PyTorch; install a CPU or CUDA build.") from exc

SEED = 42
WINDOW_HOURS = 6
ALERT_THRESHOLD = 0.35
BASE_FEATURES = ("hr_curr", "map_curr", "rr_curr", "spo2_curr", "temp_curr",
                 "lactate_missing", "time_since_lactate")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.set_num_threads(min(4, os.cpu_count() or 1))


def _load_tabular_module():
    """Load the numbered pipeline without relying on an invalid Python identifier."""
    path = os.path.join(os.path.dirname(__file__), "05_train_models.py")
    spec = importlib.util.spec_from_file_location("sepsisguard_tabular", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def set_seed():
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)


def patient_split_with_val_roles(frame):
    """Patient split and patient-disjoint early-stop/calibration validation roles."""
    split = GroupShuffleSplit(n_splits=1, test_size=.30, random_state=SEED)
    tr_idx, hold_idx = next(split.split(frame, groups=frame.subject_id))
    train, hold = frame.iloc[tr_idx].copy(), frame.iloc[hold_idx].copy()
    split2 = GroupShuffleSplit(n_splits=1, test_size=.50, random_state=SEED)
    va_idx, te_idx = next(split2.split(hold, groups=hold.subject_id))
    val, test = hold.iloc[va_idx].copy(), hold.iloc[te_idx].copy()
    split3 = GroupShuffleSplit(n_splits=1, test_size=.50, random_state=SEED + 1)
    es_idx, cal_idx = next(split3.split(val, groups=val.subject_id))
    early, calibration = val.iloc[es_idx].copy(), val.iloc[cal_idx].copy()
    parts = (train, early, calibration, test)
    ids = [set(x.subject_id) for x in parts]
    assert all(not (ids[i] & ids[j]) for i in range(4) for j in range(i)), "patient leakage"
    return parts


def make_windows(frame, feature_names=BASE_FEATURES, sequence_length=WINDOW_HOURS):
    """Create right-aligned, causal hourly windows ending at each prediction time.

    Input has shape [windows, six hours, variables].  Early ICU windows are
    left-padded with NaNs; the padding becomes an explicit missingness channel.
    No rows after the prediction anchor can enter a window.
    """
    xs, ys, groups = [], [], []
    for patient, g in frame.groupby("subject_id", sort=False):
        g = g.sort_values("hour")
        values = g.loc[:, feature_names].astype(float).to_numpy()
        labels = g.label.to_numpy(dtype=np.float32)
        for end in range(len(g)):
            start = max(0, end - sequence_length + 1)
            w = np.full((sequence_length, len(feature_names)), np.nan, dtype=np.float32)
            observed = values[start:end + 1]
            w[-len(observed):] = observed
            xs.append(w); ys.append(labels[end]); groups.append(patient)
    return np.asarray(xs), np.asarray(ys), np.asarray(groups)


class CausalRepresentation:
    """Train-fitted causal imputation + value/mask/delta representation."""
    def fit(self, x):
        raw = x.reshape(-1, x.shape[-1])
        means = np.nanmean(raw, axis=0)
        self.means_ = np.where(np.isfinite(means), means, 0.).astype(np.float32)
        filled, _, _ = self._causal_fill(x)
        self.mean_ = filled.reshape(-1, filled.shape[-1]).mean(0).astype(np.float32)
        self.std_ = np.maximum(filled.reshape(-1, filled.shape[-1]).std(0), 1e-6).astype(np.float32)
        return self

    def _causal_fill(self, x):
        mask = ~np.isfinite(x)
        out = np.empty_like(x, dtype=np.float32)
        delta = np.zeros_like(x, dtype=np.float32)
        for n in range(len(x)):
            last = self.means_.copy()
            since = np.zeros(x.shape[-1], dtype=np.float32)
            for t in range(x.shape[1]):
                observed = ~mask[n, t]
                last[observed] = x[n, t, observed]
                since[observed] = 0.
                since[~observed] += 1.
                out[n, t] = last; delta[n, t] = since
        return out, mask.astype(np.float32), delta

    def transform(self, x):
        values, mask, delta = self._causal_fill(x)
        z = (values - self.mean_) / self.std_
        # Channels: normalized values, missing/padding indicator, time-since.
        return np.concatenate((z, mask, delta), axis=-1).astype(np.float32)


class RecurrentNet(nn.Module):
    def __init__(self, input_dim, kind, hidden=48, dropout=.25):
        super().__init__()
        cls = nn.GRU if kind == "gru" else nn.LSTM
        self.encoder = cls(input_dim, hidden, batch_first=True, dropout=dropout, num_layers=2)
        self.head = nn.Sequential(nn.LayerNorm(hidden), nn.Dropout(dropout), nn.Linear(hidden, 1))

    def forward(self, x):
        seq, _ = self.encoder(x)
        return self.head(seq[:, -1]).squeeze(-1)


class TemporalBlock(nn.Module):
    def __init__(self, channels, dilation, dropout):
        super().__init__()
        # Padding is trimmed after *each* convolution.  Trimming only after a
        # two-convolution block would allow the second convolution to inspect
        # future positions produced by the first one.
        self.pad = 2 * dilation
        self.conv1 = nn.Conv1d(channels, channels, 3, padding=self.pad, dilation=dilation)
        self.conv2 = nn.Conv1d(channels, channels, 3, padding=self.pad, dilation=dilation)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        y = self.dropout(torch.relu(self.conv1(x)[..., :x.shape[-1]]))
        y = self.dropout(torch.relu(self.conv2(y)[..., :x.shape[-1]]))
        return torch.relu(x + y)


class TCN(nn.Module):
    def __init__(self, input_dim, hidden=48, dropout=.25):
        super().__init__()
        self.input = nn.Conv1d(input_dim, hidden, 1)
        self.blocks = nn.Sequential(TemporalBlock(hidden, 1, dropout), TemporalBlock(hidden, 2, dropout),
                                    TemporalBlock(hidden, 4, dropout))
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(hidden, 1))

    def forward(self, x):
        z = self.blocks(self.input(x.transpose(1, 2)))
        return self.head(z[..., -1]).squeeze(-1)


class PlattCalibrator:
    def fit(self, p, y):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        scores = np.log(p / (1 - p))
        def loss(v):
            q = np.clip(expit(v[0] * scores + v[1]), 1e-6, 1 - 1e-6)
            return -(y * np.log(q) + (1 - y) * np.log(1 - q)).mean()
        self.a_, self.b_ = minimize(loss, (1., 0.), method="L-BFGS-B").x
        return self
    def predict(self, p):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return expit(self.a_ * np.log(p / (1 - p)) + self.b_)


def predict(model, x):
    model.eval(); output = []
    with torch.no_grad():
        for (batch,) in DataLoader(TensorDataset(torch.from_numpy(x)), batch_size=1024):
            output.append(torch.sigmoid(model(batch.to(DEVICE))).cpu().numpy())
    return np.concatenate(output)


def train_model(kind, x_train, y_train, x_early, y_early):
    """Weighted BCE, dropout/weight decay, and validation-only early stopping."""
    model = (TCN(x_train.shape[-1]) if kind == "tcn" else RecurrentNet(x_train.shape[-1], kind)).to(DEVICE)
    pos_weight = torch.tensor([(y_train == 0).sum() / max((y_train == 1).sum(), 1)], device=DEVICE)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loader = DataLoader(TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train)),
                        batch_size=512, shuffle=True)
    best, best_state, stale = -np.inf, None, 0
    start = time.time()
    for epoch in range(1, 61):
        model.train()
        for xb, yb in loader:
            opt.zero_grad(); loss = loss_fn(model(xb.to(DEVICE)), yb.to(DEVICE)); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
        score = average_precision_score(y_early, predict(model, x_early))
        if score > best + 1e-4:
            best, stale = score, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= 8: break
    model.load_state_dict(best_state)
    return model, {"early_stop_auprc": float(best), "epochs": epoch, "train_seconds": time.time() - start,
                   "pos_weight": float(pos_weight.item())}


def metrics(y, p):
    q = (p >= ALERT_THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, q, labels=[0, 1]).ravel()
    return {"AUROC": roc_auc_score(y, p), "AUPRC": average_precision_score(y, p), "Brier Score": brier_score_loss(y, p),
            "Sensitivity": tp / max(tp + fn, 1), "Specificity": tn / max(tn + fp, 1),
            "PPV": tp / max(tp + fp, 1), "NPV": tn / max(tn + fn, 1),
            "Alert Rate": (tp + fp) / len(y), "False Alert %": 100 * fp / max(fp + tn, 1)}


def main():
    set_seed(); os.makedirs("model", exist_ok=True); os.makedirs("logs", exist_ok=True)
    logging.basicConfig(filename="logs/06_train_temporal_models.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    tabular = _load_tabular_module()
    data_path = "data/processed/aligned_cohort.parquet"
    frame = pd.read_parquet(data_path) if os.path.exists(data_path) else tabular.generate_demo_dataset()
    missing = set(BASE_FEATURES) - set(frame)
    if missing: raise ValueError(f"Temporal input is missing required columns: {sorted(missing)}")
    train, early, calibration, test = patient_split_with_val_roles(frame)
    train_x, train_y, _ = make_windows(train); early_x, early_y, _ = make_windows(early)
    cal_x, cal_y, _ = make_windows(calibration); test_x, test_y, _ = make_windows(test)
    rep = CausalRepresentation().fit(train_x)
    train_x, early_x, cal_x, test_x = (rep.transform(z) for z in (train_x, early_x, cal_x, test_x))
    reports, models = {}, {}
    for kind, title in (("gru", "GRU"), ("lstm", "LSTM"), ("tcn", "TCN")):
        model, meta = train_model(kind, train_x, train_y, early_x, early_y)
        calibrator = PlattCalibrator().fit(predict(model, cal_x), cal_y)
        cal_metric = metrics(cal_y, calibrator.predict(predict(model, cal_x)))
        test_metric = metrics(test_y, calibrator.predict(predict(model, test_x)))  # one final test pass/model
        reports[title] = {**test_metric, **meta, "Validation AUPRC": cal_metric["AUPRC"],
                          "Validation Brier Score": cal_metric["Brier Score"],
                          "Calibration": "Platt on patient-disjoint validation calibration split",
                          "Interpretability": "Low/medium — sequence attribution required",
                          "Clinical usefulness": "Only if validation gain exceeds tabular model",
                          "Imbalance": f"BCE pos_weight={meta['pos_weight']:.1f}"}
        models[title] = model
        torch.save({"state_dict": model.state_dict(), "features": BASE_FEATURES, "window_hours": WINDOW_HOURS,
                    "representation": rep}, f"model/{title.lower()}_temporal.pt")
    temporal = pd.DataFrame(reports).T
    temporal.to_csv("model/temporal_model_comparison.csv")
    # XGBoost comparison is intentionally read from the separately frozen tabular evaluation.
    tab_path = "model/model_comparison.csv"
    combined = temporal.copy()
    if os.path.exists(tab_path):
        xgb = pd.read_csv(tab_path).set_index("Model").loc[["XGBoost"]]
        xgb["Clinical usefulness"] = "Reference tabular model"
        combined = pd.concat((xgb, temporal), sort=False)
    combined.to_csv("model/tabular_vs_temporal_comparison.csv")
    # Recommendation uses calibration-validation AUPRC and Brier, never test metrics.
    winner = temporal.sort_values(["Validation AUPRC", "Validation Brier Score"], ascending=[False, True]).index[0]
    decision = {"recommended_temporal_model": winner, "selection_evidence": "patient-disjoint validation calibration split",
                "transformer": "Not evaluated: short sequences and 300-patient demo cohort do not justify its capacity.",
                "deployment_gate": "Adopt only if external validation improves calibrated AUPRC and alert burden over XGBoost.",
                "sequence_design": {"hours": WINDOW_HOURS, "channels": "values + missingness mask + time-since", "normalization": "train-only", "padding": "left NaN with mask"}}
    with open("model/temporal_model_selection.json", "w") as f: json.dump(decision, f, indent=2)
    print(combined.round(4).to_string())
    print("Temporal recommendation (validation evidence only):", winner)
    return combined, decision


if __name__ == "__main__":
    main()
