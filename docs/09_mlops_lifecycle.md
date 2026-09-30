# SepsisGuard AI MLOps Lifecycle

This document defines the end-to-end Machine Learning Operations (MLOps) lifecycle for SepsisGuard AI. It ensures reproducibility, traceability, and continuous monitoring of our predictive models in clinical environments. We utilize **MLflow** as our primary lightweight experiment tracking and model registry system.

## 1. MLOps Pipeline Architecture

The pipeline consists of the following sequential stages:

**`Data Versioning` → `Preprocessing Version` → `Feature Version` → `Model Training` → `Validation` → `Model Registry` → `Deployment` → `Monitoring` → `Retraining`**

### 1.1 Data & Feature Versioning
*   **Data Versioning**: Raw extracted clinical datasets (e.g., from EHR systems) are versioned using tools like DVC (Data Version Control) or stored as immutable snapshots in secure object storage (e.g., S3) with timestamped prefixes. The unique `dataset_version` identifier is tracked.
*   **Preprocessing Version**: The code responsible for cleaning, imputing, and normalizing data is versioned via Git. The Git commit hash of the preprocessing pipeline acts as the `preprocessing_version`.
*   **Feature Version**: The schema and logic used to generate the final feature matrix from the preprocessed data are recorded as the `feature_version`.

### 1.2 Model Training & Validation
*   **Training Execution**: Models are trained using standardized pipelines to ensure consistent environments and dependency management.
*   **Validation**: Every trained model undergoes rigorous validation on a hold-out test set to evaluate metrics like AUC-ROC, Precision-Recall, and clinical utility.
*   **Calibration**: Post-training calibration (e.g., Platt scaling, Isotonic regression) is performed to ensure the predicted probabilities accurately reflect true clinical risk. 

### 1.3 MLflow Experiment Tracking
During the training and validation phase, the following metadata is strictly logged to the **MLflow Tracking Server** for every experiment run:

*   **`model_version`**: Automatically managed by the MLflow Model Registry upon registration.
*   **`dataset_version`**: Hash or URI of the immutable raw training dataset.
*   **`feature_version`**: Git commit hash of the feature engineering codebase used.
*   **`training_timestamp`**: Exact UTC timestamp of the training run initiation.
*   **`hyperparameters`**: Complete dictionary of all model hyperparameters.
*   **`metrics`**: Comprehensive performance metrics (AUC, AUPRC, F1-score, Brier score) from all validation splits.
*   **`calibration`**: Calibration methodology applied and resulting diagnostic metrics.
*   **`threshold_configuration`**: The specific clinical decision threshold(s) optimized for alert generation, based on desired sensitivity/specificity tradeoffs for the target ward.

### 1.4 Model Registry & Deployment
*   **Model Registry**: Successfully validated models that meet the deployment criteria are promoted to the MLflow Model Registry (e.g., tagged as `Staging` or `Production`). The registry acts as the single source of truth for all production model artifacts.
*   **Deployment**: The prediction service pulls the currently tagged `Production` model artifact from the registry during initialization or via a controlled rolling update mechanism.
*   **Traceability Requirement (CRITICAL)**: The prediction API **MUST** embed the active `model_version` in the response payload for every single inference request. Furthermore, this version is logged alongside the prediction in the application database. This ensures every clinical alert can be definitively traced back to the exact model version, hyperparameters, and training dataset that produced it.

### 1.5 Monitoring & Retraining
*   **Inference Logging**: The prediction service logs all incoming feature vectors, resulting predictions, and the active `model_version` to a dedicated, pseudonymized monitoring database.
*   **Drift Detection**: Automated monitoring jobs periodically compare the distribution of real-time inference features against the baseline training distribution (linked via `dataset_version`) to detect data drift.
*   **Retraining Trigger**: If significant data drift is detected, or if monitored clinical outcomes indicate a degradation in model performance below predefined thresholds, an automated alert is dispatched to the ML engineering team to review and potentially trigger a new training pipeline iteration.
