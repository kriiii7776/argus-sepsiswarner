# SepsisGuard AI - Acceptance Criteria & Test Plan

This document outlines the acceptance criteria and test coverage mapped to the automated test suite.

## 1. Unit Tests (`tests/unit/`)
*   **Feature Calculations & Preprocessing**: Verify that imputations, scaling, and rolling aggregations match expected values.
*   **Scoring Systems & Label Generation**: Ensure SIRS/qSOFA/NEWS scores calculate correctly from raw vitals, and retrospective labeling generates the correct binary target window.
*   **Alert Logic**: Verify the engine triggers only when thresholds are breached, avoiding duplicates.

## 2. Integration Tests (`tests/integration/`)
*   **Database**: Mock database operations properly persist and fetch patient state.
*   **FastAPI & WS**: REST endpoints return expected schemas and status codes. WebSocket broadcasts events.
*   **ML Inference Service**: Integration with the mock or loaded pickle model works end-to-end.

## 3. Model Tests (`tests/model/`)
*   **Leakage**: Target variables must not be directly correlated with predictive features.
*   **Robustness & Calibration**: Model must output probabilities bounded [0, 1] and handle noisy synthetic inputs cleanly.
*   **Temporal Shift**: Test model distributions on split temporal datasets.

## 4. System Tests (`tests/system/`)
*   **Latency**: Sub-500ms inference and API response time.
*   **Concurrency**: Can handle 100+ concurrent simulated ICU streams.
*   **Interruption/Failures**: Graceful degradation when DB or ML service fails (e.g. 503 Service Unavailable, no cascading crashes).

## 5. Safety Tests (`tests/safety/`)
*   **Abnormal/Missing Values**: Graceful handling (e.g., ignoring `SpO2 > 100` or returning uncertain predictions when data sparsity > 80%).
*   **Contradictory Measurements**: Detecting physiologically impossible states (e.g., HR=0 but BP=120/80).
*   **Alert Flooding**: Engine must enforce a cooldown or aggregation mechanism so clinicians aren't overwhelmed.
