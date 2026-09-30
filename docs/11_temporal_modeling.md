# SepsisGuard AI: Temporal Model Component

## Scope and decision rule

`src/pipeline/06_train_temporal_models.py` evaluates a GRU, LSTM, and Temporal
Convolutional Network (TCN) on the same patient-level cohort as the tabular
benchmark. Model selection is frozen from validation evidence; test metrics are
final reporting only. A temporal model is not adopted merely because it is more
expressive: it must improve calibrated validation AUPRC and operational alert
burden over XGBoost before external validation.

## Input representation

| Design element | Choice | Reason |
|---|---|---|
| Sequence length | 6 hourly bins | Matches the six-hour prediction horizon while retaining a recent physiologic trajectory. |
| Anchor | Each prediction hour, right aligned | Every input ends at the prediction time; later rows never enter the sequence. |
| Variables | HR, MAP, RR, SpO2, temperature, lactate missingness, time since lactate | Directly observed multivariate ICU trajectory. More variables can be added only when their timestamps meet the same causal contract. |
| Missingness | Value + mask + time-since-observed channels | Lets the model distinguish a normal value from an imputed or padded value. |
| Imputation | Causal forward-fill; train-set mean before first observation | Never backfills from a future measurement. |
| Padding | Left `NaN`, encoded as missing | Supports early ICU predictions without dropping patients. |
| Normalization | Mean/SD fit on train windows only | Prevents validation/test distribution leakage. |

The final tensor shape is `[windows, 6, 3 × variables]`: normalized causal
values, missingness indicators, and time-since-observation values.

## Split, calibration, and leakage controls

Patients—not ICU windows—are split 70/15/15 into train/validation/test. The
validation patients are then split once more, by patient, into an early-stopping
subset and a calibration subset. Training uses only train patients; early
stopping monitors AUPRC on its validation role; Platt scaling fits on the other
validation role. Test patients are evaluated only after this procedure is
frozen. Assertions reject any patient intersection between the four roles.

For real data, time aggregation must enforce `charttime < prediction_time`.
The window builder sorts each patient's data forward in time and only slices
rows at or before its anchor. Labels remain the six-hour pre-onset labels
defined in the cohort builder; no onset, antibiotic, culture, or future
treatment feature is input.

## Architectures and regularization

| Model | Encoder | Regularization / fit controls |
|---|---|---|
| GRU | Two-layer, 48 hidden units | Dropout 0.25, AdamW weight decay 1e-4, gradient clipping, patience 8. |
| LSTM | Two-layer, 48 hidden units | Same controls; evaluated because its explicit cell state can retain longer trends. |
| TCN | Causal dilated convolutions (1, 2, 4) | Residual blocks, dropout 0.25, AdamW, gradient clipping, patience 8. |

All use `BCEWithLogitsLoss(pos_weight=n_negative_train/n_positive_train)`,
calculated only from training labels. Maximum training is 60 epochs; the
validation AUPRC checkpoint is restored, limiting overfitting.

## Why no temporal transformer

The demo cohort contains 300 independent patients and the sequence has only
six time steps. With this data-to-capacity ratio a transformer is unlikely to
be a defensible comparison: attention has little long-range context to exploit
and introduces an overfitting and computational-cost risk. Reconsider it only
with a substantially larger, externally varied cohort and longer validated
sequences, after GRU/TCN fail to capture a clinically meaningful signal.

## Outputs and comparison

Running the temporal pipeline produces:

| File | Contents |
|---|---|
| `model/temporal_model_comparison.csv` | GRU/LSTM/TCN test metrics, validation AUPRC, training cost, calibration, imbalance, and clinical-use fields. |
| `model/tabular_vs_temporal_comparison.csv` | The same output with the frozen XGBoost tabular reference when its comparison artifact exists. |
| `model/temporal_model_selection.json` | Validation-only temporal recommendation and deployment gate. |
| `model/gru_temporal.pt`, `lstm_temporal.pt`, `tcn_temporal.pt` | Encoder weights plus representation metadata. |
| `logs/06_train_temporal_models.log` | Run log. |

At the shared alert threshold (0.35), report AUROC, AUPRC, Brier score,
sensitivity, specificity, PPV, NPV, alert rate, and false-alert percentage.
Compare inference/training cost, attribution burden, calibration, and alerts per
clinical workflow—not only AUROC. The existing tabular `model_comparison.csv`
provides the Logistic Regression/XGBoost/LightGBM comparison with feature-gain
plots for both tree models.
