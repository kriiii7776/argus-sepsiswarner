# SepsisGuard AI: Phase 1 - Architecture & Clinical Definitions

## 1. Clinical Definitions
**Condition:** Sepsis
**Standard:** Sepsis-3 Criteria (Singer et al., 2016)
**Definition:** Life-threatening organ dysfunction caused by a dysregulated host response to infection.
**Operationalization (MIMIC-IV):**
*   **Suspected Infection:** Administration of antibiotics AND body fluid cultures obtained within a specified timeframe (e.g., cultures within 24h before to 72h after antibiotics).
*   **Organ Dysfunction:** An acute increase in Sequential Organ Failure Assessment (SOFA) score $\ge$ 2 points consequent to the infection.
*   **Onset Time ($t_{sepsis}$):** The earlier of the culture time or antibiotic time, provided the SOFA increase occurs within the clinical window.
*   **Prediction Window:** 6 hours prior to $t_{sepsis}$. The model will attempt to predict whether a patient will develop sepsis 6 hours in the future based on a trailing window of physiological data.

## 2. System Architecture

The system is designed for real-time inference (simulated), prioritizing explainability and clinical safety.

### 2.1 High-Level Components
1.  **Data Ingestion (Simulation Layer):** A Python script simulating real-time HL7/FHIR or raw streaming data by replaying MIMIC-IV patient trajectories over WebSockets.
2.  **Database (PostgreSQL):** Stores patient demographics, static features, and high-frequency time-series data (vitals, labs).
3.  **Backend (FastAPI):**
    *   Receives streaming data.
    *   Triggers feature extraction (rolling windows).
    *   Invokes the ML Model.
    *   Calculates SHAP values for explainability.
    *   Serves REST endpoints for historical data and WebSockets for real-time dashboard updates.
4.  **Machine Learning Engine (LightGBM/XGBoost):**
    *   Chosen for robust performance on tabular time-series data, handling of missing values, and fast inference.
    *   Wrapped with TreeSHAP for exact local explanations.
5.  **Frontend Dashboard (React):**
    *   Clinical UI emphasizing patient timelines, risk scores, and alert prioritization.
    *   Displays SHAP feature importance intuitively (e.g., "Risk driven by: decreasing MAP and elevated Lactate").

### 2.2 Data Schema (Conceptual PostgreSQL)
*   **`patients`**: `subject_id`, `gender`, `anchor_age`, `anchor_year`
*   **`admissions`**: `hadm_id`, `subject_id`, `admittime`, `dischtime`, `admission_type`
*   **`icustays`**: `stay_id`, `hadm_id`, `intime`, `outtime`
*   **`vitals_labs_stream`**: `stay_id`, `charttime`, `heart_rate`, `map`, `resp_rate`, `temp`, `spo2`, `fio2`, `wbc`, `lactate`, `creatinine`, `bilirubin`, `platelets`, `gcs`
*   **`predictions`**: `prediction_id`, `stay_id`, `timestamp`, `risk_score`, `shap_json`

## 3. Core Constraints Addressed
*   **No Data Leakage:** Prediction time $t_{pred} = t_{sepsis} - 6\text{h}$. Only data where `charttime` $\le t_{pred}$ will be used for features.
*   **Explainability:** TreeSHAP integrated directly into the inference pipeline.
*   **Patient-level Separation:** Train/Val/Test splits will be strictly grouped by `subject_id` to prevent records from the same patient leaking across sets.
