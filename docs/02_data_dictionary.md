# SepsisGuard AI: MIMIC-IV Data Acquisition and Dataset Strategy

## 1. Governance, Ethics, and Access

### 1.1 MIMIC-IV Access Requirements
MIMIC-IV is a credentialed, restricted-access database managed by PhysioNet. To access the full dataset:
1.  **Training:** The researcher must complete the CITI "Data or Specimens Only Research" training course.
2.  **Application:** The researcher must formally request access via PhysioNet, providing a clear research objective.
3.  **Data Use Agreement (DUA):** The researcher must sign the DUA, legally binding them to the usage terms.

### 1.2 De-identification Considerations
MIMIC-IV is strictly de-identified in accordance with HIPAA Safe Harbor provisions.
*   **Time Shifting:** All dates are shifted into the future (e.g., the year 2100+). Time intervals between a single patient's events are preserved, but the actual calendar year is obscured. `anchor_year` is used to roughly correlate with actual data collection periods if needed.
*   **Identifiers:** Names, contact information, and specific locations are removed.
*   **Clinical Notes:** Free text (in `noteevents` or `discharge`) is heavily scrubbed for PHI.

### 1.3 Research-Use Limitations
*   **No Commercial Diagnostics:** Under the DUA, the dataset cannot be used to build a commercial diagnostic product without explicit permission.
*   **No Re-identification:** Any attempt to re-identify patients is strictly prohibited and results in immediate loss of access.
*   **Open Science:** Researchers are expected to share their code and methodologies.

### 1.4 Dataset Version Assumptions
This strategy assumes **MIMIC-IV v2.2** (or the recently released v3.0). Schema changes between v1.0, v2.0, and v2.2/v3.0 (especially regarding medication tables like `pharmacy` vs `prescriptions`) require strict version control tracking.

---

## 2. Required Modules and Tables

| Domain | MIMIC-IV Module | Table | Purpose |
| :--- | :--- | :--- | :--- |
| **Demographics** | `hosp` | `patients` | Age, gender, mortality status |
| **Encounters** | `hosp` | `admissions` | Hospital admission times, demographics |
| **ICU Tracking** | `icu` | `icustays` | ICU in/out times, identifying the cohort |
| **Vital Signs** | `icu` | `chartevents` | High-frequency physiological signals |
| **Lab Tests** | `hosp` | `labevents` | Blood panels, organ function markers |
| **Microbiology** | `hosp` | `microbiologyevents` | Blood/fluid cultures for Sepsis-3 infection criteria |
| **Medications** | `hosp` / `icu` | `prescriptions` / `inputevents` | Antibiotic administration, vasopressor use |
| **Dictionary** | `icu` / `hosp` | `d_items`, `d_labitems` | Mapping `itemid` to human-readable names |

---

## 3. Final Candidate Feature Dictionary

> **IMPORTANT SCHEMA VERIFICATION NOTICE:** While the `itemid`s listed below are the established standards for MIMIC-IV, they **must** be verified against the `d_items` and `d_labitems` tables in your specific database version before running SQL extractions, as hospital systems occasionally map multiple IDs to the same clinical concept.

### 3.1 Patient Demographics & Encounters
| Variable Name | Source Table | Source Column | Unit | Freq | Continuous/Discrete | Required | Missingness | Leakage Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `subject_id` | `patients` | `subject_id` | ID | Static | Discrete | **Yes** | None | High (if not used for grouping) |
| `hadm_id` | `admissions` | `hadm_id` | ID | Static | Discrete | **Yes** | None | High (grouping) |
| `stay_id` | `icustays` | `stay_id` | ID | Static | Discrete | **Yes** | None | High (grouping) |
| `age` | `patients` | `anchor_age` | Years | Static | Continuous | **Yes** | None | Low |
| `gender` | `patients` | `gender` | M/F | Static | Discrete | Optional | None | Low |

### 3.2 Vital Signs (Current & Trended)
*All vitals are extracted from `icu.chartevents`.*

| Variable Name | `itemid` (Verify) | Unit | Freq | Continuous/Discrete | Required | Missingness | Artifact / Leakage Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `heart_rate` | 220045 | bpm | Hourly | Continuous | **Yes** | Low | Sensor disconnects (0 or >250) |
| `resp_rate` | 220210, 224690 | insp/min| Hourly | Continuous | **Yes** | Low | Highly noisy; motion artifacts |
| `spo2` | 220277 | % | Hourly | Continuous | **Yes** | Low | Fingertip displacement |
| `sbp` (Sys BP) | 220179, 220050 | mmHg | Hourly | Continuous | **Yes** | Med | Cuff dislodgement / arterial line flush |
| `dbp` (Dia BP) | 220180, 220051 | mmHg | Hourly | Continuous | **Yes** | Med | Cuff dislodgement |
| `map` (Mean BP)| 220181, 220052 | mmHg | Hourly | Continuous | **Yes** | Med | Critical for cardiovascular SOFA |
| `temp_c` | 223761 (F: 223762) | °C | 4-6 Hrs| Continuous | **Yes** | High | F/C conversion errors in raw data |

### 3.3 Laboratory Measurements (Carried / Non-Interpolated)
*Most labs are extracted from `hosp.labevents`. Point-of-care (POC) labs may be in `chartevents`.*

| Variable Name | `itemid` (Verify) | Clinical Meaning | Freq | Continuous/Discrete | Required | Missingness | Artifact / Leakage Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lactate` | 50813, 225668 | Tissue hypoperfusion | Daily+ | Continuous | **Yes** | Very High | **High Leakage Risk:** Ordering a lactate strongly implies clinical suspicion of sepsis. |
| `wbc` | 51301, 51300 | Immune/Infection resp. | Daily | Continuous | **Yes** | High | Low |
| `creatinine` | 50912 | Renal SOFA component | Daily | Continuous | **Yes** | High | Low |
| `bilirubin` | 50885 | Hepatic SOFA component | Daily | Continuous | Optional| Very High | Low |
| `platelets` | 51265 | Coagulation SOFA | Daily | Continuous | **Yes** | High | Low |
| `pao2` | 50821 | Respiration SOFA (ABG)| Sporadic| Continuous | Optional| Very High | Low |
| `fio2` | 223835 | Respiration SOFA (Vent)| Sporadic| Continuous | Optional| Very High | Hard to extract (often free text % vs decimal) |

### 3.4 Sepsis-3 Labeling Components (DO NOT use as predictive features)
*These tables are strictly for defining $t_{sepsis}$ and evaluating the target variable. They must be excluded from the feature matrix to prevent data leakage.*

| Variable Name | Source Table | Source Column | Purpose | Leakage Risk if used in features |
| :--- | :--- | :--- | :--- | :--- |
| `culture_time` | `microbiologyevents` | `charttime` | Identifies suspected infection. | **100% Leakage.** Knowing a culture was taken reveals clinical suspicion. |
| `antibiotic_time`| `prescriptions` | `starttime` | Identifies suspected infection. | **100% Leakage.** |
| `vaso_rate` | `inputevents` | `rate` (itemid: 221906, etc)| Defines cardiovascular SOFA = 3 or 4. | **100% Leakage.** Vasopressors are the *treatment* for septic shock. |

---

## 4. Derived Feature Definitions
As per Phase 3 specifications, raw vitals will be transformed into the following vector per patient per hour $t$:

*   **Current State:** $V_{t}$
*   **Missingness:** $M_{t} \in \{0, 1\}$
*   **Time Since Measurement:** $T_{last} = t - t_{measurement}$
*   **Deltas:** $\Delta_{1h}, \Delta_{2h}, \Delta_{4h}$
*   **Slopes:** $\frac{\Delta_{2h}}{2}, \frac{\Delta_{4h}}{4}$
*   **Acceleration:** $\Delta_{1h}(t) - \Delta_{1h}(t-1)$
*   **Rolling 4h Stats:** $Mean, Min, Max, StdDev, Range$
