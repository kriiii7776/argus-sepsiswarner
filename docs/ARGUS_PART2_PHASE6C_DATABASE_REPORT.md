# ARGUS Part 2 — Phase 6C: PostgreSQL / SQLAlchemy Database Hardening Report

## 1. Objective
Audit and harden the PostgreSQL + SQLAlchemy persistence layer in the consolidated `src/backend/` implementation. Ensure reliable and consistent persistence for patients, vital events, model predictions, and alerts with proper transaction boundaries, connection pooling, and error handling.

---

## 2. Database Architecture
- **Framework:** SQLAlchemy 2.0 ORM with Declarative Mapping.
- **Dialects Supported:** PostgreSQL 17+ (Production) & SQLite (Lightweight unit testing).
- **Consolidated Location:** `src/backend/db/` (`store.py`, `repositories.py`).
- **ORM Tables:**
  - `PatientRecord` -> `patients`
  - `VitalRecord` -> `vital_events`
  - `PredictionRecord` -> `predictions`
  - `AlertRecord` -> `alerts`

---

## 3. SQLAlchemy Engine Configuration
- Environment-driven URL selection via `DATABASE_URL` or `settings.database_url`.
- Connection pre-ping enabled (`pool_pre_ping=True`) to automatically drop stale connections.
- Configured with clean fallback handling during initial module import.

---

## 4. Connection Pooling
- **PostgreSQL Pool Settings:**
  - `pool_size`: 5 (configurable via `DB_POOL_SIZE`)
  - `max_overflow`: 10 (configurable via `DB_MAX_OVERFLOW`)
  - `pool_timeout`: 30 seconds (configurable via `DB_POOL_TIMEOUT`)
  - `pool_recycle`: 1800 seconds / 30 minutes (configurable via `DB_POOL_RECYCLE`)
  - `pool_pre_ping`: True
- **SQLite Settings:** `StaticPool` for `:memory:` DBs and `check_same_thread=False`.

---

## 5. Session Lifecycle
- Configured `sessionmaker(bind=engine, expire_on_commit=False)`.
- Operations use scoped context managers (`with Session() as s:` or `with Session.begin() as s:`).
- Sessions are strictly ephemeral per operation/request and never shared globally across threads.

---

## 6. Transaction Handling
- Atomic multi-record writes for inference pipeline (`VitalRecord` + `PredictionRecord` + optional `AlertRecord`) managed via `with Session.begin() as s:`.
- Automatic rollback on exception ensures zero orphaned or partial database states.

---

## 7. ORM Model Audit
- **`PatientRecord`:** `patient_id` (String(64), unique, index), `source_system`, `sex_at_birth`, `birth_year`, `created_at` (DateTime TZ).
- **`VitalRecord`:** `patient_id` (String(64), index), `timestamp` (DateTime TZ, index), `payload` (JSON), `source`.
- **`PredictionRecord`:** `patient_id` (String(64), index), `timestamp` (DateTime TZ, index), `risk` (Float), `payload` (JSON), `model_version`.
- **`AlertRecord`:** `patient_id` (String(64), index), `timestamp` (DateTime TZ, index), `severity`, `payload` (JSON).

---

## 8. schema.sql Consistency
- `deployment/database/schema.sql` is identified as a legacy deployment reference blueprint.
- Canonical ORM definitions in `src/backend/db/store.py` (`patients`, `vital_events`, `predictions`, `alerts`) are fully synchronized with runtime requirements. No schema migration required.

---

## 9. Timestamp Handling
- Clinical timestamps from event payloads are explicitly stored in `DateTime(timezone=True)` columns (`TIMESTAMPTZ` in PostgreSQL).
- Clinical time is preserved and never overwritten with database insertion time.

---

## 10. Patient Isolation
- All repository methods (`get`, `vitals`, `predictions`, `alerts`) filter strictly by `patient_id`.
- Verified 100% patient data isolation across queries.

---

## 11. Persistence Completeness
- `InferenceService.ingest()` persists:
  - `VitalRecord` (raw vitals payload)
  - `PredictionRecord` (prediction probability, model version `logistic-regression-v1`, real SHAP attributions, uncertainty summary)
  - `AlertRecord` (emitted `SmartAlertEngine` notifications)
  - `PatientRecord` (auto-registered via `patient_service.require()`)

---

## 12. Database Failure Handling
- Unreachable database or query failures trigger SQLAlchemy exception rollbacks.
- REST API layer re-raises `HTTPException(422)` without leaking database credentials or internal stack traces.
- WebSocket layer returns JSON `{"type": "error", "message": "..."}` cleanly without dropping connection.

---

## 13. Concurrency Handling
- Tested concurrent writes across 5 simultaneous patient threads using `asyncio.gather`.
- Ephemeral session contexts prevent connection collisions or data corruption.

---

## 14. PostgreSQL Test Availability
- **PostgreSQL 17.10** running on `localhost:5432`.
- Created development test database `sepsisguard_test`.
- Performed live end-to-end PostgreSQL verification.

---

## 15. Tests Added
20 new tests added in [`tests/unit/test_database.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/tests/unit/test_database.py):
1. `test_01_engine_initialization`: Engine initializes correctly.
2. `test_02_session_lifecycle`: Ephemeral session lifecycle.
3. `test_03_patient_creation`: Patient record creation.
4. `test_04_patient_retrieval`: Patient retrieval by ID.
5. `test_05_vital_persistence`: `VitalRecord` persistence.
6. `test_06_prediction_persistence`: `PredictionRecord` persistence.
7. `test_07_alert_persistence`: `AlertRecord` persistence.
8. `test_08_patient_scoped_vital_queries`: Scoped vital queries by patient.
9. `test_09_patient_scoped_prediction_queries`: Scoped prediction queries by patient.
10. `test_10_patient_scoped_alert_queries`: Scoped alert queries by patient.
11. `test_11_timestamp_preservation`: Timestamp preservation.
12. `test_12_transaction_commit`: Transaction commit behavior.
13. `test_13_transaction_rollback`: Transaction rollback behavior.
14. `test_14_database_unavailable_handling`: Handling database connection failures.
15. `test_15_session_cleanup_after_failure`: Session cleanup on failure.
16. `test_16_concurrent_writes`: Concurrent writes across patients.
17. `test_17_orm_schema_consistency`: ORM schema validation.
18. `test_18_no_accidental_in_memory_persistence`: Verification of database persistence over in-memory.
19. `test_19_existing_rest_api_still_works`: REST API health integration.
20. `test_20_existing_websocket_flow_still_works`: WebSocket ping/pong integration.

---

## 16. Full Test Results
- **Phase 6B Baseline:** 131 passed, 0 failed.
- **Added (Phase 6C):** 20 passed, 0 failed.
- **Total Test Suite:** 151 passed, 0 failed.

---

## 17. Live PostgreSQL Verification
- **Status:** PASS (Executed against PostgreSQL 17.10 database `sepsisguard_test`).
- **Verified:**
  - Table initialization (`patients`, `vital_events`, `predictions`, `alerts`).
  - Patient creation and retrieval.
  - Vitals event ingestion and `VitalRecord` persistence.
  - Inference execution, `PredictionRecord` persistence (`logistic-regression-v1`, SHAP, unavailable uncertainty).
  - Trajectory Deterioration sequence (5 ticks) -> 2 `AlertRecord` rows persisted in PostgreSQL.
  - Clinical timestamp preservation in `TIMESTAMPTZ` columns.

---

## 18. Files Changed
1. `src/backend/db/store.py`: Added PostgreSQL pool configuration (`pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`), environment URL fallback, and `init_db()` error logging.
2. `tests/unit/test_database.py`: Created 20 database unit and integration tests.
3. `docs/ARGUS_PART2_PHASE6C_DATABASE_REPORT.md`: Created Phase 6C report.

---

## 19. Files Intentionally Untouched
- `deployment/backend/` (all files preserved as legacy reference)
- `src/frontend/` (untouched)
- `model/` (model artifacts and training pipelines untouched)
- `src/backend/services/inference_runtime.py` (InferenceRuntime untouched)
- `src/backend/services/alert_engine.py` (SmartAlertEngine untouched)
- `src/backend/services/shap_service.py` (SHAP implementation untouched)

---

## 20. Remaining Limitations
- Migrations: Alembic migration infrastructure is not yet configured for automatic schema migrations in future deployment phases.
- Multi-region DB replication: Out of scope for Phase 6C.
