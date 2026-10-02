# ARGUS Part 2 Phase 5 Smart Alert Engine Validation Report

## 1. Objective
The objective of Phase 5 is to validate and stabilize the `SmartAlertEngine` policy layer in `src/pipeline/11_smart_alert_engine.py` and its integration with the stabilized `src/backend` inference pipeline. This phase ensures that alert level determination, persistence tracking, escalation, de-escalation, hysteresis, deduplication, and signal quality handling operate deterministically based on actual clinical timestamps rather than event counts.

## 2. Existing Alert-Engine Architecture
The `SmartAlertEngine` is a stateful policy layer. It processes calibrated model risk probabilities, signal quality, and clinical timestamps to maintain per-patient alert state (`AlertState`). It does NOT alter model risk probabilities, diagnose sepsis, or prescribe clinical treatments.

## 3. Alert Levels
The engine evaluates three discrete severity bands:
- `YELLOW — WATCH`: Routine clinical review.
- `ORANGE — REVIEW`: Prompt clinical review.
- `RED — URGENT`: Urgent clinical review.

## 4. Thresholds
Alert thresholds are defined in `AlertPolicy`:
- `yellow_risk`: 0.25 (25% risk)
- `orange_risk`: 0.35 (35% risk)
- `red_risk`: 0.70 (70% risk)
- `escalation_delta`: 0.10 (+10%/hr risk trajectory jump escalates `WATCH` to `REVIEW`)
- `low_confidence_red_floor`: 0.85 (If confidence or signal quality is not `HIGH`, `RED` alerts are capped at `ORANGE` unless risk reaches 0.85)

## 5. Persistence Rules
Alert persistence requires sustained elevated risk over `escalation_windows` (2 clinical observation hours) before escalating to `WATCH` or `ORANGE/REVIEW`. `RED/URGENT` alerts escalate immediately upon crossing the 0.70 risk threshold (or 0.85 floor under low confidence).

## 6. Timestamp Handling
In Phase 5, event-count based persistence (`state.consecutive_risk_windows += 1`) was replaced with actual clinical timestamp tracking (`state.risk_started_at`).
- Persistence elapsed hours: $\Delta t = (\text{now} - \text{state.risk\_started\_at}) / 3600$.
- Consecutive clinical risk windows: $\max(1, \lfloor \Delta t \rfloor + 1)$.
High-frequency events arriving seconds apart no longer inflate persistence window counts. Sparse events 2.5 hours apart correctly reflect 3 clinical risk windows.

## 7. Escalation Behavior
- Immediate escalation to `RED/URGENT` when risk $\ge 0.70$ (or $\ge 0.85$ under low confidence).
- Escalation from `WATCH` to `REVIEW` when risk trajectory $\ge +10\%$/hr or when risk persists $\ge 2$ clinical hours above 0.35.

## 8. De-escalation Behavior
De-escalation requires a sustained drop below the active alert severity band for `deescalation_windows` (3 clinical hours). `state.below_started_at` tracks elapsed time below the active band until 3 full hours have elapsed.

## 9. Hysteresis
To prevent rapid alert thrashing around boundary thresholds, `SmartAlertEngine` holds the active alert level (`active_severity`) during temporary improvements until 3 consecutive clinical hours below the threshold elapse (`suppressed_reason: 'hysteresis hold during improvement'`).

## 10. Deduplication
To prevent duplicate alerts for unchanged active conditions:
- `RED/URGENT` repeat cooldown: 2 hours (`red_repeat_hours`).
- `ORANGE/REVIEW` & `YELLOW/WATCH` repeat cooldown: 6 hours (`repeat_hours`).
Events arriving within the repeat interval return `alert_emitted: false` with `suppression_reason: 'duplicate within repeat interval'`.

## 11. Signal-Quality Handling
Signal quality (`sq`) and reliability confidence (`conf`) modulate alert severity:
- `HIGH` quality allows standard `RED` alerts at 0.70 risk floor.
- `MEDIUM` or `LOW` quality caps high-risk alerts to `ORANGE` unless risk crosses `low_confidence_red_floor` (0.85).
- Signal quality is explicitly separate from statistical model uncertainty (which remains `UNAVAILABLE`).

## 12. Missing / Stale / Invalid Data Handling
- Missing vitals or default parameters default `confidence` to `LOW`, capping unverified high risk at `ORANGE`.
- Timestamps in ISO strings or UTC datetime objects are parsed safely via `pd.Timestamp`.

## 13. Tests Added
23 unit tests were created in `tests/unit/test_smart_alert_engine.py`:
1. `test_1_normal_state`: Low risk (<0.25) returns no alert.
2. `test_2_watch_activation`: Risk 0.28 emits `WATCH` after 2h persistence.
3. `test_3_review_activation`: Risk 0.40 emits `REVIEW` after persistence.
4. `test_4_urgent_activation`: Risk 0.75 with `HIGH` quality emits immediate `RED`.
5. `test_5_timestamp_based_persistence`: 4 events in 20s stay at 1 window count.
6. `test_6_sparse_event_handling`: Events 2.5h apart compute 3 clinical windows.
7. `test_7_high_frequency_event_handling`: Events 5s apart do not inflate window count.
8. `test_8_watch_to_review_escalation`: Trajectory jump +15%/hr escalates to `REVIEW`.
9. `test_9_review_to_urgent_escalation`: Risk jump to 0.75 promotes `REVIEW` to `URGENT`.
10. `test_10_recovery_deescalation`: 3.1h recovery de-escalates `RED` to `None`.
11. `test_11_hysteresis`: 1h drop holds `active_severity` at `ORANGE`.
12. `test_12_duplicate_alert_prevention`: Repeat event within 30m is suppressed.
13. `test_13_repeated_identical_events`: Event 2.1h later emits repeat `RED` alert.
14. `test_14_high_signal_quality`: Allows `RED` alert at 0.72 risk.
15. `test_15_medium_signal_quality`: Caps 0.72 risk to `ORANGE`.
16. `test_16_low_signal_quality`: Caps 0.72 risk to `ORANGE`.
17. `test_17_missing_data`: Missing conf/sq parameters handled safely.
18. `test_18_stale_data`: String ISO timestamps handled cleanly.
19. `test_19_invalid_noisy_data`: Risk >= 0.85 overcomes LOW confidence limit.
20. `test_20_model_version_remains_logistic_regression_v1`: Confirms model version.
21. `test_21_shap_remains_available`: Confirms SHAP attributions active.
22. `test_22_uncertainty_remains_explicitly_unavailable`: Confirms uncertainty unavailable.
23. `test_23_end_to_end_inference_to_alert_behavior`: Tests full E2E inference to alert payload.

## 14. Full Test Results
Ran `python -m pytest tests/`:
- **86 passed / 0 failed** (100% pass rate across unit, model, safety, integration, and system test suites).

## 15. Live Verification
- `model_version`: `logistic-regression-v1`
- `is_demo_model`: `false`
- `risk_probability`: Calibrated probability preserved.
- `shap_explanation.explanation_available`: `true`
- `uncertainty_summary.uncertainty_available`: `false`
- `alert.alert_severity`: Deterministic alert severity generated.

## 16. Files Changed
- `src/pipeline/11_smart_alert_engine.py`: Updated `process()` method for timestamp-based persistence (`risk_started_at`) and de-escalation (`below_started_at`).
- `src/backend/services/inference_runtime.py`: Updated `SmartAlertEngine` process call.
- `tests/unit/test_smart_alert_engine.py`: Created 23 new unit tests.
- `docs/ARGUS_PART2_PHASE5_ALERT_ENGINE_REPORT.md`: Created Phase 5 report.

## 17. Files Intentionally Untouched
- `deployment/backend/`: Untouched.
- `src/frontend/`: Untouched.
- `model/`: Model artifacts untouched.

## 18. Remaining Limitations
Alert thresholds and policy behavior require formal clinical validation before real-world deployment. ARGUS remains a prototype clinical decision-support system.
