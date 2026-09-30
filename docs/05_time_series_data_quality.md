# SepsisGuard AI: Clinical Time-Series Data Quality Pipeline

To ensure the model learns true physiological deterioration rather than data artifacts, we enforce a strict time-series data quality pipeline. 

**Core Principle:** We differentiate *true physiological extremes* (e.g., HR = 180 in shock) from *measurement artifacts* (e.g., HR = 300 due to a sensor disconnect). Extremes are kept; artifacts are removed.

---

## 1. Preprocessing Methods & Risks

### 1.1 Missing Values
*   **Method:** explicit missingness indicators (e.g., `HR_missing = 1`) and `time_since_measurement`. Global mean imputation is reserved strictly for models that cannot handle NaNs natively (like Logistic Regression) and is calculated only on the training set.
*   **Why Necessary:** Missingness in the ICU is not random. It is often driven by clinical protocol or suspicion.
*   **Clinical Risk:** Ignoring missingness hides the clinician's attention level from the model.
*   **Statistical Risk:** Overestimating the confidence of predictions based on sparse data.
*   **Leakage Risk:** Global mean imputation causes leakage if calculated before splitting.
*   **When to Apply:** Missing indicators/time-since applied **before** splitting (patient-isolated). Global imputation applied **after** splitting.

### 1.2 Duplicate Observations
*   **Method:** Retain the first entry based on standard timestamps; if identical, keep the row with the most complete data across other columns.
*   **Why Necessary:** Data entry errors often result in double-charting.
*   **Clinical Risk:** None.
*   **Statistical Risk:** Inflates the apparent sample size of observation windows.
*   **Leakage Risk:** None.
*   **When to Apply:** **Before** splitting.

### 1.3 Conflicting Observations
*   **Method:** If two highly divergent values (e.g., HR=60 and HR=140) are recorded at the exact same minute, drop both for that specific minute and treat as missing, rather than averaging them, as one is likely an artifact.
*   **Why Necessary:** Averages of conflicting artifacts create fake physiological states.
*   **Clinical Risk:** Blinding the model to a true sudden change if we aggressively drop them.
*   **Statistical Risk:** Introducing synthetic mean values that don't exist in reality.
*   **Leakage Risk:** None.
*   **When to Apply:** **Before** splitting.

### 1.4 Irregular Sampling & 1.12 Sparse Measurements
*   **Method:** Resample data into fixed 1-hour bins using the mean value within the hour.
*   **Why Necessary:** Tree-based models require fixed-width feature vectors.
*   **Clinical Risk:** Blurring high-frequency crises (e.g., a 5-minute desaturation event).
*   **Statistical Risk:** Smoothing out variance.
*   **Leakage Risk:** None.
*   **When to Apply:** **Before** splitting.

### 1.5 Physiologically Impossible Values & 1.6 Sensor Artifacts
*   **Method:** Hard physiological clamping (e.g., set HR < 20 or > 250 to `NaN`; set MAP < 10 or > 200 to `NaN`). Do *not* use statistical bounds (like removing the top 1% of values).
*   **Why Necessary:** To distinguish sensor disconnects/flushes from septic shock.
*   **Clinical Risk:** Accidentally removing true extremes if bounds are set too conservatively.
*   **Statistical Risk:** None; improves model robustness.
*   **Leakage Risk:** Using global statistical percentiles (e.g., 99th) before splitting causes leakage. Hard physiological limits do not.
*   **When to Apply:** **Before** splitting.

### 1.7 Measurement Delays
*   **Method:** Use the `charttime` (when it was charted), not the `storetime` (when it was entered into the database).
*   **Why Necessary:** `storetime` can be hours later, especially during shift changes.
*   **Clinical Risk:** The model might learn to expect data that a real-time system won't have yet.
*   **Statistical Risk:** None.
*   **Leakage Risk:** Using `storetime` might inadvertently leak future information if batch-entered.
*   **When to Apply:** **Before** splitting.

### 1.8 Different Units & 1.9 Laboratory Reference Differences
*   **Method:** Standardize units (Fahrenheit $\rightarrow$ Celsius, lbs $\rightarrow$ kg). For labs, use raw values but ensure `itemid` mappings cover all historical hospital iterations of the same lab test.
*   **Why Necessary:** Without standardization, the model perceives bimodal distributions.
*   **Clinical Risk:** Missing a fever if 101F is interpreted as 101C (fatal artifact).
*   **Statistical Risk:** Creates fake variance.
*   **Leakage Risk:** None.
*   **When to Apply:** **Before** splitting.

### 1.10 Carry-Forward Measurements & 1.11 Interpolation
*   **Method:** Forward-fill (`ffill`) vitals with a strict limit (e.g., 4 hours). Do not back-fill (`bfill`). Do not linearly interpolate. Do not forward-fill labs.
*   **Why Necessary:** Clinical measurements are assumed stable over short periods.
*   **Clinical Risk:** Carrying a normal HR forward into a period where the patient actually crashed.
*   **Statistical Risk:** Underestimating variance.
*   **Leakage Risk:** `bfill` or linear interpolation uses future data to fill past gaps, causing massive temporal leakage.
*   **When to Apply:** **Before** splitting (since it looks only backward within a single patient timeline, it does not leak global data).

### 1.13 ICU Admission/Discharge Boundaries
*   **Method:** Hard filter: Only accept `charttime` where `intime` $\le$ `charttime` $\le$ `outtime`.
*   **Why Necessary:** Ward data or pre-admission ED data operates under different clinical protocols and sampling frequencies.
*   **Clinical Risk:** Confusing ward stability with ICU instability.
*   **Statistical Risk:** Distribution shifts in the data.
*   **Leakage Risk:** None.
*   **When to Apply:** **Before** splitting.

---

## 2. Automated Data-Quality Tests (Expectations)
These tests run in `validator.py` and halt the pipeline if they fail:
1.  **Strict Chronology:** `Assert(df.groupby('stay_id')['charttime'].is_monotonic_increasing)`
2.  **No Leakage Interpolation:** `Assert(count(bfill_artifacts) == 0)`
3.  **Physiological Bounds:** `Assert(df['heart_rate'].between(20, 250).all(skipna=True))`
4.  **No Unmapped Units:** `Assert(df['itemid'].isin(approved_unit_mapping_list))`
5.  **Patient Independence:** `Assert(train_patients.intersection(test_patients).empty)`

---

## 3. Data Quality Report Template
Generated dynamically after Phase 1 and 2 of the extraction pipeline:

```text
=================================================
SEPSISGUARD AI - DATA QUALITY & COHORT REPORT
=================================================
Timestamp: 2026-09-29 10:00:00 UTC
Dataset Version: MIMIC-IV Demo v2.2

[ 1. COHORT SUMMARY ]
Total Unique Patients:          XYZ
Total ICU Stays:                XYZ
Total Positive Sepsis Events:   XYZ
Total Negative Stays:           XYZ

[ 2. MEASUREMENT DENSITY & FREQUENCY ]
Average Observations / Stay:    XYZ
Median Time Between Vitals:     XYZ mins
Median Time Between Labs:       XYZ hours

[ 3. ARTIFACT & OUTLIER HANDLING ]
Invalid/Implausible Dropped:    XYZ rows (X.X%)
Duplicate Rows Dropped:         XYZ rows (X.X%)
Conflicting Timestamps Handled: XYZ instances

[ 4. MISSINGNESS (Post-Clamping, Pre-Imputation) ]
Heart Rate:    XX.X%
MAP:           XX.X%
SpO2:          XX.X%
Temperature:   XX.X%
Lactate:       XX.X% (Expected High)
Creatinine:    XX.X% (Expected High)

[ 5. VALIDATION STATUS ]
Chronology Test:        PASSED
Leakage Test (bfill):   PASSED
Boundary Test:          PASSED
=================================================
```
