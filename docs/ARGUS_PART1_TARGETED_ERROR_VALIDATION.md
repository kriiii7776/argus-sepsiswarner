# ARGUS Part 1 Targeted Error Validation

This document presents targeted runtime validation results for the four primary architectural defects identified in the ARGUS Part 1 Simulator backend (`part1/backend/app`). All tests were executed in an isolated runtime environment without modifying project source code, existing tests, or configuration.

---

## ERR-01 — Patient Persistence

### Test Performed
1. **Status Update Persistence Test**:
   - Created temporary patient `PAT-ERR01-A` with `status=ACTIVE`.
   - Confirmed initial record was saved to disk (`patient_registry.json`).
   - Updated status to `DISCHARGED` via `PatientRegistry.update_patient_status()`.
   - Inspected `patient_registry.json` on disk and reloaded a new `PatientRegistry` instance from disk to check whether the updated status persisted.
2. **Patient Removal Persistence Test**:
   - Created patient `PAT-ERR01-B`.
   - Called `PatientRegistry.remove_patient("PAT-ERR01-B")`.
   - Inspected `patient_registry.json` on disk and reloaded `PatientRegistry` from disk.
3. **Registry Clear Persistence Test**:
   - Called `PatientRegistry.clear()`.
   - Inspected `patient_registry.json` on disk and reloaded `PatientRegistry` from disk.

### Expected Result
- Updating patient status should rewrite `patient_registry.json` so that reloading registry from disk preserves `status=DISCHARGED`.
- Removing a patient should update `patient_registry.json` so that reloading registry from disk shows the patient was deleted.
- Calling `clear()` should empty `patient_registry.json` on disk so that reloading registry yields an empty registry (0 patients).

### Actual Result
- **Status Update**: In-memory patient status updated to `discharged`, but `patient_registry.json` remained `active`. Upon reloading from disk, the status reverted to `active` (Persisted? `False`).
- **Patient Removal**: In-memory patient count decreased, but `PAT-ERR01-B` remained present inside `patient_registry.json`. Reloading from disk restored `PAT-ERR01-B` (Persisted? `False`).
- **Registry Clear**: In-memory registry cleared to 0 patients, but `patient_registry.json` retained all previously written patients. Reloading from disk restored 2 patients (Persisted? `False`).

### Confirmed / Not Confirmed
**CONFIRMED BUG: YES**

### Evidence
In `part1/backend/app/services/patient_registry.py`:
- `register_patient()` calls `self._save_to_disk()` (line 57).
- `update_patient_status()` (lines 104–120) mutates `self._patients` but **does not call `self._save_to_disk()`**.
- `remove_patient()` (lines 122–130) deletes keys from `self._patients` but **does not call `self._save_to_disk()`**.
- `clear()` (lines 132–137) clears `self._patients` but **does not call `self._save_to_disk()`**.

---

## ERR-02 — Scenario Isolation

### Test Setup
1. Instantiated `SimulationService` and populated `PatientRegistry` with two distinct patients: `PATIENT-A` (`SESS-A`) and `PATIENT-B` (`SESS-B`).
2. Called `service.set_patient_scenario("PATIENT-A", ScenarioName.RAPID_DETERIORATION)`.
3. Observed scenario state and physiological vitals emitted by `VitalSignGenerator` for both `PATIENT-A` and `PATIENT-B`.
4. Reversed scenario assignment: called `service.set_patient_scenario("PATIENT-B", ScenarioName.RAPID_DETERIORATION)` and observed emitted vitals for both patients.

### Patient A Results
- **Step 1 (PATIENT-A set to `rapid_deterioration`)**: Emitted `scenario_state: ScenarioState.RAPID_DETERIORATION`, HR = 95.2 bpm, SysBP = 96.8 mmHg.
- **Step 2 (Reversed scenario)**: Emitted `scenario_state: ScenarioState.RAPID_DETERIORATION`, HR = 106.1 bpm.

### Patient B Results
- **Step 1 (PATIENT-B left unassigned/intended stable)**: Emitted `scenario_state: ScenarioState.RAPID_DETERIORATION`, HR = 101.4 bpm, SysBP = 98.6 mmHg. **Patient B was forced into rapid deterioration without being assigned to it.**
- **Step 2 (PATIENT-B set to `rapid_deterioration`)**: Emitted `scenario_state: ScenarioState.RAPID_DETERIORATION`, HR = 111.2 bpm.

### Cross-Contamination Result
**Cross-patient scenario contamination: YES**

### Confirmed / Not Confirmed
**CONFIRMED BUG: YES**

### Evidence
In `part1/backend/app/services/simulation_service.py`:
- `SimulationService.__init__()` instantiates a single shared scenario engine: `self.scenario_engine = ScenarioEngine(ScenarioName.STABLE)` (line 29).
- `set_patient_scenario(patient_id, scenario_name)` (lines 123–138) ignores the `patient_id` parameter scope and mutates the single shared `self.scenario_engine`.
- In `_stream_loop()` (lines 161–175), every patient in the registry receives updates from the exact same shared scenario engine: `effect = self.scenario_engine.update(clock.elapsed_sim_seconds)`.

---

## ERR-03 — Random Seed

### Generator Behaviour
`SimulationService._stream_loop()` initializes physiological generators for registered patients lazily when generating continuous vitals.

### Seed Behaviour
In `simulation_service.py` line 166, generator instantiation hardcodes the random seed parameter:
```python
if patient.patient_id not in self._generators:
    self._generators[patient.patient_id] = VitalSignGenerator(patient, seed=42)
```

### Observed Result
- Created two patients (`PAT-SEED-A` and `PAT-SEED-B`) with identical baseline age and standard profile.
- Initialized two `VitalSignGenerator` instances using `seed=42`.
- Generated vitals over 10 consecutive ticks: **10 out of 10 samples (100%) were 100% IDENTICAL** in Heart Rate, Blood Pressure, and SpO2 values.
- Pseudo-random Ornstein-Uhlenbeck noise drift and physiological phase offsets (`_hr_phase`, `_rr_phase`, `_bp_phase`, `_temp_phase`) were identical across distinct patients.

### Confirmed / Not Confirmed
**CONFIRMED BUG: YES**

### Evidence
- `simulation_service.py` line 166 passes `seed=42` to all `VitalSignGenerator` instantiations.
- `VitalSignGenerator.__init__()` in `part1/backend/app/simulation/vital_generator.py` uses `self.rng = np.random.default_rng(seed)` (line 35). Because `seed=42` is fixed, every patient generator produces identical pseudo-random noise arrays and phase offsets.

---

## ERR-04 — Persistence Error Handling

### Silent Handlers Found
In `part1/backend/app/services/patient_registry.py`:
1. **`_save_to_disk()`** (lines 34–39):
   ```python
   def _save_to_disk(self) -> None:
       try:
           data = [p.model_dump(mode="json") for p in self._patients.values()]
           self._persistence_file.write_text(json.dumps(data, indent=2))
       except Exception:
           pass
   ```
2. **`_load_from_disk()`** (lines 41–49):
   ```python
   def _load_from_disk(self) -> None:
       try:
           if self._persistence_file.exists():
               raw = json.loads(self._persistence_file.read_text())
               for item in raw:
                   patient = Patient.model_validate(item)
                   self._patients[patient.patient_id] = patient
       except Exception:
           pass
   ```

### Failure Behaviour
1. **Write Failures**: When disk save fails (e.g. read-only filesystem, permission denied, OS I/O error), `_save_to_disk()` silently swallows the exception (`except Exception: pass`). In-memory updates succeed while disk state remains stale. No logs, warnings, or exceptions are emitted.
2. **Load Failures**: When loading a corrupted JSON file or invalid schema (`json.JSONDecodeError` / `ValidationError`), `_load_from_disk()` silently swallows the exception and leaves `_patients` empty without notifying operators or logging an error.

### Confirmed / Not Confirmed
**CONFIRMED BUG: YES**

### Evidence
- Executed isolated runtime tests attempting to write to a non-writable file path (`C:\Windows\System32\argus_test_invalid_permission.json`). `_save_to_disk()` failed silently without raising any exception or logging an error message.
- Executed isolated runtime tests loading from a corrupted JSON file (`{ CORRUPTED INVALID JSON CONTENT ::: `). `_load_from_disk()` failed silently, swallowed the exception, and initialized an empty registry without logging any alert or error message.

---

## Final Decision

| Error | Static Finding | Runtime Finding | Confirmed? | Severity |
|-------|----------------|-----------------|------------|----------|
| **ERR-01** | `update_patient_status()`, `remove_patient()`, and `clear()` do not call `_save_to_disk()`. | Status updates, patient deletions, and `clear()` fail to persist to disk; reloading restores stale state. | **YES** | **HIGH** |
| **ERR-02** | `SimulationService` holds a single global `self.scenario_engine` instance shared across all patients in `_stream_loop()`. | Setting scenario for Patient A mutates scenario for Patient B, causing 100% cross-patient scenario contamination. | **YES** | **CRITICAL** |
| **ERR-03** | `SimulationService._stream_loop()` hardcodes `seed=42` when instantiating `VitalSignGenerator`. | Two distinct patients receive 100% identical noise draw sequences and physiological phase offsets. | **YES** | **HIGH** |
| **ERR-04** | `_save_to_disk()` and `_load_from_disk()` use bare `except Exception: pass`. | Disk I/O failures and corrupted JSON files are silently ignored without logging or operator notification. | **YES** | **HIGH** |
