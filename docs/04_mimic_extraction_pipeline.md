# SepsisGuard AI: Complete MIMIC-IV Extraction Pipeline

## 1. Project Directory Structure
A strictly reproducible pipeline requires a standardized directory layout.

```text
Argus/
├── data/
│   ├── raw/                 # Unaltered MIMIC-IV CSV files
│   ├── interim/             # Cleaned, unit-normalized, unfiltered tables
│   ├── processed/           # Final aligned, temporal features (model-ready)
│   ├── config.yaml          # Pipeline hyperparameters and schema definitions
│   └── sql/                 # Raw SQL extraction scripts
├── src/
│   ├── pipeline/
│   │   ├── extractor.py     # SQL execution and chunked reading
│   │   ├── normalizer.py    # Unit conversion and outlier removal
│   │   ├── aligner.py       # Time-series binning and ICU alignment
│   │   └── validator.py     # Data quality checks
│   └── pipeline_runner.py   # Main orchestration script
├── logs/                    # Pipeline execution logs
└── docs/                    # Dictionaries and architecture
```

## 2. Configuration File Design (`config.yaml`)
Externalizing parameters prevents hard-coding and ensures reproducibility.

```yaml
pipeline:
  version: "1.0.0"
  random_seed: 42
data:
  raw_path: "data/raw/"
  processed_path: "data/processed/"
normalization:
  temp_c_min: 30.0
  temp_c_max: 45.0
  hr_min: 0
  hr_max: 300
features:
  observation_window_hrs: 4
  prediction_horizon_hrs: 6
  imputation_limit_hrs: 4
# Mappings MUST be verified against local d_items
item_mappings:
  heart_rate: [220045]
  map: [220181, 220052]
  temp_c: [223761]
  temp_f: [223762]
```

## 3. The Extraction Strategy (SQL vs Python)
*   **SQL Phase:** Heavy lifting (joining `chartevents` to `icustays`, filtering out non-ICU data).
*   **Python Phase:** Complex temporal logic (binning, hybrid missingness, calculating slopes, validation).

## 4. Pipeline Stages

### Step 1: Table Extraction (SQL)
*   **Input:** Raw `chartevents`, `icustays`, `labevents`
*   **Action:** Join tables to filter data exclusively to ICU limits (`intime` to `outtime`).
*   **Output:** `interim/icu_events.parquet`
*   **Validation:** Check row counts > 0.
*   **Error Handling:** Catch SQL syntax errors; abort pipeline.

### Step 2: Unit Normalization
*   **Input:** `interim/icu_events.parquet`
*   **Action:** Convert known diverging units.
    *   `IF itemid == {temp_f} THEN (valuenum - 32) * 5/9`
    *   `IF itemid == {weight_lbs} THEN valuenum * 0.453592`
*   **Output:** Memory dataframe.
*   **Validation:** Ensure no Farenheit ranges exist after conversion.

### Step 3: Physiologically Implausible Value Handling
*   **Action:** Remove known artifact outliers (sensor errors).
    *   `Heart Rate < 0 OR > 300` $\rightarrow$ set to `NaN`
    *   `MAP < 10 OR > 300` $\rightarrow$ set to `NaN`
*   **Validation:** Assert `df['heart_rate'].max() <= 300`.
*   **Logging:** Log the percentage of values dropped per variable. If $>5\%$, trigger a `DataQualityWarning`.

### Step 4: Timestamp Normalization & Duplicate Handling
*   **Action:** Round `charttime` to the nearest hour. If multiple measurements exist in the same hour for the same `itemid`, take the `mean()` (or `max()` depending on clinical relevance).
*   **Output:** 1-hour binned intermediate dataframe.

### Step 5: Patient Filtering & ICU Alignment
*   **Action:** Apply the Temporal Sepsis-Label Strategy (Phase 3). Drop patients with ICU stays $< 10$ hours. Align timestamps relative to $t_{sepsis}$ for positive patients.
*   **Output:** `processed/aligned_cohort.parquet`

## 5. Reproducibility & Logging Strategy
*   **Logging:** Use Python's `logging` module. Write to `logs/pipeline_{timestamp}.log`. Log every configuration parameter, input/output row counts for every step, and the random seed.
*   **Reproducibility:** The `config.yaml` is version-controlled. Output files are hashed (MD5) to track dataset drift.

---
*See `data/pipeline_runner.py` for the implementation skeleton.*
