# ARGUS Fix and Validation Report

Date: 2026-10-02  
Repository: `argus-sepsiswarner`  
Branch: `feature/argus-part2-phase7b`  
Baseline commit: `29c18fc9283d7c326307147896a0d2b4c23fb3d4`

## Executive result

**Final status: NOT READY.** The stack now runs on PostgreSQL after a guarded, row-verified migration from the live SQLite database; four simulator patients have produced independent live records and WebSocket messages. The Android APK built and installed; after the user unlocked the phone, the dashboard visibly showed all four patients as live and their detail page rendered model contributors. However, detail view showed `Latest vitals unavailable`, and native urgent notification behavior was not confirmed. The clinical cohort and official derived labels are still absent, and the legacy Logistic Regression artifact's training provenance is unverified. No valid patient-disjoint clinical performance or calibration metrics can be reported.

No model was replaced, retrained, or silently relabeled. No clinical labels or model-performance metrics were fabricated. No commit or push was made.

## 1. Fixes implemented

| Area | Change | Validation |
|---|---|---|
| Risk parsing | `risk_probability` remains nullable and is rejected when nonnumeric, nonfinite, or outside `[0,1]`; absent/null is not converted to zero. | Flutter model tests pass. |
| Risk display | Added a shared formatter: two decimal places for ordinary risks; positive probabilities below 0.01% display as `<0.01%`; unavailable/invalid values display `Risk unavailable`. Applied to patient, alert, Immediate Review, and urgent notification text. | New formatter tests; Flutter suite and analyzer pass. |
| Wrong-patient fallback | Immediate Review no longer substitutes the first patient when the requested patient is absent; it shows `Patient data unavailable`. Stale state is identified. Conflicting envelope/payload patient IDs are rejected. | Widget and event-envelope tests pass. |
| Session traceability | `session_id` is carried from Part 1 adapter through event, prediction, persistence, and alert payload. Existing SQL tables receive additive nullable columns at initialization. | Part 1/Part 2 integration and database tests pass. |
| Feature definitions | Added one ordered 31-feature implementation in `src/pipeline/canonical_features.py`; inference and training feature generation call the shared function. The window is inclusive `[t-4h,t]`, and slopes divide by elapsed clinical hours. Training refuses the absent cohort unless synthetic demo is explicitly opted into and directs outputs to candidate artifacts. | Parity tests cover stable, deteriorating, recovering, irregular-timestamp, and missing-observation histories. |
| Compose database URL | Root Compose backend URL now uses PostgreSQL service DNS and the project's psycopg v3 SQLAlchemy dialect: `postgresql+psycopg://...@postgres:5432/...`. | `docker-compose config` passes; the full stack was recreated and its PostgreSQL health check passed. |
| Test compatibility | Updated the database test to SQLAlchemy 2 `text()` and psycopg v3 URL; errors remain asserted strictly. | Database tests pass. |

## 2. Model artifact and numerical reproduction

- Expected artifact loaded: `model/lr_model.pkl`, with `model/lr_calibrator.pkl` and `model/scaler.pkl`.
- Model class: `LogisticRegression`.
- Model version: `logistic-regression-v1`.
- Runtime flag: `is_demo_model=false` (also observed from the running API).
- Coefficient shape: `(1, 31)`; feature count: 31.
- Intercept observed: `-9.17182631439818`.
- Calibration object: `SigmoidCalibrator`; observed parameters approximately `a=10.8169303`, `b=-8.98154036`.
- Independent numerical check in scikit-learn 1.8.0: raw probability `0.0005614768813`; calibrated probability `0.00012645887857`; runtime calibrated probability matched with absolute difference `0.0` for the checked vector.
- Runtime generated 31 SHAP values for the same vector. Multi-patient runtime integration also checked 31 attribution names and values.

**Training provenance:** `TRAINING PROVENANCE UNVERIFIED`. `logs/05_train_models.log` records pipeline runs that explicitly generated 13,299 synthetic rows for 300 synthetic patients, with 427 generated positive labels, because `aligned_cohort.parquet` was missing. The model-selection decision metrics correspond to that synthetic run. The checked-in artifact has no embedded data/version manifest or checksum-to-run record, so the exact artifact-to-run linkage cannot be proven; none of those old metrics qualify as clinical evaluation. The log describes Platt/sigmoid calibration on its validation split, but that split was also synthetic and is not calibration evidence for clinical use. The artifact was not replaced or retrained because no valid labeled training cohort was available.

This verifies artifact loading and numerical reproduction for the checked vector; it does **not** establish clinical validity, calibration quality, training-data provenance, or that the artifact was trained with the now-canonical feature formulas. The observed model output flag is not proof of its provenance.

## 3. Feature parity

The 31 ordered features are: `hr_curr`, `map_curr`, `rr_curr`, `spo2_curr`, `temp_curr`, `hr_mean_4h`, `hr_std_4h`, `hr_min_4h`, `hr_max_4h`, `map_mean_4h`, `map_std_4h`, `map_min_4h`, `rr_mean_4h`, `temp_mean_4h`, `hr_delta_1h`, `hr_delta_4h`, `hr_slope_4h`, `map_delta_1h`, `map_delta_4h`, `map_slope_4h`, `rr_delta_1h`, `temp_delta_1h`, `hr_accel`, `shock_index`, `resp_distress_idx`, `fever_response_idx`, `lactate_missing`, `time_since_lactate`, `qsofa_curr`, `map_time_low_4h`, `icu_hour`.

| Feature group | Canonical definition | Parity result |
|---|---|---|
| Current vitals (5) | Latest timestamped event values in model order. | Shared training/runtime implementation; tests pass. |
| 4-hour summaries (9) | Mean/std (population), min/max as named, over available observations in inclusive `[t-4h,t]`; absent-series fallback is current value and zero std. | Shared implementation; tests pass. |
| 1-hour deltas (4) | Current minus latest value at or before `t-1h`; zero if no baseline/current value. | Shared implementation; tests pass. |
| 4-hour deltas/slopes (4) | Current minus latest value at or before `t-4h` (first in-window event if no earlier baseline); slope is delta divided by actual elapsed hours. | Shared implementation; irregular-time tests pass. |
| HR acceleration (1) | Difference of consecutive current-to-1h and 1h-to-2h HR changes; zero when baselines are unavailable. | Shared implementation; tests pass. |
| Derived indices (4) | HR/MAP shock index; RR/SpO2 distress index; fever response `HR - 10*(temp-37)`; qSOFA proxy `RR>=22 + MAP<=65`. | Shared implementation; tests pass. |
| Lactate features (2) | Current missing indicator; elapsed time since most recent observed lactate (capped at 8h), or elapsed history if none. | Shared implementation; missing-data tests pass. |
| MAP burden and ICU time (2) | Count of low-MAP observations in the 4h window; elapsed timestamp hours from first event. | Shared implementation; tests pass. |

**Scope caveat:** tests prove the new training feature-generation path and runtime use the same shared implementation. They cannot prove the existing `logistic-regression-v1` training rows/artifact were built using these definitions, because the processed training cohort and provenance are unavailable. Therefore parity for the artifact's historical training inputs is **unverified**, despite the shared-code parity result.

## 4. Multi-patient validation

- Backend: four distinct simulated event histories were interleaved through a single runtime; patient histories/session IDs remained isolated, and each returned a real artifact-based model prediction and separate SHAP vector. Live WebSocket capture received one prediction per patient with matching patient/session identities and 31 SHAP entries each. Integration test passed. The same model produced varying risk outputs over time; because provenance is synthetic/unverified, these are software outputs and not clinical evidence.
- Mobile: unit/widget tests verify patient-keyed state, reject mismatched patient IDs, and show no other patient's data when the requested patient is missing. The unlocked live dashboard showed four distinct simulator patients, each with `Risk: 0.01%` and `NO ALERT`. Opening PATIENT-001 showed `Bedside Review`, the model version, risk, and ranked model contributors, but its `Latest vitals unavailable` panel remained empty despite live simulator vitals elsewhere. The physical app review route was exercised; displaying latest vitals and device reconnect remain unverified.
- Clinical multi-patient performance: unavailable; simulated profiles are software isolation tests, not labeled clinical cases.

## 5. Dataset and ML performance

- `data/processed/aligned_cohort.parquet`: absent. A blocked, machine-readable inventory is at `data/processed/aligned_cohort_manifest.json`.
- Local MIMIC-IV Demo 2.2 inventory: 100 subjects; 140 ICU stays; 668,862 chart events; 107,727 lab events; 2,899 microbiology events; 15,306 pharmacy rows; 18,087 prescriptions; 20,404 ICU input events; 9,362 ICU output events. The raw source tables include inputs used by the official six-component SOFA and suspected-infection concepts. The Demo is a 100-patient subset provided for feasibility assessment, not a source for claims of generalizable performance ([PhysioNet MIMIC-IV Demo 2.2](https://www.physionet.org/content/mimic-iv-demo/2.2/)).
- The old `data/02_sepsis3_extraction.py` was mathematically invalid: its cardiovascular-only component was limited to 0/1 while the code required `MAX(score) >= 2`; it also used an incomplete hard-coded antibiotic match. It has been replaced with a fail-closed importer for `mimiciv_derived.sepsis3`, requiring the official MIT-LCP `suspicion_of_infection`, full `sofa`, and `sepsis3` concepts. The official concept sets Sepsis-3 from suspected infection plus total SOFA >=2 in its defined infection assessment window ([MIT-LCP Sepsis-3 concept](https://github.com/MIT-LCP/mimic-code/blob/main/mimic-iv/concepts_duckdb/sepsis/sepsis3.sql), [SOFA concept](https://github.com/MIT-LCP/mimic-code/blob/main/mimic-iv/concepts_duckdb/score/sofa.sql), [suspected infection concept](https://github.com/MIT-LCP/mimic-code/blob/main/mimic-iv/concepts_duckdb/sepsis/suspicion_of_infection.sql)).
- Official derived relations are not installed in this environment, so no true positive/negative Sepsis-3 count has been computed. The manifest records label counts as null, not zero. There is no processed clinical cohort, train/validation/test partition, or patient-overlap result.
- The previous implicit synthetic fallback is now disabled unless `--allow-synthetic-demo` is explicitly supplied. Synthetic profiles were used only for software behavior/isolation tests and are not evaluation data.
- Training/validation/test patient counts, positive/negative patients, prediction horizon validity, patient-disjointness, ICU-stay leakage, duplicate-window leakage, and temporal leakage: **not established**.
- AUROC, AUPRC, sensitivity, specificity, PPV, NPV, F1, Brier score, calibration curve/slope/intercept, confusion matrix (TN/FP/FN/TP), and clinical examples: **NOT AVAILABLE**. No held-out clinical cohort exists to calculate them validly.
- Alert thresholds remain unchanged: WATCH `0.25`, REVIEW `0.35`, URGENT `0.70`. Clinical threshold behavior was not evaluated on a valid held-out cohort.

## 6. Mobile risk trace and Android

- Captured a real WebSocket prediction from the currently running service at `2026-10-02T07:34:13.696064+00:00` for `PATIENT-001`: `risk_probability=0.00012569325996341176`, `model_version=logistic-regression-v1`, `is_demo_model=false`, severity `None`.
- Root cause reproduced: prior one-decimal percentage formatting rendered this valid nonzero risk as `0.0%`.
- New formatter output for that exact value: `0.01%`; probabilities smaller than 0.01% display `<0.01%`. A reference value `0.862403` displays `86.24%`.
- Flutter parsing, app-state, widget, and formatter tests pass; final rendered strings are tested. The real socket message was not instrumented through every live Flutter layer on device.
- ADB detected device `Infinix_X6852`. Built and installed current-source APK `1.0.0+2` (`versionCode=2`) with app data preserved. After the user unlocked it, the dashboard visibly showed four live patients with `0.01%` and `NO ALERT` for each. Opening PATIENT-001 showed `Bedside Review`, `0.01%`, model version `logistic-regression-v1`, and SHAP contributors. That view simultaneously showed `Latest vitals unavailable`, a live data-display defect/limitation requiring follow-up. The accessibility dump did not complete (`could not get idle state`) while the app was continuously updating. The app was not uninstalled or cleared. The phone routes to host `172.27.45.54`.

## 7. Database and end-to-end status

- Compose configuration: corrected for PostgreSQL; all three containers were recreated and are healthy.
- Before cutover, created a SQLite online backup, verified `PRAGMA integrity_check=ok`, stopped the simulator, confirmed counts stable, and created a final quiesced backup. Migrated 6 patients, 11,443 vital events, 11,443 predictions, and 2 alerts (22,894 rows) to PostgreSQL while preserving IDs. A read-only row-by-row comparison of every migrated column and JSON payload matched the source backup.
- The active Part 1 registry was exported before restart and is now persisted through a Compose bind mount at `.argus_live_part1_registry_20261002.json`; its original active patient/session survived recreation.
- Runtime proof: container environment has `DATABASE_URL=postgresql+psycopg://...@postgres:5432/sepsisguard`; SQLAlchemy reports dialect `postgresql`; PostgreSQL contains all four tables and the migrated records. New simulator rows arrived after cutover with non-null session IDs. PostgreSQL persisted a new alert as well.
- Backups retained in workspace: `.argus_live_part2_sqlite_quiesced_20261002.sqlite` (verified migration source) and `.argus_live_part1_registry_20261002.json` (active bind-mounted registry; it now contains the four audit/demo patients).
- The host's separate port-5432 endpoint did not accept the Compose credentials; validation and migration were correctly run inside the Compose network against service DNS `postgres`.

| Layer | Status | Evidence / limit |
|---|---|---|
| Part 1 | PASS (automated regression) | `126 passed`; live stack was already running. |
| Part 2 | PASS (automated regression) | `205 passed, 1 skipped`; temp SQLite test DB. |
| Model loading/numerics | PASS for checked vector | Real LR and calibrator loaded; independent result matched. Clinical validity remains unverified. |
| Feature/SHAP | PASS for tested histories | Five parity profiles and four-patient runtime test. Historical artifact training parity unverified. |
| Alert engine | PASS in regression tests | No real rapid-deterioration/RED clinical scenario or phone alert was generated for this audit. |
| WebSocket | PASS for live message capture | Captured real risk; full live replay into updated phone not performed. |
| Flutter | PARTIAL (31 tests from prior sequential run) | Parallel rerun exhausted Windows Dart worker resources. A sequential rerun was started, but had not completed at report time; analyzer also failed under resource exhaustion. Native notification behavior is not tested by widget tests. |
| Android | PARTIAL | Current APK installed and opened. Four-patient dashboard and PATIENT-001 review were visibly checked; review displayed model contributors but said `Latest vitals unavailable`. Native notification behavior remains unverified. |
| PostgreSQL | PASS | Running backend uses PostgreSQL; 22,894 migrated rows across four tables passed row-by-row comparison, and new rows persisted after restart. |
| Clinical performance | NOT AVAILABLE | No valid labeled, patient-disjoint processed cohort. |

## 8. Regression checks

- Part 1: `126 passed`.
- Part 2 relevant suite: `205 passed, 1 skipped` including the new fail-closed extraction tests.
- Flutter: prior sequential run `31 tests passed`; the final parallel rerun failed from Dart worker/memory exhaustion. A sequential rerun stalled without output and was stopped; the earlier 31-test result remains the last complete run.
- Flutter analyzer: prior run `No issues found`; final parallel rerun failed from Dart worker/memory exhaustion.
- Compose: `docker-compose config` passed.
- `git diff --check` reports whitespace warnings in pre-existing/modified files (including `part1/backend/app/main.py`); no broad whitespace cleanup was applied to avoid changing unrelated work.
- The workspace contained extensive pre-existing modified and untracked content. No reset, commit, or push was performed.

## 9. Remaining work required before READY

1. Build the official MIT-LCP-derived relations for local MIMIC-IV Demo 2.2, verify the target output and label counts, then decide whether the small Demo cohort supports a non-clinical pipeline smoke test. Obtain an appropriately sized/approved labeled cohort for meaningful held-out clinical evaluation.
2. Generate canonical features and patient-disjoint partitions; perform duplicate-window, stay-overlap, and temporal leakage checks. Preserve test data untouched and evaluate/recalibrate only with valid cohort provenance. Create a versioned Logistic Regression artifact only if valid data supports retraining.
3. Fix and recheck the Bedside Review `Latest vitals unavailable` panel with live records. Complete Immediate Review and WebSocket reconnect checks; observe an actual urgent notification physically before marking sound/vibration pass.

Until these are complete, ARGUS is **NOT READY for clinical deployment**. The implemented parsing, patient-isolation, feature-sharing, and risk display fixes are validated in automated tests, but they do not resolve the clinical-data/model-provenance gap or the Bedside Review live-vitals and native-notification verification gaps.
