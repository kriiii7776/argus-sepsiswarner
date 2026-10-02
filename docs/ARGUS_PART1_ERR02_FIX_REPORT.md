# ARGUS Part 1 ERR-02 Fix Report

## 1. Problem
During multi-patient simulation runs, changing the scenario trajectory for one patient (`PATIENT-A`) involuntarily changed the scenario state for all other active patients (`PATIENT-B`, `PATIENT-C`). For example, assigning `PATIENT-A` to `rapid_deterioration` while leaving `PATIENT-B` unassigned caused `PATIENT-B` to also enter `rapid_deterioration`. This was a critical patient isolation defect.

---

## 2. Root Cause
In `part1/backend/app/services/simulation_service.py`, `SimulationService.__init__()` held a single global singleton instance:
`self.scenario_engine = ScenarioEngine(ScenarioName.STABLE)`

Calling `set_patient_scenario(patient_id, scenario_name)` mutated this single shared instance regardless of `patient_id`. In `_stream_loop()`, the streaming generator iterated over all registered patients and called `effect = self.scenario_engine.update(clock.elapsed_sim_seconds)` using the same shared engine for every patient.

---

## 3. Implementation
Replaced global scenario state with a **per-patient scenario engine map**:
1. Added `self._scenario_engines: Dict[str, ScenarioEngine] = {}` to `SimulationService`.
2. Added `get_scenario_engine(patient_id)` helper that retrieves or dynamically creates an isolated `ScenarioEngine` instance for any given `patient_id`.
3. Created a backwards-compatible `@property def scenario_engine(self)` that returns the `ScenarioEngine` for the active patient.
4. Updated `set_patient_scenario(patient_id, scenario_name)` to assign scenario state machines exclusively to `get_scenario_engine(patient_id)`.
5. Updated `_stream_loop()` to retrieve `engine = self.get_scenario_engine(patient.patient_id)` for each patient individually before generating vital updates.
6. Added automatic lifecycle cleanup in `_stream_loop()` to prune stale engines when patients are removed from `PatientRegistry`.
7. Updated `stop_simulation()` to reset all per-patient scenario engines back to `ScenarioName.STABLE`.
8. Updated `get_clinical_context()` endpoint in `app/api/v1/patients.py` to fetch `get_scenario_engine(patient_id).scenario_name`.

Target Architecture:
```
SimulationService
│
├── PATIENT-A  ──> ScenarioEngine-A (e.g. RAPID_DETERIORATION)
├── PATIENT-B  ──> ScenarioEngine-B (e.g. STABLE)
└── PATIENT-C  ──> ScenarioEngine-C (e.g. RECOVERY)
```

---

## 4. Files Changed
- [`part1/backend/app/services/simulation_service.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/backend/app/services/simulation_service.py)
- [`part1/backend/app/api/v1/patients.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/backend/app/api/v1/patients.py)
- [`part1/backend/app/main.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/backend/app/main.py)
- [`part1/tests/unit/test_err02_scenario_isolation.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/tests/unit/test_err02_scenario_isolation.py) *(new test file)*
- [`docs/ARGUS_PART1_ERR02_FIX_REPORT.md`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/docs/ARGUS_PART1_ERR02_FIX_REPORT.md) *(this report)*

---

## 5. Tests Added
Added 6 focused unit & integration tests in `part1/tests/unit/test_err02_scenario_isolation.py`:
- `test_1_unassigned_patient_remains_stable`: Verifies unassigned patient remains stable when another patient is set to `rapid_deterioration`.
- `test_2_independent_scenario_assignments`: Verifies PATIENT-A -> `rapid_deterioration` and PATIENT-B -> `recovery` remain independent.
- `test_3_patient_a_change_does_not_affect_patient_b`: Verifies changing PATIENT-A to `stable` does not affect PATIENT-B (`recovery`).
- `test_4_patient_b_change_does_not_affect_patient_a`: Verifies changing PATIENT-B to `noisy` does not affect PATIENT-A (`stable`).
- `test_5_emitted_vital_messages_contain_patient_specific_scenarios`: Verifies emitted vital update messages contain patient-specific scenario state tags.
- `test_6_concurrent_simulation_stream_isolation`: Verifies concurrent multi-patient scenario isolation and proper lifecycle engine cleanup upon patient deletion.

---

## 6. Focused Test Results
Command: `$env:PYTHONPATH="part1/backend"; python -m pytest part1/tests/unit/test_err02_scenario_isolation.py -v`
- **Passed**: 6 / 6
- **Failed**: 0
- **Pass Rate**: 100%

---

## 7. Full Part 1 Test Results
Command: `$env:PYTHONPATH="part1/backend"; python -m pytest part1/tests -v`
- **Total Tests**: 106
- **Passed**: 106
- **Failed**: 0
- **Warnings**: 14 (pre-existing third-party deprecation warnings)
- **Pass Rate**: 100%

---

## 8. Runtime Validation
Performed isolated multi-patient simulation scenario test:
- **Phase 1**: Assigned `PATIENT-A` -> `rapid_deterioration` | `PATIENT-B` -> `stable`.
  - Emitted `PATIENT-A` contract state: `ScenarioState.RAPID_DETERIORATION`
  - Emitted `PATIENT-B` contract state: `ScenarioState.STABLE`
- **Phase 2 (Reversed)**: Assigned `PATIENT-A` -> `stable` | `PATIENT-B` -> `rapid_deterioration`.
  - Emitted `PATIENT-A` contract state: `ScenarioState.STABLE`
  - Emitted `PATIENT-B` contract state: `ScenarioState.RAPID_DETERIORATION`

---

## 9. Cross-Patient Isolation
**Cross-patient scenario contamination: NO**
Scenario engines and generated physiological trajectories are now 100% isolated per patient.

---

## 10. Scope Verification
- **ERR-01 persistence logic**: UNCHANGED (`update_patient_status`, `remove_patient`, `clear` untouched)
- **ERR-03 random seed logic**: UNCHANGED (`seed=42` left hardcoded in generator loop)
- **ERR-04 exception handling**: UNCHANGED (`_save_to_disk` and `_load_from_disk` untouched)
- **Part 2 source & ML pipeline**: UNCHANGED
- **Part 3 Flutter & Android**: UNCHANGED

---

## 11. Git Verification

### Git Status Output
```
 M part1/backend/app/api/v1/patients.py
 M part1/backend/app/main.py
 M part1/backend/app/services/simulation_service.py
?? docs/ARGUS_PART1_ERR02_FIX_REPORT.md
?? part1/tests/unit/test_err02_scenario_isolation.py
```

### Diff Summary
- Modified `SimulationService` in `simulation_service.py` to maintain `_scenario_engines: Dict[str, ScenarioEngine]`.
- Updated `patients.py` to retrieve patient-specific scenario names for clinical context queries.
- Updated `main.py` demo mode startup to call `set_patient_scenario()`.
- Added 6 focused unit tests in `test_err02_scenario_isolation.py`.
- Generated fix documentation report in `docs/ARGUS_PART1_ERR02_FIX_REPORT.md`.
