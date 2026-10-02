# ARGUS END-TO-END ARCHITECTURE & DATA FLOW AUDIT

**Date:** October 3, 2026  
**Branch:** `feature/argus-e2e-full-fix`  
**Base Commit:** `323bac7`  

---

## 1. System Overview & Architecture Mapping

```
+-----------------------------------------------------------------------------------+
|                              PART 1 SIMULATOR (Port 8001)                          |
|  - Patient Registry (Synthetic + MIMIC Replay Cohort)                              |
|  - Simulation Clock & Scenario Engine (rapid_deterioration, stable, etc.)          |
|  - Vital Generator (1Hz continuous vital event production)                         |
|  - WebSocket Server (/api/v1/stream)                                              |
+-----------------------------------------------------------------------------------+
                                         |
                                         | (WebSocket / JSON Vital Event Stream)
                                         v
+-----------------------------------------------------------------------------------+
|                        PART 1 -> PART 2 BRIDGE / ADAPTER                          |
|  - sepsisguard.part1_ws_bridge (connects to ws://127.0.0.1:8001/api/v1/stream)    |
|  - Event Schema Normalization & Patient ID Mapping                                 |
|  - Ingests events into Part 2 InferenceRuntime & Event Ingestion pipeline         |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        PART 2 CDS BACKEND (Port 8000)                             |
|  - Event Ingestion & Timestamp-based Windowing (1h, 4h, 6h means, slopes, deltas) |
|  - ML Inference: logistic-regression-v1 (31 Canonical Features)                   |
|  - Sigmoid Calibration & SHAP LinearExplainer                                     |
|  - SmartAlertEngine (State Machine, Policy Bands: YELLOW, ORANGE, RED)             |
|  - Alert Router (ICU Scope & User/Device Assignment Routing)                      |
|  - Database Persistence (SQLAlchemy / SQLite-PostgreSQL Store)                   |
|  - WebSocket Gateway (/api/v1/ws/stream) Broadcast                                |
+-----------------------------------------------------------------------------------+
                   |                                           |
                   | (REST / WebSocket)                        | (ADB Reverse / WS)
                   v                                           v
+------------------------------------+       +--------------------------------------+
|     DESKTOP FRONTEND (Port 5173)   |       |       ANDROID MOBILE (Flutter)       |
|  - TelemetryContext (State Hub)    |       |  - AppState & WebSocket Client       |
|  - Dashboard Page                  |       |  - Patient Roster Screen             |
|  - Patient Focus Page              |       |  - Patient Detail Screen             |
|  - Analytics Page                  |       |  - Alert Screen & Notification System|
|  - Alert Center Page               |       |  - Acknowledgement Lifecycle         |
+------------------------------------+       +--------------------------------------+
```

---

## 2. Layer-by-Layer Inventory & Data Models

### A. Part 1 Simulator (`part1/backend`)
- **`app/main.py`**: Lifespan auto-seeds demo patient `PATIENT-001` and starts simulation in `DEMO_MODE`.
- **`app/services/patient_registry.py`**: In-memory registry of active simulation patients (`PATIENT-001`..`004`, `ARGUS-AUDIT-*`, MIMIC cohort).
- **`app/services/simulation_service.py`**: Runs 1Hz simulation clock loop emitting `vital_event` payloads.
- **`app/simulation/mimic_replay.py`**: Loads retrospective MIMIC-IV ICU stay trajectories.
- **`app/api/v1/endpoints/stream.py`**: Exposes `/api/v1/stream` WebSocket endpoint.

### B. Part 1 -> Part 2 Bridge (`src/backend/services/part1_ws_bridge.py`)
- Background async task `Part1WSBridgeService`.
- Connects to `ws://127.0.0.1:8001/api/v1/stream`.
- Receives raw telemetry packets, maps fields to Part 2 `VitalUpdate` structure, and calls `InferenceRuntime.process_vital_event()`.

### C. Part 2 CDS Backend (`src/backend`)
- **`src/backend/services/inference_runtime.py`**:
  - Maintains `patient_windows` (timestamped vital history per patient).
  - Computes 31 canonical features (HR, MAP, Temp, RR, SpO2, Lactate, 4h slopes, 4h means, deltas, shock index, qSOFA, etc.).
  - Runs `logistic-regression-v1`, Sigmoid calibration, and SHAP attributions.
- **`src/backend/services/smart_alert_engine.py`**:
  - Tracks alert states per patient (`LOW`, `YELLOW_WATCH`, `ORANGE_REVIEW`, `RED_URGENT`).
  - Emits alerts when risk exceeds policy bands and window persistence criteria.
- **`src/backend/services/alert_router.py`**:
  - Maps patients to assigned staff users/devices and dispatches alerts over Part 2 WebSocket.
- **`src/backend/db/store.py`**:
  - SQLAlchemy SQLite/PostgreSQL store for Patients, Vitals, Predictions, Alerts, Staff, Assignments, Devices, Acknowledgements.
- **`src/backend/api/v1/endpoints/ws.py`**:
  - Exposes `ws://<host>:8000/api/v1/ws/stream?token=<JWT>` for authenticated frontend and mobile clients.

### D. Desktop Frontend (`src/frontend/src`)
- **`contexts/TelemetryContext.tsx`**: React context managing live telemetry state (`patientsMap`, `vitalsMap`, `predictionsMap`, `trajectoriesMap`, `alertsMap`).
- **`pages/Dashboard.tsx`**: Overview cards, ICU roster table, telemetry health indicator.
- **`pages/PatientFocus.tsx`**: Deep dive into vitals, live charts, SHAP breakdown.
- **`pages/AnalyticsPage.tsx`**: Population-level sepsis analytics and risk trajectory trends.
- **`pages/AlertCenter.tsx`**: Active alerts dashboard and acknowledgement action buttons.

### E. Android Mobile App (`part3/mobile`)
- **`lib/presentation/state/app_state.dart`**: Central MobX/Provider app state.
- **`lib/data/ws_client.dart`**: WebSockets listener processing `vital_event`, `prediction`, `alert_emitted` messages.
- **`lib/data/api_client.dart`**: REST client for login, patient roster, vitals, risk, alert acknowledgement.
- **`lib/services/notification_service.dart`**: Triggering device sound, vibration, and push notification overlays.

---

## 3. Identified Data Flow Weaknesses & Root Causes to Audit

1. **Patient Registry Mismatches**:
   - Part 1 Simulator auto-seeds `PATIENT-001` and 10 MIMIC stay IDs (`MIMIC-38197705`, etc.), but does not seed `PATIENT-002`..`004` or `MIMIC-1001`..`1013` by default.
   - Part 2 DB / Frontend hardcodes `PATIENT-001`..`004` or `MIMIC-1001`..`1013`, causing 404s/empty fallbacks for non-existent patients.
2. **Bridge Patient Registration**:
   - When Bridge ingests a Part 1 patient event, Part 2 backend must ensure the patient record exists in Part 2 DB/registry so all endpoints (`/api/v1/patients/{id}`, `/vitals`, `/risk`, `/icu/overview`) return valid data for every active patient stream.
3. **Alert Acknowledgement Lifecycle**:
   - Mobile acknowledgement must record the specific `alert_id` as ACKNOWLEDGED, but MUST NOT stop the bridge telemetry or prevent subsequent high-risk predictions from generating NEW alerts with unique `alert_id`s.
4. **Analytics Page Hydration**:
   - Analytics Page must query active runtime database records (predictions, vitals, alerts) rather than static or cached snapshots.
5. **Patient Focus Data Freshness**:
   - TelemetryContext must ensure incoming WebSocket prediction/vital events take precedence over stale REST baseline responses (even if risk score is 0.0, timestamp comparison must determine freshness).

---
*End of Architecture Audit Document.*
