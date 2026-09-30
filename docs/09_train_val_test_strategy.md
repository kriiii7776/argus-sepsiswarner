# SepsisGuard AI: Complete Train/Validation/Test Strategy

Ordinary random row splitting (e.g., standard `train_test_split`) is mathematically disastrous in continuous ICU time-series data due to massive autocorrelation between adjacent temporal windows. This document codifies the rigorous data partitioning strategy required for SepsisGuard AI.

---

## 1. Evaluation of Splitting Strategies

### 1.1 ICU-Stay-Level Splitting
*   **Method:** Splitting based on `stay_id`.
*   **Risk:** **High Leakage.** Patients often have multiple ICU stays (`stay_id`s) under the same `subject_id`. Their underlying physiology, chronic conditions, and genetic responses to infection will leak if Stay A is in Train and Stay B is in Test.
*   **Decision:** Prohibited.

### 1.2 Patient-Level Splitting (Grouped)
*   **Method:** Splitting based entirely on `subject_id`.
*   **Risk:** Low. Ensures complete biological independence between partitions.
*   **Decision:** **Mandatory Minimum Requirement.** All splits *must* group by `subject_id`.

### 1.3 Temporal Splitting (Out-of-Time Holdout)
*   **Method:** Splitting based on admission dates (e.g., Train: 2008-2015 $\rightarrow$ Val: 2016-2018 $\rightarrow$ Test: 2019).
*   **Risk:** Exposes the model to distribution shifts (e.g., changes in sepsis guidelines or EHR systems over time).
*   **Decision:** **The Gold Standard.** While the ~100 patient MIMIC-IV Demo is too small to support this, the final production model *must* use a temporal out-of-time holdout.

### 1.4 Grouped Cross-Validation
*   **Method:** `GroupKFold` using `subject_id`.
*   **Decision:** Used strictly during hyperparameter tuning on the Training set. Not used for final evaluation.

---

## 2. Primary Configuration (The SepsisGuard Split)

For the final evaluation on the full MIMIC-IV dataset, we merge Patient-Level and Temporal Splitting:

1.  **TRAIN (70%):** Historical admissions (e.g., Years 1-7). Used to fit all parameters, weights, and preprocessing objects.
2.  **VALIDATION (15%):** Sequential subsequent admissions (e.g., Years 8-9). Used for early stopping, hyperparameter tuning, and threshold calibration.
3.  **TEST (15%):** Future holdout admissions (e.g., Year 10). Strictly locked until the final model architecture is frozen. Evaluates true generalization to future patients.

*Constraint: If an individual patient has admissions spanning the temporal cutoffs, all of their admissions are forced into the partition of their earliest admission (Train) to prevent reverse-temporal leakage.*

---

## 3. Strict Preprocessing Isolation Rules

To prevent **preprocessing leakage**, no calculation that aggregates global distributions can see the Validation or Test sets.

*   **Scaling/Normalization:** If using neural networks or regularized regression, `StandardScaler` or `MinMaxScaler` is `.fit()` **only** on TRAIN. `.transform()` is applied to VAL and TEST.
*   **Imputation:** Global mean/median imputation (if used for baselines) is calculated **only** on TRAIN.
*   **Feature Selection:** Variance thresholding or LASSO selection is run **only** on TRAIN.
*   **Class Weighting:** `scale_pos_weight` or `class_weight='balanced'` is calculated using the positive/negative ratio of TRAIN **only**.

---

## 4. Leakage Prevention Mechanisms

1.  **Patient Leakage:** Solved by `GroupShuffleSplit` on `subject_id`.
2.  **ICU-Stay Leakage:** Implicitly solved by patient-level splitting.
3.  **Overlapping-Window Leakage:** Prevented by Strategy A (from Phase 3), which extracts exactly one non-overlapping positive window per patient, preventing correlated labels.
4.  **Future-Information Leakage:** Prevented by the strict 6-hour exclusion horizon and the prohibition of `bfill` (backward filling) in the time-series representation.
5.  **Label Leakage:** Prevented by excluding culture orders, antibiotic administrations, and vasopressors from the feature space.
6.  **Hyperparameter Tuning Leakage:** Solved by executing all grid searches using `GroupKFold` strictly confined to the TRAIN partition. The TEST partition is never accessed during tuning.

---

## 5. Formal Leakage Audit Checklist

Before evaluating the final model on the TEST partition, the lead ML Engineer must execute this audit script:

*   [ ] **Audit 1 (Intersection):** `len(set(train_patients).intersection(set(test_patients))) == 0`
*   [ ] **Audit 2 (Leakage Features):** Assert that no column in the feature matrix contains `culture`, `antibiotic`, `abx`, `vaso`, `norepi`, or `lactate` (if lactate was deemed too leaky by clinical consensus).
*   [ ] **Audit 3 (Future Peeking):** Assert that no value in the observation tensor has a timestamp $\ge (t_{sepsis} - \text{Horizon})$.
*   [ ] **Audit 4 (Scaler Isolation):** Assert that `scaler.n_samples_seen_` exactly equals the number of rows in the TRAIN partition.
*   [ ] **Audit 5 (Class Weight Validation):** Manually recalculate the `scale_pos_weight` parameter used in the XGBoost config and verify it maps exactly to the TRAIN positive/negative distribution, completely independent of TEST.
