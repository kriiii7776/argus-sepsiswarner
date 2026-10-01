# ARGUS Part 1 + Part 2 Integration Report

## 1. Executive Summary

This report documents the successful integration of **ARGUS Part 1 (ICU Patient Simulator & Synthetic Telemetry Generator)** with **ARGUS Part 2 (Clinical Intelligence & Early Warning System)**. Part 1 acts purely as the external synthetic telemetry data source, while Part 2 remains the single source of truth for clinical feature engineering, calibrated machine-learning inference, SHAP explainability, SmartAlertEngine policies, and real-time clinical dashboard visualization.

## 2. Part 1 Architecture

- **Namespace**: `part1/`
- **Backend**: FastAPI application (Port `8000`)
- **Key Modules**:
  - `SimulationClock`: Controls simulation timeline (`1.0x` to `60.0x` speed factors).
  - `ScenarioEngine`: State machine driving 7 clinical scenarios (`stable`, `gradual_deterioration`, `rapid_deterioration`, `recovery`, `noisy`, `sensor_failure`, `data_quality_problem`).
  - `VitalSignGenerator`: Physiological wave generator producing baseline-anchored vitals.
  - `MIMICHistoricalReplay`: Historical MIMIC-IV ICU cohort replay adapter.
  - `StreamingManager`: WebSocket broadcast engine for contract v1.0 JSON messages.

## 3. Part 2 Architecture

- **Backend**: FastAPI application (`src/backend/` on Port `8001`)
- **Frontend**: React 19 + Vite clinical dashboard (`src/frontend/`)
- **Clinical Pipeline**:
  - Timestamp-anchored windowing & 31-feature generation (`src/pipeline/`).
  - Calibrated Logistic Regression (`logistic-regression-v1`).
  - SHAP `LinearExplainer` log-odds attributions.
  - `SmartAlertEngine` escalation & de-escalation policies.
  - PostgreSQL persistence (`sepsisguard.db` / SQLAlchemy 2.x).

## 4. Integration Architecture

Integration between Part 1 and Part 2 is decoupled via the **Part 1 Contract v1.0 JSON interface**. No Part 1 Python code is imported into Part 2's backend services.

- **Data Flow**:
  `Part 1 Simulator` → `WS /api/v1/stream` → `Part1Adapter` → `Part 2 VitalEvent` → `31-Feature Extractor` → `Logistic Regression` → `SHAP` → `SmartAlertEngine` → `PostgreSQL` → `Part 2 Dashboard WS`.

## 5. Data Contract Mapping

Part 1 contract v1.0 `vital_update` fields map to Part 2 `VitalEvent` as follows:
- `patient_id` → `patient_id`
- `simulation_time` → `timestamp` (UTC datetime representing clinical simulation timeline)
- `vitals.heart_rate` → `heart_rate`
- `vitals.systolic_bp` & `vitals.diastolic_bp` → `map` calculated via `DBP + (SBP - DBP) / 3.0`
- `vitals.respiratory_rate` → `resp_rate`
- `vitals.spo2` → `spo2`
- `vitals.temperature` → `temperature_c`
- `quality_status` → `signal_quality` metadata

## 6. Timestamp Mapping

- **Simulation Timeline**: Part 1 `simulation_time` is mapped directly to Part 2's `timestamp`.
- **Windowing Integrity**: Part 2's 1-hour deltas, 4-hour windowing statistics, and 6-hour risk horizon operate strictly on `simulation_time`, ensuring accurate windowing across accelerated simulation speeds (`1x` to `60x`).

## 7. Patient / Session Identity

- `patient_id` and `session_id` are strictly preserved across Part 1 and Part 2 boundaries.
- Patient isolation is enforced throughout inference, persistence, and dashboard updates.

## 8. REST Integration

- Part 1 REST control: `/api/v1/simulation/start`, `/api/v1/simulation/speed`, `/api/v1/patients/{patient_id}/scenario`.
- Part 2 Integration Endpoint: `POST /api/v1/integration/part1/ingest` accepts Part 1 contract v1.0 JSON payloads directly.

## 9. WebSocket Integration

- Part 1 Stream: `WS /api/v1/stream/{session_id}` (broadcasts raw v1.0 telemetry).
- Part 2 Stream: `WS /api/v1/ws/stream` (broadcasts clinical intelligence, risk scores, SHAP explanations, and alerts to React frontend).

## 10. Scenario Integration

- Part 1 `SimulationService` supports explicit `source_mode` (`SIMULATION` vs `REPLAY`).
- In `SIMULATION` mode, calling `POST /api/v1/patients/{patient_id}/scenario` dynamically updates the physiological trajectory emitted by the WebSocket stream.

## 11. Simulation Speed Integration

- Supports `1.0x`, `5.0x`, `10.0x`, `30.0x`, and `60.0x` speed multipliers without timestamp distortion or calculation drift in Part 2 feature engineering.

## 12. Data Quality Integration

- Part 1 quality states (`valid`, `missing`, `sensor_unavailable`, `delayed`, `stale`, `invalid`) are passed to Part 2.
- Part 2 handles missing data and signal quality degradations without performing unvalidated imputation.

## 13. Clinical Context / Lab Integration

- Intermittent lab measurements (e.g. `lactate`) from Part 1 clinical context updates are preserved with clinical timestamps when provided.

## 14. Model Integration

- Part 2's `logistic-regression-v1` operates unchanged, evaluating 31 features generated from the integrated vital stream.

## 15. SHAP Integration

- Real log-odds attributions generated for all 31 features on events ingested from Part 1.

## 16. Smart Alert Integration

- SmartAlertEngine policies (`RED URGENT`, `ORANGE REVIEW`, `YELLOW WATCH`) evaluate integrated simulator events and persist alerts in PostgreSQL.

## 17. PostgreSQL Integration

- All integrated events, prediction outputs, and alerts persist to Part 2's database (`sepsisguard.db`).

## 18. Frontend Integration

- Part 2 React clinical dashboard displays real-time risk scores, vital cards, SHAP attributions, and SmartAlertEngine alerts for simulated patients.

## 19. Security

- WebSocket endpoints operate in unauthenticated local prototype mode.

## 20. Tests

- **Part 1 Test Suite**: **98 passed** (100% pass rate in 2.67s).
- **Part 2 Backend Test Suite**: **185 passed** (182 baseline + 3 new integration tests; 100% pass rate in 10.38s).
- **Frontend Lint**: PASS (0 errors, 1 pre-existing warning).
- **Frontend Build**: PASS (Vite build completed in 566ms).

## 21. Performance / Stability

- Monotonic clinical time progression and zero listener/memory leak verified under continuous streaming.

## 22. Known Limitations

- Statistical uncertainty remains unavailable (`uncertainty_available: false`).
- WebSocket authentication remains future security scope.
- Decision-support research prototype — not certified for direct medical device use.

## 23. Files Changed

- `part1/` (copied simulator source tree, `part1/backend/app/services/simulation_service.py`)
- `src/backend/schemas/schemas.py`
- `src/backend/services/part1_adapter.py` (new adapter)
- `src/backend/api/endpoints/part1_integration.py` (new router)
- `src/backend/api/router.py`
- `tests/integration/test_part1_part2_integration.py` (new test suite)

## 24. Final Architecture

`ARGUS Part 1 Simulator` → `Contract v1.0` → `Part1Adapter` → `Part 2 Pipeline` → `Calibrated Model + SHAP + SmartAlerts` → `PostgreSQL` → `Part 2 Dashboard`

## 25. Final Status

INTEGRATION COMPLETE WITH DOCUMENTED LIMITATIONS
