# ARGUS Part 2 — Phase 6B: WebSocket Audit & Stabilization Report

## 1. Objective
Audit and stabilize the WebSocket communication layer in the consolidated `src/backend/` implementation. Ensure that real-time raw event ingestion, model inference (`logistic-regression-v1`), SHAP feature attribution, and `SmartAlertEngine` notifications function deterministically across WebSocket connections without altering underlying ML models, calibration, or alert logic.

---

## 2. Existing WebSocket Architecture
- **Framework:** FastAPI / Starlette WebSockets.
- **Broker:** `LocalEventBroker` (`src/backend/services/event_broker.py`) managing active subscriber sockets in `broker.subscribers` set.
- **Processing Pipeline:**
  Raw WebSocket Event -> Validation (`VitalEvent`) -> `InferenceService.ingest()` -> `InferenceRuntime` -> Real SHAP Attributions -> `SmartAlertEngine` -> DB Records (`VitalRecord`, `PredictionRecord`, `AlertRecord`) -> `broker.publish('prediction', ...)` & `broker.publish('alert', ...)` -> Active WebSocket Subscribers.

---

## 3. Endpoint Inventory
| Path | Type | Role | Implementation |
|---|---|---|---|
| `WS /api/v1/ws/stream` | Endpoint | **Canonical Stream** | Pub-sub broadcast stream + event ingestion + keepalive ping/pong |
| `WS /api/v1/ws` | Endpoint | **Compatibility Alias** | Pub-sub stream + legacy echo support (`"Message text was: ..."`) |

---

## 4. Canonical Endpoint Decision
- **Canonical Stream Endpoint:** `WS /api/v1/ws/stream` is the official real-time WebSocket stream.
- **Compatibility Endpoint:** `WS /api/v1/ws` is retained as a compatibility alias. Both endpoints register sockets with `broker.subscribers` to receive broadcast events.

---

## 5. Incoming Message Contract
- **Format:** Raw JSON text.
- **Fields:**
  - `patient_id`: `str` (min_length=1, max_length=64)
  - `timestamp`: `datetime` / ISO 8601 string
  - `heart_rate`: `float | None` (0 - 400)
  - `map`: `float | None` (0 - 300) [or computed automatically if `bp_systolic` and `bp_diastolic` are provided]
  - `resp_rate`: `float | None` (0 - 100)
  - `spo2`: `float | None` (0 - 100)
  - `temperature_c`: `float | None` (20 - 50) [or `temperature`]
  - `lactate`: `float | None` (0 - 30)
  - `source`: `'simulator'` | `'integration'`
- **Control Messages:** `{"type": "ping"}` or `{"type": "keepalive"}` returns `{"type": "pong", "occurred_at": "..."}`.

---

## 6. Outgoing Message Contract
Broadcast payloads from `broker.publish()` format:
- `type`: `"prediction"` or `"alert"`
- `occurred_at`: ISO 8601 timestamp string
- `patient_id`: `str`
- `payload`:
  - `patient_id`: `str`
  - `prediction_timestamp`: `datetime` / ISO string
  - `risk_probability`: `float`
  - `model_version`: `"logistic-regression-v1"`
  - `is_demo_model`: `false`
  - `signal_quality`: `"HIGH"` | `"MEDIUM"` | `"LOW"`
  - `shap_explanation`: `{"explanation_available": true, "base_value": float, "feature_attributions": [...]}`
  - `uncertainty_summary`: `{"uncertainty_available": false, "method": "UNAVAILABLE", "reason": "..."}`
  - `alert`: `{"alert_emitted": bool, "alert_severity": str, "recommended_action": str, ...}`

---

## 7. Connection Lifecycle
- **Connect:** Socket accepted (`await ws.accept()`), socket added to `broker.subscribers`.
- **Receive / Process:** Message received via `await ws.receive_text()`, parsed, validated, and processed via `InferenceService.ingest()`.
- **Send:** Updates broadcast via `broker.publish()` iterating over `list(broker.subscribers)`.
- **Disconnect:** Socket safely removed from `broker.subscribers` upon `WebSocketDisconnect` or `send_text` failure. No socket leaks.

---

## 8. Timestamp Handling
- The clinical event timestamp from the incoming raw event (`timestamp`) is preserved end-to-end.
- Supports ISO 8601 string timestamps (e.g. `'2026-10-01T18:00:00+00:00'`).
- Chronological sorting and windowing in `InferenceRuntime` handles out-of-order events and duplicate event timestamps gracefully.

---

## 9. Multiple-Client Handling
- `LocalEventBroker` maintains active subscribers set.
- When an event is ingested, all connected clients receive broadcast updates concurrently without cross-client blocking or message duplication.

---

## 10. Patient Isolation
- Broadcast messages contain `patient_id` explicitly in both outer envelope and payload (`"patient_id": "WS-ISO-A"`).
- Ingestion, database records, and predictions preserve patient separation without cross-patient data leakage.

---

## 11. Error Handling
- Malformed JSON, missing mandatory fields (`patient_id`, `timestamp`), or validation errors return structured error messages (`{"type": "error", "message": "..."}`).
- Connection remains open on soft validation errors without crashing the backend or exposing internal stack traces, file paths, or secrets.

---

## 12. Disconnect / Reconnect
- Client disconnect removes socket reference cleanly.
- Client reconnect adds fresh socket without stale references or duplicate subscriptions.

---

## 13. Authentication Status
- **Status:** NOT IMPLEMENTED (Public dev stream).
- **Limitation:** WebSocket connections currently do not enforce Bearer token authentication, matching REST event stream endpoints. Authentication hardening will be addressed in future phases.

---

## 14. Tests Added
25 new unit/integration tests added in [`tests/unit/test_websocket.py`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/tests/unit/test_websocket.py):
1. `test_01_connection_accepted`: Connects to `/api/v1/ws/stream`.
2. `test_02_canonical_endpoint`: Verifies ping/pong keepalive on canonical endpoint.
3. `test_03_compatibility_alias`: Verifies `/api/v1/ws` alias and legacy echo compatibility.
4. `test_04_connection_cleanup`: Verifies subscriber count decreases on disconnect.
5. `test_05_valid_raw_event`: Verifies valid vitals event ingestion over WS.
6. `test_06_prediction_returned`: Verifies prediction probability, model version (`logistic-regression-v1`), and demo status (`false`).
7. `test_07_shap_returned`: Verifies SHAP feature attributions in payload.
8. `test_08_uncertainty_unavailable`: Verifies `uncertainty_summary.uncertainty_available == false` and `method == 'UNAVAILABLE'`.
9. `test_09_alert_returned`: Verifies alert broadcast on high-risk vitals.
10. `test_10_clinical_timestamp_preserved`: Verifies original clinical timestamp is preserved in output.
11. `test_11_iso_timestamp`: Verifies ISO timestamp parsing.
12. `test_12_out_of_order_events`: Verifies out-of-order events handling in windowing.
13. `test_13_duplicate_timestamp`: Verifies duplicate timestamp handling.
14. `test_14_malformed_json`: Verifies malformed JSON returns error JSON without crash.
15. `test_15_missing_patient_id`: Verifies missing `patient_id` returns error JSON.
16. `test_16_missing_timestamp`: Verifies missing `timestamp` returns error JSON.
17. `test_17_invalid_numeric_values`: Verifies invalid numeric values return validation error.
18. `test_18_client_disconnect`: Verifies clean disconnect.
19. `test_19_client_reconnect`: Verifies reconnect creates fresh subscriber.
20. `test_20_multiple_clients`: Verifies broadcast to multiple connected clients.
21. `test_21_multiple_patients`: Verifies handling events for multiple patients.
22. `test_22_patient_isolation`: Verifies correct `patient_id` targeting.
23. `test_23_no_duplicate_inference`: Verifies single inference execution per event.
24. `test_24_no_legacy_dependency`: Verifies zero imports from `deployment/backend`.
25. `test_25_end_to_end_ws_event_prediction_alert`: Verifies complete end-to-end WS flow (raw event -> inference -> SHAP -> alert).

---

## 15. Full Test Result
- **Phase 6A Baseline:** 106 tests passed, 0 failed.
- **Added (Phase 6B):** 25 tests passed, 0 failed.
- **Total:** 131 passed, 0 failed.

---

## 16. Live Smoke Test
- **Executed:** Standard Python `TestClient.websocket_connect` to `WS /api/v1/ws/stream` on `src.backend.main:app`.
- **Result:**
  - Connection accepted & subscriber registered.
  - Event ingested for `SMOKE-WS-PATIENT`.
  - Response received: `type` = `prediction`, `model_version` = `logistic-regression-v1`, `is_demo_model` = `false`, SHAP available = `true`, `uncertainty_available` = `false`, `prediction_timestamp` = `2026-10-01 18:00:00+00:00`.
  - Clean subscriber cleanup on exit.

---

## 17. Files Changed
1. `src/backend/schemas/schemas.py`: Added `@model_validator(mode='before')` to `VitalEvent` for alias mapping (`temperature` -> `temperature_c`) and automatic MAP calculation from blood pressure.
2. `src/backend/api/endpoints/websocket.py`: Replaced minimal handler with full JSON parsing, schema validation, `InferenceService.ingest()` execution, ping/pong keepalive, and error catching.
3. `tests/unit/test_websocket.py`: Created WebSocket test suite (25 tests).
4. `docs/ARGUS_PART2_PHASE6B_WEBSOCKET_REPORT.md`: Created Phase 6B report.

---

## 18. Files Intentionally Untouched
- `deployment/backend/` (all files preserved as legacy reference)
- `src/frontend/` (untouched)
- `model/` (model artifacts and training pipelines untouched)
- `src/backend/services/inference_runtime.py` (InferenceRuntime untouched)
- `src/backend/services/alert_engine.py` (SmartAlertEngine untouched)
- `src/backend/services/shap_service.py` (SHAP implementation untouched)

---

## 19. Remaining Limitations
- Authentication: WebSocket endpoints remain unauthenticated; token validation can be integrated in future security hardening phases.
- Scaling: `LocalEventBroker` is single-process in-memory; multi-worker deployments will require Redis Pub/Sub integration.
