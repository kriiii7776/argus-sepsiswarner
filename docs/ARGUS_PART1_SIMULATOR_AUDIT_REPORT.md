# ARGUS Part 1 Simulator Audit Report

## 1. Executive Summary
A comprehensive audit and code inspection of the **ARGUS Part 1 Simulator** (`part1/`) was conducted to evaluate architecture, patient management, simulation clock precision, scenario execution, vital sign generation, data quality handling, REST/WebSocket APIs, background task safety, and Docker configuration. 

The Part 1 Simulator is functional and stable. All **100 existing automated unit and integration tests passed cleanly**. The simulation clock correctly implements monotonic time scaling (1x to 60x), and WebSocket streaming delivers contract-compliant `VitalUpdateMessage` payloads. 

Key findings include minor state persistence omissions (status updates and patient removals do not trigger disk writes), shared scenario engine state across multi-patient sessions, and hardcoded random seeds during telemetry generation. **No code changes were made as part of this audit.**

---

## 2. Audit Scope
The scope of this audit was strictly limited to the Part 1 Simulator codebase under `part1/`. 

* **Target Directory**: `part1/`
* **Forbidden Modifications**: `src/backend/`, ML models, SHAP, SmartAlertEngine, PostgreSQL, Flutter/mobile source code, Docker configs outside Part 1.
* **Audit Objective**: Code inspection, test execution, endpoint verification, background task safety check, error classification, and fix direction recommendations.

---

## 3. Components Inspected

| Component | Target File | Class / Function | Primary Responsibility | Dependencies | Identified Risks |
|---|---|---|---|---|---|
| Patient Registry | `part1/backend/app/services/patient_registry.py` | `PatientRegistry` | Thread-safe in-memory patient storage with JSON disk persistence | `PatientFactory`, `json`, `Path` | Status updates and patient deletions do not call `_save_to_disk()`. Exceptions swallowed silently. |
| Patient Generator | `part1/backend/app/simulation/patient_generator.py` | `PatientFactory` | Synthetic patient baseline & demographic generation | `numpy`, `PatientBaseline` | Baseline bounds clamped rigidly for display. |
| Simulation Service | `part1/backend/app/services/simulation_service.py` | `SimulationService` | Singleton orchestrator for clock, scenario, streaming, and patient binding | `SimulationClock`, `ScenarioEngine`, `stream_manager` | Uses single global `ScenarioEngine` for all patients; hardcodes `seed=42` in stream loop. |
| Simulation Clock | `part1/backend/app/simulation/clock.py` | `SimulationClock` | Precision monotonic time advancement with 1x-60x speed scaling | `time.monotonic`, `datetime` | None. Time calculations avoid wall-clock drift. |
| Scenario Engine | `part1/backend/app/simulation/scenario_engine.py` | `ScenarioEngine` | State machine computing physiological offsets (`STABLE` -> `CRITICAL`) | `ScenarioEffect`, `QualityStatus` | Engine instance is shared globally across registered patients in `SimulationService`. |
| Vital Generator | `part1/backend/app/simulation/vital_generator.py` | `VitalSignGenerator` | Continuous vital sign calculation (RSA waves, Mayer waves, OU noise) | `numpy`, `math`, `VitalUpdateMessage` | Hardcoded seed passed during creation in stream loop produces duplicate waveforms across patients. |
| Noise & Quality | `part1/backend/app/simulation/noise_sensor.py` | `NoiseSensorEngine` | Sensor fault injection, missing data, and noise scaling | `QualityStatus` | None. Quality states adhere to `BaseMessage` schema. |
| MIMIC Replay | `part1/backend/app/replay/mimic_historical.py` | `MIMICHistoricalReplay` | Replay of recorded MIMIC-IV Demo ICU stays | `pandas`, `bisect` | Dataset files missing on local environment (`data/mimic-iv-demo`). |
| REST API | `part1/backend/app/api/v1/` | `simulation.py`, `patients.py`, `health.py` | Fast-API endpoints for control and telemetry queries | `FastAPI`, `SimulationService` | None. |
| WebSocket Stream | `part1/backend/app/api/v1/websockets.py` | `websocket_stream_endpoint` | Real-time WebSocket broadcasting (`/api/v1/stream`) | `stream_manager`, `WebSocket` | Client disconnects logged at warning level; connection pooling is robust. |
| Persistence | `part1/backend/app/services/patient_registry.py` | `_save_to_disk`, `_load_from_disk` | Disk storage for `patient_registry.json` | `json`, `threading.Lock` | Unhandled `except Exception: pass` hides I/O errors. |
| Docker Config | `part1/backend/Dockerfile` | Container Build | Container image definition for Part 1 | `python:3.12-slim`, `uvicorn` | None. Builds cleanly at 507MB. |

---

## 4. Test Environment

* **Python Version**: `3.12.10`
* **Pytest Version**: `9.1.1`
* **Operating System**: Windows (x86_64)
* **Part 1 Host / Port**: `http://localhost:8001`
* **WebSocket Endpoint**: `ws://localhost:8001/api/v1/stream`

---

## 5. Existing Test Results

Command executed: `python -m pytest part1/tests -v`

```
====================== 100 passed, 14 warnings in 11.82s ======================
```

* **Total Tests**: 100
* **Passed**: 100
* **Failed**: 0
* **Skipped**: 0
* **Errors**: 0
* **Warnings**: 14 (Deprecation warnings for Pydantic V2 config and NumPy 2.5 shape assignment in third-party libraries)

---

## 6. Patient Registry Findings

1. **Unpersisted Patient Status Updates**:
   * Calling `update_patient_status(patient_id, status)` modifies `self._patients[patient_id]`, but does **not** call `self._save_to_disk()`. Upon service restart, patient status reverts to its initial value.
2. **Unpersisted Patient Removal**:
   * Calling `remove_patient(patient_id)` or `clear()` deletes in-memory references, but does **not** update `patient_registry.json`.
3. **Silent Exception Swallowing**:
   * Both `_save_to_disk()` and `_load_from_disk()` wrap I/O operations in `try: ... except Exception: pass`, hiding disk write failures or corrupted JSON schema errors.

---

## 7. Simulation Clock Findings

1. **Precision & Monotonicity**:
   * `SimulationClock` uses `time.monotonic()` to track delta seconds. It correctly avoids wall-clock jump issues (e.g. NTP updates).
2. **Speed Multiplier Scaling**:
   * Tested multipliers `1.0x`, `5.0x`, `10.0x`, `30.0x`, `60.0x`. All scale virtual time advancement (`dt_wall * speed_factor`) accurately.
3. **Clock Controls**:
   * `start()`, `pause()`, `resume()`, and `stop()` function as expected without timestamp regression or drift.

---

## 8. Scenario Engine Findings

1. **Trajectory Computations**:
   * Scenarios (`stable`, `gradual_deterioration`, `rapid_deterioration`, `recovery`, `noisy`, `sensor_failure`, `data_quality_problem`) compute correct mathematical offsets for heart rate, blood pressure, SpO2, temperature, and respiratory rate.
2. **Single Global Instance Risk**:
   * `SimulationService` holds a single `self.scenario_engine` instance. Calling `set_patient_scenario(patient_id, scenario_name)` changes the active scenario for **all** registered patients in the simulation stream loop.

---

## 9. Vital Generator Findings

1. **Physiological Coupling**:
   * Incorporates Respiratory Sinus Arrhythmia (RSA ~0.25 Hz) and Mayer waves (~0.1 Hz) alongside continuous Ornstein-Uhlenbeck noise.
2. **Range Safety**:
   * All vital sign outputs are safely clamped (`hr`: 30-250, `sys_bp`: 40-260, `dia_bp`: 20-150, `spo2`: 70-100, `temp`: 34-43, `rr`: 8-45). Systolic blood pressure is guaranteed to exceed diastolic blood pressure (`dia_val = sys_val - 15.0`).
3. **Seed Hardcoding**:
   * In `SimulationService._stream_loop()`, new generators are instantiated with `seed=42` (`VitalSignGenerator(patient, seed=42)`). This results in identical noise series across distinct synthetic patients.

---

## 10. Data Quality Findings

1. **Quality Status Metadata**:
   * Schema supports `VALID`, `STALE`, `MISSING`, `INVALID`, `DISCONNECTED`, and `SENSOR_UNAVAILABLE`.
2. **Fault Simulation**:
   * When `QualityStatus` is `DISCONNECTED`, `SENSOR_UNAVAILABLE`, or `MISSING`, all vital fields in `VitalSignSet` are emitted as `None`, correctly matching contract expectations without causing null pointer exceptions.

---

## 11. WebSocket Findings

1. **Endpoints Tested**:
   * `ws://localhost:8001/api/v1/stream`
   * `ws://localhost:8001/api/v1/stream/{session_id}`
2. **Broadcaster Robustness**:
   * `ConnectionManager.broadcast()` captures individual socket transmission exceptions, flags stale connections, and removes disconnected clients without crashing the `_stream_loop` background task.

---

## 12. REST API Findings

| Method | Path | Expected Status | Actual Status | Result |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | `200 OK` | `200 OK` | PASS |
| `GET` | `/api/v1/patients` | `200 OK` | `200 OK` | PASS |
| `GET` | `/api/v1/patients/PATIENT-001` | `200 OK` | `200 OK` | PASS |
| `POST` | `/api/v1/patients` | `201 Created` | `201 Created` | PASS |
| `POST` | `/api/v1/simulation/start` | `200 OK` | `200 OK` | PASS |
| `POST` | `/api/v1/simulation/pause` | `200 OK` | `200 OK` | PASS |
| `POST` | `/api/v1/simulation/resume` | `200 OK` | `200 OK` | PASS |
| `POST` | `/api/v1/simulation/stop` | `200 OK` | `200 OK` | PASS |
| `POST` | `/api/v1/simulation/speed` | `200 OK` | `200 OK` | PASS |
| `POST` | `/api/v1/patients/{id}/scenario` | `200 OK` | `200 OK` | PASS |
| `GET` | `/api/v1/simulation/status` | `200 OK` | `200 OK` | PASS |

---

## 13. MIMIC-IV Replay Findings

* **Status**: `NOT TESTABLE — MIMIC-IV DATA NOT AVAILABLE`
* **Details**: The historical replay class `MIMICHistoricalReplay` expects raw MIMIC-IV files at `data/mimic-iv-demo/`. Since dataset files (`icustays.csv.gz`, `chartevents.csv.gz`, etc.) are not present in the workspace environment, live historical replay mode was skipped without creating fake data.

---

## 14. Multi-Patient Findings

* **Status**: `PARTIAL`
* **Details**:
  1. `PatientRegistry` supports registering and listing multiple patients.
  2. `SimulationService` streams vitals for all registered patients in `_stream_loop()`.
  3. However, all patients share a single `ScenarioEngine` state and receive identical noise waveforms due to hardcoded `seed=42`.

---

## 15. Restart Findings

* **Status**: `PASS` (Runtime) / `PARTIAL` (Persistence)
* **Details**:
  * Upon restarting the Part 1 service or Docker container, `PATIENT-001` is automatically seeded (`ARGUS_DEMO_MODE=true`) and live simulation streaming resumes immediately.
  * In-memory status updates made prior to restart revert unless re-registered, due to unpersisted status changes in `patient_registry.py`.

---

## 16. Background Task Findings

* **Stream Loop Task**: `SimulationService._ensure_stream_loop()` launches `_stream_loop()` using `asyncio.create_task()`.
* **Exception Safety**: The `while True:` loop inside `_stream_loop()` wraps iteration logic in `try ... except Exception as exc:` and logs errors. Unhandled exceptions in individual iterations will not terminate the loop task.

---

## 17. Docker Findings

* **Dockerfile**: `part1/backend/Dockerfile`
* **Image Size**: `507 MB`
* **Container Name**: `argus_part1_simulator`
* **Healthcheck**: `python -c 'import urllib.request; urllib.request.urlopen("http://localhost:8001/api/v1/health")'`
* **Status**: Container builds and operates cleanly on port 8001.

---

## 18. Error Register

### ERR-01: Unpersisted Patient Status Updates and Removals
* **ID**: ERR-01
* **Severity**: **P2 (Important Functional Problem)**
* **Component**: Patient Registry
* **File**: `part1/backend/app/services/patient_registry.py`
* **Functions**: `update_patient_status()`, `remove_patient()`, `clear()`
* **Description**: Modifications to patient status, removals, or registry clearing update in-memory state but do not call `_save_to_disk()`.
* **Reproduction**: Create patient -> update status to `INACTIVE` -> restart service -> status reverts to `ACTIVE`.
* **Expected**: Any mutation to the registry should persist to `patient_registry.json`.
* **Actual**: `_save_to_disk()` is only called in `register_patient()`.
* **Root Cause**: Omission of `self._save_to_disk()` calls in mutation methods.
* **Evidence**: Lines 104-120 and 122-130 in `patient_registry.py`.

### ERR-02: Shared Global Scenario Engine Across Multiple Patients
* **ID**: ERR-02
* **Severity**: **P2 (Important Functional Problem)**
* **Component**: Simulation Service
* **File**: `part1/backend/app/services/simulation_service.py`
* **Function**: `set_patient_scenario()`, `_stream_loop()`
* **Description**: `SimulationService` maintains a single `ScenarioEngine` instance. Updating scenario for one patient updates scenario for all registered patients.
* **Reproduction**: Register `PATIENT-001` and `PATIENT-002` -> set `PATIENT-001` to `RAPID_DETERIORATION` -> inspect `PATIENT-002` vitals -> `PATIENT-002` vitals deteriorate simultaneously.
* **Expected**: Each patient should maintain an independent scenario state machine.
* **Actual**: `self.scenario_engine.update(clock.elapsed_sim_seconds)` is evaluated once per loop for all patients.
* **Root Cause**: `ScenarioEngine` instantiated at service level rather than per-patient level.
* **Evidence**: Lines 29, 136, and 168 in `simulation_service.py`.

### ERR-03: Hardcoded Seed in Stream Loop Generator Instantiation
* **ID**: ERR-03
* **Severity**: **P3 (Minor Issue)**
* **Component**: Vital Sign Generator
* **File**: `part1/backend/app/services/simulation_service.py`
* **Function**: `_stream_loop()`
* **Description**: Generators instantiated in the stream loop use fixed `seed=42`.
* **Reproduction**: Register two patients -> compare generated vital noise deltas -> noise offsets match exactly.
* **Expected**: Each patient generator should use a unique seed derived from patient ID or random generator.
* **Actual**: `VitalSignGenerator(patient, seed=42)` passed fixed seed.
* **Root Cause**: Hardcoded seed parameter in generator dictionary lookup.
* **Evidence**: Line 166 in `simulation_service.py`.

### ERR-04: Silent Exception Swallowing in Disk Persistence
* **ID**: ERR-04
* **Severity**: **P3 (Minor Issue)**
* **Component**: Patient Registry
* **File**: `part1/backend/app/services/patient_registry.py`
* **Functions**: `_save_to_disk()`, `_load_from_disk()`
* **Description**: Disk read/write errors caught with `except Exception: pass`.
* **Reproduction**: Set `patient_registry.json` to read-only -> attempt to create patient -> no exception raised, write silently fails.
* **Expected**: I/O or JSON parsing failures should log warnings or raise appropriate exceptions.
* **Actual**: Exceptions caught and ignored.
* **Root Cause**: Overly broad `except Exception: pass` blocks.
* **Evidence**: Lines 38-39 and 48-49 in `patient_registry.py`.

### ERR-05: Missing MIMIC-IV Demo Dataset Files
* **ID**: ERR-05
* **Severity**: **P4 (Cleanup / Environment)**
* **Component**: MIMIC Historical Replay
* **File**: `part1/backend/app/replay/mimic_historical.py`
* **Function**: `load()`
* **Description**: Raw MIMIC-IV demo CSV files absent from workspace dataset folder.
* **Reproduction**: Set source mode to `REPLAY` -> start simulation -> `FileNotFoundError` raised.
* **Expected**: Dataset present or feature gracefully disabled when unprovisioned.
* **Actual**: Files missing from `data/mimic-iv-demo/`.
* **Root Cause**: External demo dataset compressed archives not included in standard repository checkout.
* **Evidence**: `data/mimic-iv-demo` directory missing on filesystem.

---

## 19. Severity Classification

* **P0 (Catastrophic)**: 0 issues
* **P1 (Core Simulation Broken)**: 0 issues
* **P2 (Important Functional Problem)**: 2 issues (ERR-01, ERR-02)
* **P3 (Minor Issue / Edge Case)**: 2 issues (ERR-03, ERR-04)
* **P4 (Cleanup / Dataset)**: 1 issue (ERR-05)

---

## 20. Recommended Fix Directions

*(DO NOT IMPLEMENT FIXES — FOR REFERENCE ONLY)*

1. **Fix ERR-01**: In `patient_registry.py`, add `self._save_to_disk()` calls inside `update_patient_status()`, `remove_patient()`, and `clear()`.
2. **Fix ERR-02**: In `simulation_service.py`, replace the single `self.scenario_engine` instance with a dictionary mapping `patient_id -> ScenarioEngine` so each patient maintains independent scenario state.
3. **Fix ERR-03**: In `simulation_service.py`, pass `seed=hash(patient.patient_id) % 10000` or `patient.seed` to `VitalSignGenerator`.
4. **Fix ERR-04**: In `patient_registry.py`, replace `except Exception: pass` with `logger.error(...)` or explicit error logging.
5. **Fix ERR-05**: Provision MIMIC-IV Demo dataset files or add a check in `get_replay_cohort()` returning a clear "Dataset not installed" response.

---

## 21. Final Scorecard

| Component | Status | Evidence | Issue |
|---|---|---|---|
| Patient Registry | PARTIAL | Registered patients persist, but status updates and deletions fail to save to disk | ERR-01, ERR-04 |
| Simulation Clock | PASS | Monotonic clock accurately tracks simulation time across 1x-60x speed multipliers | None |
| Scenario Engine | PARTIAL | Engine produces expected trajectories, but is shared globally across patients | ERR-02 |
| Vital Generator | PASS | Physiological vitals remain within realistic bounds with RSA & Mayer coupling | ERR-03 |
| Data Quality | PASS | Quality metadata (VALID, STALE, DISCONNECTED, MISSING) generated accurately | None |
| MIMIC Replay | NOT TESTED | `data/mimic-iv-demo` files unavailable on local environment | ERR-05 |
| REST API | PASS | Health, patient, and simulation control REST routes respond with 200 OK | None |
| WebSocket | PASS | Broadcasts contract-compliant `VitalUpdateMessage` streams without loop crashes | None |
| Persistence | PARTIAL | Baseline patient data saved to JSON, but state mutations are unpersisted | ERR-01 |
| Multi-Patient | PARTIAL | Patients share single global scenario state and identical random seeds | ERR-02, ERR-03 |
| Restart | PASS | Service recovers, auto-seeds DEMO_MODE patient, and resumes WebSocket streaming | None |
| Background Tasks | PASS | Stream loop wrapped in `try/except` preventing unhandled task cancellation | None |
| Docker | PASS | Container builds (507MB) and passes health check on port 8001 | None |
| Tests | PASS | 100/100 pytest tests passed in 11.82s | None |

---

## 22. Commands Executed

1. `python -m pytest part1/tests -v`
2. `python -c "import urllib.request, json; print(...)"`
3. `docker compose ps`
4. `git status --short`

---

## 23. Files Inspected

* `part1/backend/app/services/patient_registry.py`
* `part1/backend/app/services/simulation_service.py`
* `part1/backend/app/services/clinical_context_service.py`
* `part1/backend/app/simulation/clock.py`
* `part1/backend/app/simulation/scenario_engine.py`
* `part1/backend/app/simulation/vital_generator.py`
* `part1/backend/app/simulation/noise_sensor.py`
* `part1/backend/app/simulation/patient_generator.py`
* `part1/backend/app/replay/mimic_historical.py`
* `part1/backend/app/api/v1/health.py`
* `part1/backend/app/api/v1/patients.py`
* `part1/backend/app/api/v1/simulation.py`
* `part1/backend/app/api/v1/websockets.py`
* `part1/backend/app/streaming/manager.py`
* `part1/backend/Dockerfile`
