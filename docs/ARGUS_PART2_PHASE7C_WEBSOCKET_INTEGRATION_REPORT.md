# ARGUS Part 2 — Phase 7C WebSocket Integration Report

## 1. Objective

Connect the Phase 7B frontend to the canonical Phase 6B backend WebSocket endpoint (`WS /api/v1/ws/stream`) to enable real-time clinical monitoring, streaming risk predictions, live SmartAlertEngine alert emissions, real SHAP feature attributions, and patient-isolated UI updates without polling, page refreshes, or mock data.

## 2. Branch Verification

- **Active Development Branch:** `feature/argus-part2-phase7b`
- **Baseline Commit:** `e4e55b8 feat(argus): establish phase 7b frontend integration baseline`
- **Safety Backup Branch:** `backup/argus-part2-before-stabilization` (Untouched at `923dab7`)
- **Main Branch:** `main` (Untouched at `923dab7`)

## 3. Backend WebSocket Contract

Inspected canonical Phase 6B WebSocket implementation in `src/backend/api/endpoints/websocket.py`, `src/backend/services/event_broker.py`, and `tests/unit/test_websocket.py`:
- **Canonical Endpoint:** `WS /api/v1/ws/stream`
- **Compatibility Endpoint:** `WS /api/v1/ws`
- **Keepalive Protocol:** Client sends `{"type": "ping"}`, server responds with `{"type": "pong", "occurred_at": "<ISO-timestamp>"}`.
- **Broadcast Message Schema:**
  - `type`: `'prediction'`, `'alert'`, `'pong'`, or `'error'`
  - `occurred_at`: ISO 8601 clinical event timestamp
  - `patient_id`: Target ICU patient identifier
  - `payload`: Contains prediction results (`risk_probability`, `alert_severity`, `shap_explanation`, `uncertainty_summary`, `alert`, `model_version`).

## 4. WebSocket Client Architecture

Implemented dedicated `WebSocketService` in `src/frontend/src/services/websocket.ts` and custom React hook `useWebSocket` in `src/frontend/src/hooks/useWebSocket.ts`:
- **URL Configuration:** Derived from `import.meta.env.VITE_WS_BASE_URL` with automatic protocol translation (`http://` -> `ws://`, `https://` -> `wss://`). Default: `ws://localhost:8000/api/v1/ws/stream`.
- **Decoupled Architecture:** WebSocket management logic is completely isolated from UI page components.

## 5. Connection Lifecycle

Maintains explicit connection lifecycle states:
- `CONNECTING`
- `CONNECTED` (🟢 LIVE)
- `RECONNECTING` (🟡 RECONNECTING)
- `DISCONNECTED` (🔴 DISCONNECTED)
- `ERROR`

The `ConnectionStatus` component in the sidebar reflects these live status badges dynamically.

## 6. Reconnection Strategy

- Controlled exponential backoff retry strategy (1s, 2s, 4s, 8s, max 10s delay up to 5 attempts).
- Prevents infinite rapid reconnect loops.
- Automatically clears timers on component unmount / intentional disconnect (`disconnect()`).
- Guarantees no duplicate WebSocket connections or event listener accumulation.

## 7. Patient Isolation

Strict patient-aware event routing:
- `subscribePatient(patientId, callback)` registers listeners for a specific patient ID.
- When incoming WebSocket envelopes arrive, the service matches `envelope.patient_id` or `envelope.payload.patient_id`.
- Telemetry events for Patient A are dispatched **ONLY** to Patient A subscribers and never pollute Patient B's UI state.

## 8. Real-Time State Updates

- **`PatientDetailsPage.tsx`:** Real-time updates update current vitals, risk probability, append new points to deterioration risk trajectory chart, update real SHAP feature attributions, and append active alerts without full page reload or browser refresh.
- **`Dashboard.tsx`:** Listens to global stream and updates patient risk scores, risk levels, and recent urgent alerts across the roster.
- **`AlertsPage.tsx`:** Listens to global stream and updates active clinical alert counters and alert cards when SmartAlertEngine emits new alerts.

## 9. REST + WebSocket Architecture

- **REST API:** Responsible for initial page load data fetching and current baseline state retrieval (`GET /patients/{id}`, `GET /patients/{id}/vitals`, `GET /patients/{id}/risk`, etc.).
- **WebSocket Stream:** Responsible for subsequent real-time telemetry updates.
- **Resilience:** If WebSocket disconnects, the UI preserves the last known valid REST state and displays a `RECONNECTING` / `DISCONNECTED` badge until stream connection is restored.

## 10. Timestamp Handling

- Clinical event timestamps (`prediction_timestamp` or `occurred_at` from backend) are preserved and displayed on trajectory charts and alert cards.
- Clinical timestamps are never replaced with local `new Date()` calls.

## 11. Duplicate Event Handling

- Deduplication cache tracks processed event keys (`type:patient_id:timestamp`) within a 5-second window to prevent duplicate UI renders.

## 12. Error Handling

- Server error envelopes (`{"type": "error", "message": "..."}`) are logged safely without crashing the React application.
- Raw stack traces are never exposed to the UI.

## 13. Cleanup / Memory Safety

- `useWebSocket` automatically unsubscribes event listeners and state listeners on component unmount or patient switching.
- Timers (`reconnectTimer`, `pingTimer`) are cleared on socket disconnect.

## 14. Testing

- **Frontend Build (`tsc -b && vite build`):** PASS (0 errors)
- **Frontend Lint (`oxlint`):** PASS (0 errors)
- **Frontend Client Unit Test (`node --experimental-strip-types src/services/api.test.ts`):** 3/3 passed
- **Backend Unit Integration Tests (`pytest tests/unit/test_frontend_websocket_integration.py`):** 5/5 passed

## 15. Live WebSocket Verification

Ran live uvicorn server (`src.backend.main:app` on port 8000) and verified live WebSocket stream via `scratch/verify_live_websocket.py`:
1. Connection to `WS /api/v1/ws/stream` — PASS
2. Keepalive Ping/Pong check — PASS
3. Two independent clients connected simultaneously — PASS
4. Live prediction event received — PASS
5. Real SHAP attributions present — PASS
6. Uncertainty status explicitly `UNAVAILABLE` — PASS
7. Live SmartAlertEngine alert emission — PASS
8. Patient isolation (Patient A vs. Patient B) — PASS
- **Result:** 10/10 PASS

## 16. Frontend Validation

- **Lint:** PASS
- **Build:** PASS
- **Types:** PASS

## 17. Backend Regression

Ran `python -m pytest tests/`:
- **Result:** 182 passed / 0 failed / 0 blocked (across 182 total unit/integration tests).

## 18. Files Changed

- `src/frontend/src/App.tsx`
- `src/frontend/src/components/common/ConnectionStatus.tsx`
- `src/frontend/src/components/layout/AppShell.tsx`
- `src/frontend/src/components/layout/Sidebar.tsx`
- `src/frontend/src/pages/AlertsPage.tsx`
- `src/frontend/src/pages/Dashboard.tsx`
- `src/frontend/src/pages/PatientDetailsPage.tsx`

## 19. Files Created

- `src/frontend/src/services/websocket.ts`
- `src/frontend/src/hooks/useWebSocket.ts`
- `tests/unit/test_frontend_websocket_integration.py`
- `scratch/verify_live_websocket.py`
- `docs/ARGUS_PART2_PHASE7C_WEBSOCKET_INTEGRATION_REPORT.md`

## 20. Issues / Blockers

- None.

## 21. Phase 7D Readiness

Phase 7C WebSocket integration is fully validated and PASS. The project is 100% ready for Phase 7D (End-to-End Verification & Documentation).
