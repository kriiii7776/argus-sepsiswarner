# ARGUS Part 2 Phase 3A Timestamp and Windowing Report

## 1. Objective
The objective of Phase 3A was to replace event-count and array-index based clinical windowing (`vals[-4:]`, `d('hr_curr', 1)`, `d('hr_curr', 4)`) in the official `src/backend` runtime with **true timestamp-based clinical windowing**. The system now processes elapsed clinical time using event timestamps rather than event packet counts.

---

## 2. Previous Time Handling
In the previous implementation ([`deployment/backend/app/service.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/deployment/backend/app/service.py#L32-L40)):
- Rolling 4-hour features (`hr_mean_4h`, `map_time_low_4h`) were calculated using array slicing on `deque` history: `vals(key)[-4:]`.
- 1-hour deltas (`hr_delta_1h`) subtracted item $N$ minus item $N-1$: `d('hr_curr', 1)`.
- 4-hour slopes (`hr_slope_4h`) subtracted item $N$ minus item $N-4$ and divided by hardcoded integer `4`: `d('hr_curr', 4) / 4`.
- Alert persistence passed `len(history)` (total event count) as `persistent_windows`.

**Critical Problem:** When events arrived every 5 seconds (e.g. from the simulator), 4 events represented **20 seconds of data**, NOT 4 hours of clinical observations. This caused massive numerical distortions when fed into ML models trained on 1-hour binned clinical data.

---

## 3. Problems Found & Resolved
1. **Event Count vs Clinical Time:** Replaced index offsets (`vals[-4:]`) with timestamp ranges (`timestamp >= t_curr - timedelta(hours=4)`).
2. **Unsorted Event Arrival:** Implemented explicit chronological sorting by `(timestamp, received_at)` rather than assuming arrival order.
3. **Duplicate Timestamps:** Added deterministic deduplication for events with identical timestamps.
4. **Distorted Slope Calculations:** Replaced division by hardcoded constant `4` with division by actual elapsed clinical hours (`dt_hours_4h`).
5. **Alert Persistence Distortion:** Updated `persistent_windows` to reflect elapsed clinical hours instead of raw event packet counts.

---

## 4. Timestamp Normalization
- All incoming event timestamps (`VitalEvent.timestamp`) are normalized into timezone-aware UTC `datetime` objects via `ensure_utc()`.
- String ISO 8601 inputs and naive datetimes are converted to UTC.

---

## 5. Event Ordering & Deduplication
- Each patient's event history is maintained in chronological order sorted by `(timestamp, received_at)`.
- If an event arrives with a duplicate timestamp for the same patient, the newest received payload replaces the previous entry.
- Out-of-order or late-arriving events are placed in their exact chronological position without advancing time prematurely.

---

## 6. 1-Hour Binning & Baseline Selection
- 1-hour deltas (`hr_delta_1h`, `map_delta_1h`, `rr_delta_1h`, `temp_delta_1h`) search history for the observation occurring closest to $\le t_{\text{curr}} - 1\text{h}$.
- If no baseline event exists $\ge 1$ hour prior to $t_{\text{curr}}$, delta evaluates to `0.0`.

---

## 7. 4-Hour Observation Window
- Rolling 4-hour statistics (`hr_mean_4h`, `hr_std_4h`, `hr_min_4h`, `hr_max_4h`, `map_mean_4h`, `map_std_4h`, `map_min_4h`, `rr_mean_4h`, `temp_mean_4h`, `map_time_low_4h`) filter history using an inclusive lower boundary rule:
  $$\text{h\_4h} = \{ e \in \text{history} \mid t_{\text{curr}} - 4\text{h} \le e.\text{timestamp} \le t_{\text{curr}} \}$$
- Events older than 4 hours are automatically excluded from the 4-hour statistics.

---

## 8. 6-Hour Prediction Horizon
- The prediction target remains anchored to the clinical `prediction_timestamp` with a 6-hour forward-looking horizon schema.

---

## 9. Persistence Timing
- `SmartAlertEngine` parameter `persistent_windows` is calculated as elapsed clinical hours:
  $$\text{persistent\_windows} = \max\left(1, \left\lfloor \frac{t_{\text{curr}} - t_{\text{first}}}{3600} \right\rfloor + 1\right)$$

---

## 10. Slope / Trend Timing
- 4-hour trend slopes are calculated using exact elapsed clinical hours:
  $$\text{slope\_4h} = \frac{\text{val}(t_{\text{curr}}) - \text{val}(e_{\text{baseline}})}{\text{elapsed\_hours}}$$
- Division by zero is safely prevented with a minimum threshold (`max(elapsed_hours, 0.001)`).

---

## 11. Missing and Irregular Data
- Handles sparse streams (e.g. 2 events 10 minutes apart), high-frequency streams (every 5 seconds), and standard ICU intervals (15 minutes, 1 hour).
- `time_since_lactate` measures actual elapsed hours since the last valid lactate measurement.
- `icu_hour` measures actual elapsed hours since the patient's first recorded event.

---

## 12. Files Modified

### Modified Code File
- [`src/backend/services/inference_runtime.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/backend/services/inference_runtime.py) — Updated `Runtime` class with timestamp-based windowing, chronological sorting, 4h boundary rules, and time slopes.

### Newly Created Test File
- [`tests/unit/test_timestamp_windowing.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/tests/unit/test_timestamp_windowing.py) — 12 unit tests verifying timestamp windowing rules.

### Unmodified Files Preserved
- `deployment/backend/app/` — **0 files modified** (Legacy reference intact).
- `src/frontend/` — **0 files modified**.
- `model/` — **0 model artifacts modified or retrained**.

---

## 13. Tests Added

1. `test_1_rapid_events_not_interpreted_as_four_hours`: 4 events 5s apart do not create fake 4-hour history.
2. `test_2_exact_four_clinical_hours_window`: Events covering 4 hours form a valid 4h window.
3. `test_3_five_minute_interval_window`: 5-minute interval events (49 events in 4h) processed correctly.
4. `test_4_fifteen_minute_interval_window`: 15-minute interval events (17 events in 4h) processed correctly.
5. `test_5_irregular_event_intervals`: Irregular intervals calculate slopes using actual elapsed time.
6. `test_6_out_of_order_event_sorting`: Out-of-order events sorted chronologically by timestamp.
7. `test_7_duplicate_timestamps_deterministic_handling`: Duplicate timestamps deduplicated deterministically.
8. `test_8_old_events_excluded_from_4h_window`: Events older than 4h excluded from 4h mean/max.
9. `test_9_inclusive_boundary_rule`: Events exactly at $t_{\text{curr}} - 4\text{h}$ included in 4h window.
10. `test_10_slope_uses_elapsed_clinical_time`: Slope calculated as $\Delta \text{val} / \Delta t_{\text{hours}}$.
11. `test_11_sparse_data_no_fake_history`: Sparse data does not generate 1h delta without 1h baseline.
12. `test_12_future_and_late_arrival_timestamps`: Late arrivals placed in chronological order safely.

---

## 14. Test Results

- **Command:** `python -m pytest tests/`
- **Total Tests Collected:** 26
- **Passed:** **26**
- **Failed:** **0**
- **Existing Test Regression:** **None (14/14 existing integration/unit/safety tests passed)**

```
tests\integration\test_integration.py ...                                [ 11%]
tests\model\test_model.py ...                                            [ 23%]
tests\safety\test_safety.py ...                                          [ 34%]
tests\system\test_system.py ..                                           [ 42%]
tests\unit\test_timestamp_windowing.py ............                      [ 88%]
tests\unit\test_unit.py ...                                              [100%]
======================= 26 passed, 2 warnings in 6.21s ========================
```

---

## 15. Remaining Temporal Issues
- None in the backend feature calculation layer. The backend now accurately processes high-frequency, regular, irregular, and sparse data streams using clinical timestamps.

---

## 16. Verification Summary

| Verification Check | Target / Rule | Result | Status |
|---|---|---|---|
| **Timestamp Windowing Fix** | Replace index offsets with timestamp ranges | `inference_runtime.py` updated | **PASSED** |
| **New Unit Tests** | 12 focused timestamp tests | 12 / 12 PASSED | **PASSED** |
| **Existing Test Suite** | Zero regressions | 14 / 14 PASSED | **PASSED** |
| **Deployment Backend Preserved** | `deployment/backend/app/` untouched | 0 files modified | **PASSED** |
| **Frontend Preserved** | `src/frontend/` untouched | 0 files modified | **PASSED** |
| **Model Artifacts Preserved** | No retraining or artifact edits | 0 artifacts modified | **PASSED** |
| **Dependencies Preserved** | No new external dependencies | 0 dependencies added | **PASSED** |
