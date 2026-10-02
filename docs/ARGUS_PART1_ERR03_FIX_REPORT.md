# ARGUS Part 1 ERR-03 Fix Report

## 1. Problem
In `SimulationService._stream_loop()`, continuous physiological vital sign generators were instantiated with a hardcoded integer random seed parameter `seed=42` for all active patients. Consequently, two distinct patients (even with different IDs and baselines) produced 100% identical pseudo-random noise sequences, Mayer wave phase offsets, and Ornstein-Uhlenbeck drift trajectories across all vital sign parameters.

---

## 2. Root Cause
In `part1/backend/app/services/simulation_service.py` line 197:
```python
if patient.patient_id not in self._generators:
    self._generators[patient.patient_id] = VitalSignGenerator(patient, seed=42)
```
Every patient generator received `seed=42`, causing NumPy `default_rng(42)` to initialize identical random number draw sequences for all patients.

---

## 3. Seed Architecture
1. **Patient-Specific Derived Seed**: When `seed` is not explicitly provided (`seed=None`), `VitalSignGenerator.__init__()` deterministically derives a patient-specific seed from `patient.patient_id` using SHA-256 hashing:
   ```python
   digest = hashlib.sha256(patient.patient_id.encode("utf-8")).hexdigest()
   self.seed = int(digest[:8], 16)
   ```
   This ensures different patients (`PATIENT-A`, `PATIENT-B`) receive distinct, independent random seeds.
2. **Explicit Seed Priority**: If an explicit `seed` parameter (or configured seed) is supplied (e.g. `seed=100`), that explicit seed takes precedence, preserving exact reproducibility for unit tests and synthetic patient fixtures.
3. **Cross-Process Stability**: Hashing via `hashlib.sha256` avoids Python's process-randomized `hash()` function (`PYTHONHASHSEED`), ensuring persistent reproducibility across process restarts.

---

## 4. Generator Lifecycle
- `SimulationService._generators` maintains a single `VitalSignGenerator` instance per active patient.
- Generators are instantiated once when the patient starts streaming (`VitalSignGenerator(patient)`).
- On each tick of `_stream_loop()`, the existing cached generator instance advances its internal NumPy RNG (`self.rng`), maintaining smooth time-series continuity.
- When a patient is removed, its generator instance is automatically pruned from `self._generators`.

---

## 5. Files Changed
- [`part1/backend/app/simulation/vital_generator.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/backend/app/simulation/vital_generator.py)
- [`part1/backend/app/services/simulation_service.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/backend/app/services/simulation_service.py)
- [`part1/tests/unit/test_err03_random_seed_isolation.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/part1/tests/unit/test_err03_random_seed_isolation.py) *(new test file)*
- [`docs/ARGUS_PART1_ERR03_FIX_REPORT.md`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/docs/ARGUS_PART1_ERR03_FIX_REPORT.md) *(this report)*

---

## 6. Tests Added
Added 6 focused unit tests in `part1/tests/unit/test_err03_random_seed_isolation.py`:
- `test_1_different_patients_generate_different_noise_sequences`: Verifies equivalent patients with different IDs generate distinct noise sequences across 10 consecutive ticks.
- `test_2_explicitly_different_seeds_produce_different_sequences`: Verifies explicitly configured seeds (`seed=100` vs `seed=200`) yield different vitals.
- `test_3_explicit_seed_is_100_percent_reproducible`: Verifies identical explicit seed (`seed=555`) produces 100% identical outputs.
- `test_4_derived_patient_seed_is_reproducible_across_instances`: Verifies derived seed for a patient ID is stable and reproducible across generator instances.
- `test_5_err02_scenario_isolation_remains_intact`: Verifies ERR-02 scenario isolation is unaffected by seed changes.
- `test_6_rng_states_are_decoupled_between_patients`: Verifies advancing Patient A's generator does not alter Patient B's initial RNG state.

---

## 7. Focused Test Results
Command: `$env:PYTHONPATH="part1/backend"; python -m pytest part1/tests/unit/test_err03_random_seed_isolation.py -v`
- **Passed**: 6 / 6
- **Failed**: 0
- **Pass Rate**: 100%

---

## 8. Full Part 1 Test Results
Command: `$env:PYTHONPATH="part1/backend"; python -m pytest part1/tests -v`
- **Total Tests**: 118
- **Passed**: 118
- **Failed**: 0
- **Warnings**: 14 (pre-existing third-party deprecation warnings)
- **Pass Rate**: 100%

---

## 9. Runtime Validation
Performed runtime generator comparison between two equivalent patients (`PATIENT-RT-A` vs `PATIENT-RT-B`):
- Derived Seed A: `2309100339`
- Derived Seed B: `1756813862`
- **Tick Comparison**: 10 out of 10 ticks (100%) produced distinct, independent vital sign noise values for Heart Rate, Blood Pressure, and SpO2.

Sample Tick 1 Output:
- `PATIENT-RT-A`: HR = 78.9 bpm, BP = 117.7 mmHg, SpO2 = 99.4%
- `PATIENT-RT-B`: HR = 72.6 bpm, BP = 119.6 mmHg, SpO2 = 99.2%

---

## 10. Reproducibility Validation
- Initializing `VitalSignGenerator` with an explicit seed (`seed=777`) produced 100% identical time-series outputs across independent generator instances.
- Initializing `VitalSignGenerator` for the same patient ID without an explicit seed derived the exact same integer seed every time.

---

## 11. ERR-01 Regression
Re-executed ERR-01 patient persistence tests (`test_err01_patient_persistence.py`):
- All 6 ERR-01 tests **PASSED** (100%).
- Status updates, patient removals, and registry clears persist to disk without issue.

---

## 12. ERR-02 Regression
Re-executed ERR-02 scenario isolation tests (`test_err02_scenario_isolation.py`):
- All 6 ERR-02 tests **PASSED** (100%).
- `PATIENT-A` (`rapid_deterioration`) and `PATIENT-B` (`stable`) remain strictly isolated per patient.

---

## 13. ERR-04 Status
**ERR-04 -> NOT FIXED**
Persistence exception swallowing (`except Exception: pass` in `_save_to_disk` and `_load_from_disk`) remains intentionally open for subsequent targeted remediation.

---

## 14. Scope Verification
- **Part 2 Backend / ML Model / SHAP / Alert Engine**: UNCHANGED
- **Part 3 Flutter Mobile / Android**: UNCHANGED
- **ERR-01 Persistence Implementation**: UNCHANGED
- **ERR-02 Scenario-Engine Implementation**: UNCHANGED

---

## 15. Git Verification

### Git Status Output
```
 M part1/backend/app/services/simulation_service.py
 M part1/backend/app/simulation/vital_generator.py
?? docs/ARGUS_PART1_ERR03_FIX_REPORT.md
?? part1/tests/unit/test_err03_random_seed_isolation.py
```

### Diff Summary
- Updated `VitalSignGenerator.__init__()` in `vital_generator.py` to derive a SHA-256 patient seed when `seed` is `None`.
- Updated `SimulationService._stream_loop()` in `simulation_service.py` to instantiate `VitalSignGenerator(patient)` without hardcoded `seed=42`.
- Added 6 focused unit tests in `test_err03_random_seed_isolation.py`.
- Generated fix documentation report in `docs/ARGUS_PART1_ERR03_FIX_REPORT.md`.
