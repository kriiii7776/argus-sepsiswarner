# Post-Deployment Monitoring and Retraining Workflow

This document outlines the comprehensive post-deployment monitoring strategy for SepsisGuard AI. This strategy is designed to ensure continuous model safety, reliability, and clinical utility. It also defines the strict, human-in-the-loop retraining workflow.

## 1. Monitoring Dimensions

The monitoring system tracks four distinct types of drift to capture both statistical and operational degradation.

### 1.1 Data Drift
Monitors changes in the statistical distribution of the input features over time, independently of the clinical outcome. This helps detect shifting patient populations or systemic changes in how measurements are taken.
*   **Metrics**: Population Stability Index (PSI), Wasserstein distance, or Kolmogorov-Smirnov test applied to feature distributions.
*   **Target**: Vital signs (HR, Temp, BP), lab results (Lactate, WBC), and derived physiological features.

### 1.2 Concept Drift
Monitors changes in the fundamental relationship between the input features and the true clinical outcome (sepsis diagnosis). This occurs if the underlying disease manifestation changes or if clinical protocols evolve (e.g., a new standard of care affects how quickly symptoms progress).
*   **Metrics**: Correlation coefficients between features and the target variable over sliding windows; tracking feature importance stability over time.

### 1.3 Performance Drift
Monitors the predictive performance of the model against true clinical outcomes (which are typically delayed by hours or days until the final diagnosis is recorded).
*   **Metrics**: AUROC, AUPRC, Calibration (Brier score, Expected Calibration Error - ECE), and Sensitivity (Recall) evaluated at the chosen operational threshold.

### 1.4 Operational Drift
Monitors the health of the data pipeline and the inference infrastructure to ensure timely and reliable predictions.
*   **Metrics**:
    *   **Missingness**: The percentage of missing values per feature or per patient encounter.
    *   **Latency**: End-to-end inference time (from data arrival in the EHR to alert generation).
    *   **Alert Frequency**: The absolute volume of high-risk alerts generated per ward/day (crucial to detect and prevent alert fatigue).
    *   **Sensor Quality**: Detection of impossible physiological values (e.g., negative heart rate, body temperature outside biological limits) or stuck sensors (constant values over prolonged periods).

## 2. Alert Thresholds

The monitoring system evaluates metrics over a rolling window (e.g., daily and weekly aggregates) and triggers alerts based on predefined thresholds. 

| Drift Category | Metric Example | Normal | Warning (Investigation Required) | Critical (Immediate Intervention) |
| :--- | :--- | :--- | :--- | :--- |
| **Data Drift** | PSI (Key Features) | `< 0.1` | `0.1 - 0.2` | `> 0.2` |
| **Concept Drift**| Feature-Outcome Correlation Shift | `< 10% change` | `10% - 20% change` | `> 20% change` |
| **Performance**| AUROC | `> Baseline - 0.02` | `Baseline - 0.05` to `Baseline - 0.02` | `< Baseline - 0.05` |
| **Performance**| Sensitivity @ Threshold | `> 0.80` | `0.75 - 0.80` | `< 0.75` |
| **Operational**| Feature Missingness | `< 5%` | `5% - 15%` | `> 15%` |
| **Operational**| Alert Frequency (per 100 beds) | `5 - 15 / day` | `15 - 25 / day` (or `< 5`) | `> 25 / day` (High Alert Fatigue Risk) |

*Note: 'Baseline' refers to the performance achieved on the validation set during the model's original training phase.*

## 3. Model Review and Retraining Workflow

**CRITICAL DIRECTIVE: SepsisGuard AI is a clinical decision support tool. Under NO circumstances will the model automatically retrain and deploy itself to production without human validation and approval.**

All retraining events must follow a strict, human-in-the-loop review process to ensure patient safety.

### Step 1: Alert Generation & Triage
1.  The monitoring system detects a metric crossing a **Warning** or **Critical** threshold.
2.  An automated alert is immediately dispatched to the ML Engineering and Clinical Operations teams, detailing the exact metrics, timeframes, and affected hospital wards.
3.  *Action*: If a **Critical** operational or performance alert fires, the system may be temporarily placed in a "Shadow Mode" or "Degraded Mode" (e.g., silencing automated UI alerts for clinicians but continuing to log predictions in the background) pending urgent review.

### Step 2: Investigation & Root Cause Analysis
1.  The ML Engineering team investigates the drift.
2.  *Questions to answer*: Is this a transient data pipeline issue (e.g., a broken EHR API integration causing high missingness)? Or is it a genuine shift in clinical reality (e.g., a new pathogen wave altering baseline vitals)?
3.  *Action*: If it's a transient pipeline issue, the engineering team fixes the pipeline. If it's a genuine drift requiring model adaptation, proceed to Step 3.

### Step 3: Manual Retraining & Validation (Shadow Environment)
1.  A new, curated dataset snapshot is created, incorporating the recent data that triggered the drift alongside historical data.
2.  An ML Engineer manually triggers the training pipeline using the new dataset.
3.  The new candidate model (`Model_V_Next`) is rigorously evaluated against a new, representative hold-out set.
4.  The candidate model is deployed to a **Shadow Environment**. Here, it runs inference on live, real-time data, but its predictions are *not* surfaced to clinicians. Its performance and calibration are compared head-to-head against the current production model over a set period.

### Step 4: Clinical Review & Approval
1.  A comprehensive "Model Update Report" is generated, comparing the performance, calibration curves, and feature importance of the production model versus the candidate model.
2.  The report is reviewed by the **Clinical AI Governance Board** (comprising Lead Clinicians, Data Scientists, and Risk Officers).
3.  The board must explicitly sign off on the update, verifying that the new model is statistically superior and, most importantly, clinically safe.

### Step 5: Controlled Deployment
1.  Upon formal approval, the candidate model is promoted to the Production Model Registry.
2.  The prediction service performs a zero-downtime rolling update to load the new model version.
3.  *Post-Deployment*: The monitoring window baselines are reset, and the system is placed on heightened alert (a "hypercare" period) for the first 72 hours post-deployment to ensure stability.
