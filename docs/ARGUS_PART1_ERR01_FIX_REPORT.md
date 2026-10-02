# ARGUS Part 1 ERR-01 Fix Report

## 1. Problem
In the Part 1 Simulator `PatientRegistry` service (`part1/backend/app/services/patient_registry.py`), patient lifecycle mutations (`update_patient_status()`, `remove_patient()`, and `clear()`) mutated in-memory data structures (`self._patients`) but failed to invoke disk persistence (`_save_to_disk()`). Consequently, whenever the registry or simulator backend restarted/reloaded, any status updates, patient removals, or registry clears were lost, restoring stale patient records from `patient_registry.json`.

---

## 2. Root Cause
In `PatientRegistry`, `register_patient()` (and `create_patient()`) called `self._save_to_disk()` after modifying `self._patients`. However:
- `update_patient_status()` mutated `self._patients[patient_id]` but omitted `self._save_to_disk()`.
- `remove_patient()` executed `del self._patients[patient_id]` but omitted `self._save_to_disk()`.
- `clear()` executed `self._patients.clear()` but omitted `self._save_to_disk()`.

---

## 3. Implementation
Minimal, targeted fix added to `patient_registry.py`:
Called `self._save_to_disk()` inside `update_patient_status()`, `remove_patient()`, and `clear()` immediately following in-memory mutation within the thread lock `with self._lock:`.

```python
    def update_patient_status(self, patient_id: str, status: PatientStatus) -> Patient:
        with self._lock:
            ...
            self._patients[patient_id] = updated_patient
            self._save_to_disk()  # <-- Added persistence
            return updated_patient

    def remove_patient(self, patient_id: str) -> bool:
        with self._lock:
            if patient_id in self._patients:
                del self._patients[patient_id]
                self._save_to_disk()  # <-- Added persistence
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._patients.clear()
            self._save_to_disk()  # <-- Added persistence
```

No database, external dependencies, or schema redesign were introduced. Existing return types, exceptions (e.g. 404 for missing patient), and edge-case behavior were preserved without alteration.

---

## 4. Files Changed
- [`part1/backend/app/services/patient_registry.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/backend/app/services/patient_registry.py)
- [`part1/tests/unit/test_err01_patient_persistence.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/tests/unit/test_err01_patient_persistence.py) *(new test file)*
- [`docs/ARGUS_PART1_ERR01_FIX_REPORT.md`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/docs/ARGUS_PART1_ERR01_FIX_REPORT.md) *(this report)*

---

## 5. Tests Added
Added 6 focused unit tests in `part1/tests/unit/test_err01_patient_persistence.py`:
- `test_1_status_update_persists_across_reloads`: Verifies updating patient status to `DISCHARGED` persists to disk and survives reload into a new `PatientRegistry` instance.
- `test_2_patient_removal_persists_across_reloads`: Verifies calling `remove_patient()` removes record from disk file and survives reload into a new `PatientRegistry` instance.
- `test_3_clear_registry_persists_across_reloads`: Verifies calling `clear()` empties disk file (`[]`) and survives reload.
- `test_4_update_nonexistent_patient_raises_exception`: Verifies 404 `ARGUSException` is raised when updating non-existent patient.
- `test_5_remove_nonexistent_patient_returns_false`: Verifies `remove_patient()` returns `False` when patient is absent.
- `test_6_clear_empty_registry_succeeds`: Verifies `clear()` on an empty registry succeeds without error.

---

## 6. Focused Test Results
Command: `$env:PYTHONPATH="part1/backend"; python -m pytest part1/tests/unit/test_err01_patient_persistence.py -v`
- **Passed**: 6 / 6
- **Failed**: 0
- **Pass Rate**: 100%

---

## 7. Full Part 1 Test Results
Command: `$env:PYTHONPATH="part1/backend"; python -m pytest part1/tests -v`
- **Total Tests**: 112
- **Passed**: 112
- **Failed**: 0
- **Warnings**: 14 (pre-existing third-party deprecation warnings)
- **Pass Rate**: 100%

---

## 8. Runtime Validation
Tested real filesystem persistence and reload lifecycle:
1. **Status Update**:
   - Created patient `PAT-RT-01` with `ACTIVE` status.
   - Updated status to `DISCHARGED` via `update_patient_status()`.
   - Directly inspected `patient_registry.json` on disk: `{"status": "discharged"}`.
   - Initialized new `PatientRegistry` from disk: `status == DISCHARGED` preserved.
2. **Patient Removal**:
   - Created patient `PAT-RT-02`.
   - Called `remove_patient("PAT-RT-02")`.
   - Directly inspected `patient_registry.json`: `PAT-RT-02` absent.
   - Initialized new `PatientRegistry` from disk: `PAT-RT-02` remains absent.
3. **Registry Clear**:
   - Created multiple patients and called `clear()`.
   - Directly inspected `patient_registry.json`: `[]`.
   - Initialized new `PatientRegistry` from disk: 0 patients (empty registry preserved).

---

## 9. ERR-02 Regression
Re-executed the ERR-02 scenario isolation suite (`test_err02_scenario_isolation.py`):
- All 6 ERR-02 tests **PASSED** (100%).
- `PATIENT-A` (`rapid_deterioration`) and `PATIENT-B` (`stable`) remain strictly isolated per patient.
- Zero cross-patient scenario contamination.

---

## 10. ERR-03 / ERR-04 Status
- **ERR-03 (Hardcoded Random Seed)**: **NOT FIXED** (intentionally left unchanged: `seed=42` hardcoded in generator loop as required).
- **ERR-04 (Persistence Exception Swallowing)**: **NOT FIXED** (intentionally left unchanged: `except Exception: pass` in `_save_to_disk`/`_load_from_disk` untouched as required).

---

## 11. Scope Verification
- **Part 2 Backend / ML Model / SHAP / Alert Engine**: UNCHANGED
- **Part 3 Flutter Mobile / Android Notification System**: UNCHANGED
- **ERR-02 Scenario-Engine Implementation**: UNCHANGED
- **MIMIC Replay & Docker Configuration**: UNCHANGED

---

## 12. Git Verification

### Git Status Output
```
 M part1/backend/app/services/patient_registry.py
?? docs/ARGUS_PART1_ERR01_FIX_REPORT.md
?? part1/tests/unit/test_err01_patient_persistence.py
```

### Diff Summary
- Modified `PatientRegistry` in `patient_registry.py` to call `self._save_to_disk()` in `update_patient_status()`, `remove_patient()`, and `clear()`.
- Added 6 focused unit tests in `test_err01_patient_persistence.py`.
- Generated fix documentation report in `docs/ARGUS_PART1_ERR01_FIX_REPORT.md`.
