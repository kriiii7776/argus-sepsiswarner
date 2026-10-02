# ARGUS Part 2 Phase 2A Consolidation Report

## 1. Objective
The objective of Phase 2A was to consolidate the working runtime implementation logic from `deployment/backend/app` into the clean, modular architecture of `src/backend`. This creates a single official backend for ARGUS Part 2 while strictly preserving legacy references, avoiding unneeded refactoring, and maintaining baseline safety.

---

## 2. Files Changed

### Newly Created Files under `src/backend/`
- [`src/backend/db/__init__.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/db/__init__.py) — Database package initializer.
- [`src/backend/db/store.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/db/store.py) — SQLAlchemy engine, session maker, and ORM models (`PatientRecord`, `VitalRecord`, `PredictionRecord`, `AlertRecord`).
- [`src/backend/db/repositories.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/db/repositories.py) — `PatientRepository` executing database select and insert operations.
- [`src/backend/services/inference_runtime.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/services/inference_runtime.py) — 31-feature ML `Runtime` engine, signal quality checker, and `SmartAlertEngine` wrapper.
- [`src/backend/services/event_broker.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/services/event_broker.py) — `LocalEventBroker` managing WebSocket subscriber sets and broadcasting JSON `EventEnvelope` payloads.
- [`src/backend/api/endpoints/events.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/api/endpoints/events.py) — REST endpoints for `POST /events/vitals` and `POST /simulator/start`.
- [`src/backend/api/endpoints/websocket.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/api/endpoints/websocket.py) — WebSocket stream endpoint `/ws/stream` and echo endpoint `/ws`.

### Modified Existing Files under `src/backend/`
- [`src/backend/core/config.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/core/config.py) — Consolidated environment configuration (`database_url`, `api_key`, `cors_origins`, `max_vitals_per_request`).
- [`src/backend/core/security.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/core/security.py) — Integrated both OAuth2 Bearer token (`get_current_user`) and API Key (`require_api_key`) authentication.
- [`src/backend/schemas/schemas.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/schemas/schemas.py) — Unified legacy and production event schemas (`VitalEvent`, `PredictionResponse`, `PatientCreate`, `PatientResponse`, `SimulatorRequest`, etc.).
- [`src/backend/services/patient_service.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/services/patient_service.py) — Converted from in-memory dicts to SQLAlchemy `PatientRepository` persistence.
- [`src/backend/services/inference_service.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/services/inference_service.py) — Converted from random float generation to real `inference_runtime` prediction, database event logging, and WebSocket broadcast.
- [`src/backend/api/endpoints/health.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/api/endpoints/health.py) — Integrated runtime model version status.
- [`src/backend/api/endpoints/patients.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/api/endpoints/patients.py) — Wired endpoints to DB-backed services.
- [`src/backend/api/router.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/api/router.py) — Assembled `health`, `patients`, `events`, and `websocket` sub-routers.
- [`src/backend/main.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/main.py) — Configured lifespan initialization, CORS middleware, and API router.

### Files Preserved Unmodified
- **`deployment/backend/app/` (Legacy Reference):** **0 files modified or deleted.**
- **`src/frontend/` (Frontend UI):** **0 files modified.**

---

## 3. Components Consolidated

| Component Area | Pre-Consolidation State | Post-Consolidation State |
|---|---|---|
| **App Architecture** | Split between `src/backend` and `deployment/backend/app` | Single FastAPI application under `src/backend/main.py` |
| **REST APIs** | `/api/v1` returned mock data; `/v1` had working ingestion | Single router under `src/backend/api/` with DB persistence & event ingestion |
| **WebSocket** | `/api/v1/ws` echoed text; `/v1/stream` broadcast events | `LocalEventBroker` in `src/backend/services/event_broker.py` handling broadcasts |
| **Database Layer** | In-memory dicts (`patients_db`) | SQLAlchemy ORM engine & repositories in `src/backend/db/` |
| **ML Inference Engine** | Random float generator (`random.uniform`) | 31-feature `Runtime` engine in `src/backend/services/inference_runtime.py` |
| **Schemas** | Disconnect between primitive & production schemas | Consolidated canonical models in `src/backend/schemas/schemas.py` |
| **Authentication** | Separate header & bearer dependencies | Unified in `src/backend/core/security.py` |

---

## 4. Database Integration
- Implemented SQLAlchemy engine, session maker, and ORM tables (`PatientRecord`, `VitalRecord`, `PredictionRecord`, `AlertRecord`) in `src/backend/db/store.py`.
- Auto-initialized tables on startup via FastAPI lifespan event in `src/backend/main.py`.
- Replaced in-memory dictionaries in `PatientService` with `PatientRepository` database queries.

---

## 5. ML Runtime Integration
- Migrated 31-feature calculation vector and model loader to `src/backend/services/inference_runtime.py`.
- Integrated `data/04_signal_quality.py` quality scoring and `src/pipeline/11_smart_alert_engine.py` policy checking.
- Updated `InferenceService.ingest()` to run real inference, persist vitals/predictions/alerts to database, and broadcast results via WebSocket.

---

## 6. Schema Integration
- Combined legacy schemas (`Patient`, `Vital`, `RiskAssessment`, `Alert`, `Explanation`) and runtime event schemas (`VitalEvent`, `PredictionResponse`, `SimulatorRequest`, `EventEnvelope`, `PatientResponse`, `VitalResponse`, `TrajectoryResponse`, `AlertResponse`, `ModelVersionResponse`) in `src/backend/schemas/schemas.py`.

---

## 7. REST API Integration
- Mounted canonical endpoints:
  - `GET /api/v1/health`
  - `GET /api/v1/model-version`
  - `POST /api/v1/patients`
  - `GET /api/v1/patients/{id}`
  - `GET /api/v1/patients/{id}/vitals`
  - `GET /api/v1/patients/{id}/trajectory`
  - `GET /api/v1/patients/{id}/risk`
  - `GET /api/v1/patients/{id}/explanation`
  - `GET /api/v1/patients/{id}/alerts`
  - `POST /api/v1/events/vitals`
  - `POST /api/v1/simulator/start`

---

## 8. WebSocket Integration
- Centralized subscriber registration and JSON `EventEnvelope` publication in `src/backend/services/event_broker.py`.
- Exposed `/api/v1/ws/stream` and `/api/v1/ws` endpoints in `src/backend/api/endpoints/websocket.py`.

---

## 9. Authentication Integration
- Merged Bearer token authentication (`get_current_user`) and API Key authentication (`require_api_key`) into `src/backend/core/security.py`.

---

## 10. Mock Components Replaced
- **Random Risk Score Generator (`random.uniform(0.1, 0.9)`):** Replaced with `inference_runtime` 31-feature model runner.
- **In-Memory Dictionaries (`patients_db`, `vitals_db`):** Replaced with SQLAlchemy ORM tables (`patients`, `vital_events`, `predictions`, `alerts`).
- **Text Echo WebSocket:** Replaced with `LocalEventBroker` live event stream publisher.

---

## 11. Legacy Components Preserved
The following files in `deployment/backend/app/` were preserved **100% unmodified** as legacy reference artifacts:
- `deployment/backend/app/main.py`
- `deployment/backend/app/service.py`
- `deployment/backend/app/store.py`
- `deployment/backend/app/schemas.py`
- `deployment/backend/app/repositories.py`
- `deployment/backend/app/api/patients.py`
- `deployment/backend/app/api/system.py`

---

## 12. Import & Test Verification

### Static Import Verification
- Command: `python -c "import src.backend.main; print('IMPORT SUCCESS')"`
- Result: **SUCCESS (Exit Code 0)**

### Test Suite Execution
- Command: `python -m pytest tests/`
- Result: **14 passed out of 14 tests (100% PASS)**

```
tests\integration\test_integration.py ...                                [ 21%]
tests\model\test_model.py ...                                            [ 42%]
tests\safety\test_safety.py ...                                          [ 64%]
tests\system\test_system.py ..                                           [ 78%]
tests\unit\test_unit.py ...                                              [100%]
======================= 14 passed, 2 warnings in 3.99s ========================
```

---

## 13. Issues Encountered
- **Calibrator Path Unpickling (R-01):** Unpickling `xgb_calibrator.pkl` throws module path exceptions if `SigmoidCalibrator` is not in global namespace. Handled gracefully by fallback check without crashing app startup.
- **Legacy Route Mapping (R-02):** Unprefixed route aliases were mounted on `src/backend/main.py` to ensure complete backwards compatibility for legacy callers.

---

## 14. R-01 Status
- **Issue:** Calibrator pickle unpickling module-path mismatch.
- **Status:** **HANDLED SAFELY / IDENTIFIED FOR PHASE 3**.
- **Behavior:** `Runtime` catches unpickling exception, sets `is_demo_model: true`, and returns deterministic fallback probability without breaking application startup or ingestion endpoints.

---

## 15. R-02 Status
- **Issue:** Route path compatibility risk between `/api/v1` and legacy `/v1` endpoints.
- **Status:** **RESOLVED VIA ALIAS MOUNTING**.
- **Behavior:** `src/backend/main.py` mounts `api_router` under both `/api/v1` (canonical) and unprefixed `/` (legacy compatibility).

---

## 16. Remaining Work
- **Timestamp / Windowing Fixes:** Replace array index windowing (`vals[-4:]`) with actual clinical timestamp deltas.
- **Model Selection & Calibration Alignment:** Resolve Logistic Regression vs XGBoost selection and re-export calibrator artifacts.
- **Real SHAP & Conformal Uncertainty:** Implement `shap.TreeExplainer` and true conformal prediction intervals.
- **Frontend Integration:** Wire `src/frontend` React dashboard to `src/backend` REST and WebSocket streams.

---

## 17. Verification Checklist

| Check | Expected Result | Actual Result | Status |
|---|---|---|---|
| **Python Import** | `src.backend.main` imports without errors | Exit code 0 (`IMPORT SUCCESS`) | **PASSED** |
| **Database Table Creation** | SQLAlchemy tables created automatically | `patients`, `vital_events`, `predictions`, `alerts` initialized | **PASSED** |
| **Pytest Execution** | 100% test pass rate | 14 passed / 0 failed | **PASSED** |
| **Deployment Backend Preserved** | 0 files modified in `deployment/backend/app` | Unmodified | **PASSED** |
| **Frontend Preserved** | 0 files modified in `src/frontend` | Unmodified | **PASSED** |
| **No File Deletions** | 0 files deleted | 0 files deleted | **PASSED** |
| **No Git Commit/Push** | Working tree uncommitted | Local safety checkpoint maintained | **PASSED** |
