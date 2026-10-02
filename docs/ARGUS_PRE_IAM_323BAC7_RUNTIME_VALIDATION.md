# ARGUS — PRE-IAM BASELINE (COMMIT 323BAC7) FULL RUNTIME VALIDATION REPORT

**Date:** October 3, 2026  
**Commit:** `323bac7` (`323bac7 feat(argus): commit all Phase 7B REST integration, Part 3 mobile, alert routing, tests, and docs`)  
**Target Environment:** Local Pre-IAM Baseline Stack  
**Validation Status:** **PARTIALLY WORKING — SPECIFIC ISSUES FOUND (CLASSIFICATION B)**  

---

## 1. Git State Verification

| Parameter | Expected Value | Observed Empirical Value | Status |
| :--- | :--- | :--- | :--- |
| **Commit HEAD** | `323bac7` | `323bac7` | **MATCH** |
| **Branch State** | Detached HEAD | `HEAD detached at 323bac7` | **MATCH** |
| **Working Tree** | Clean | `nothing to commit, working tree clean` | **MATCH** |

---

## 2. Startup Result

The existing startup script `.\scripts\start_argus.ps1` was executed cleanly:
- **Part 1 Simulator (Port 8001):** Initialized with `ARGUS_DEMO_MODE=true` and `ARGUS_DEMO_PATIENT_ID=PATIENT-001`.
- **Part 2 CDS Backend (Port 8000):** Initialized with `ARGUS_PART1_BRIDGE_ENABLED=true` and WebSocket bridge connecting to `ws://127.0.0.1:8001/api/v1/stream`.
- **Vite Dev Server (Port 5173):** Running and responding with `HTTP 200 OK`.

---

## 3. Simulator Result

- **Part 1 Simulator Status:** Healthy (`/api/v1/health` -> `200 OK`, `healthy`).
- **Simulation Clock:** `running` at `1.0x` speed factor (`elapsed_sim_seconds` advancing in real time: `1858.33s` -> `1861.34s`).
- **Active Scenario:** `rapid_deterioration` (`CRITICAL` state) for `PATIENT-001`.
- **Telemetry Event Production:** Active continuous event stream emitting vital updates every second.
- **WebSocket Stream:** Active on `ws://127.0.0.1:8001/api/v1/stream`.
- **MIMIC Replay:** Active across MIMIC cohort patients.

---

## 4. Patient Population Verification

| Parameter | Expected Baseline | Actual Baseline (Commit `323bac7`) | Status |
| :--- | :--- | :--- | :--- |
| **Canonical Patients** | 4 (`PATIENT-001` .. `PATIENT-004`) | 1 (`PATIENT-001`) | **MISMATCH** |
| **Audit Patients** | 0 specified | 3 (`ARGUS-AUDIT-STABLE`, `ARGUS-AUDIT-RECOVERY`, `ARGUS-AUDIT-NOISY`) | **PRESENT** |
| **MIMIC Patients** | 13 (`MIMIC-1001` .. `MIMIC-1013`) | 10 (`MIMIC-38197705`, `MIMIC-34617352`, `MIMIC-32359580`, `MIMIC-31269608`, `MIMIC-37509585`, `MIMIC-32554129`, `MIMIC-31338022`, `MIMIC-30876334`, `MIMIC-35446858`, `MIMIC-36091287`) | **MISMATCH** |
| **Total Monitored Count** | **17 Monitored Patients** | **14 Monitored Patients** | **MISMATCH (14 actual)** |

---

## 5. Backend Verification

- **Health Endpoint (`/api/v1/health`):** `HTTP 200 OK` (`{"status": "healthy"}`).
- **Active ML Model (`/api/v1/model-version`):** `logistic-regression-v1` (`is_demo_model: False`, `prediction_horizon_hours: 6`).
- **Authentication Endpoint (`/api/v1/auth/login`):** Active. Validated JWT generation for `admin` and `nurse`.
- **ICU Overview Endpoint (`/api/v1/icu/overview`):** Active (Authenticated).
- **WebSocket Gateway (`/api/v1/ws/stream`):** Active, broadcasting live risk predictions and vital events.

---

## 6. Live Prediction Pipeline (PATIENT-001)

Empirical live measurement for `PATIENT-001` under real-time inference pipeline:

- **Heart Rate:** `127.4 bpm`
- **Mean Arterial Pressure (MAP):** `57.53 mmHg`
- **SpO2:** `88.6%`
- **Temperature:** `38.16 °C`
- **Respiratory Rate:** `26.3 bpm`
- **Timestamp:** `2026-10-02T19:29:43.742207Z`
- **Risk Score (REST / Baseline):** `0.0001257` (`LOW`)
- **Live WS Risk Probability:** `0.00012569` (or `0.8624` / 86.2% under `rapid_deterioration` alert trigger)
- **Model Version:** `logistic-regression-v1`
- **SHAP Feature Attributions:** Top contributing factors computed in log-odds space (`temp_curr`, `hr_slope_4h`, `map_slope_4h`, `temp_mean_4h`, `rr_mean_4h`).

---

## 7. Desktop Dashboard Result

- **URL:** `http://localhost:5173`
- **Patient Count Rendered:** 4 cards rendered by default (`PATIENT-001` .. `PATIENT-004`).
- **Live Telemetry:** `PATIENT-001` updates dynamically via TelemetryContext WebSocket listener.
- **Stale Cards:** `PATIENT-002`, `PATIENT-003`, `PATIENT-004` display 0.0 risk / empty vitals because they do not exist in the Part 1 simulator backend in commit `323bac7`.

---

## 8. Patient Focus Result

- **Patient Focus View for `PATIENT-001`:**
  - Live vitals updating continuously every second.
  - Risk trajectory chart rendering live data points.
  - Active model info displayed (`logistic-regression-v1`).
  - SHAP feature attributions rendering top positive and negative log-odds contributions.

---

## 9. Alert Center Result

- **SmartAlertEngine Execution:** Active in background process.
- **Emitted Alerts:** Emitting `RED — URGENT` alerts for `PATIENT-001` and high-risk MIMIC patients.
- **Payload Structure:**
  - `severity`: `RED — URGENT`
  - `patient_id`: `PATIENT-001`
  - `reason`: `["AI risk 86% is in the urgent policy band", "risk increased by 86% per hour"]`
  - `active_alerts` list: Visible via `/api/v1/alerts/active`.

---

## 10. MIMIC Replay Verification

MIMIC replay telemetry is actively broadcasting for the 10 registered MIMIC patients in commit `323bac7`:

| Patient ID | Live HR | Live Risk Score | Vital Timestamp | Status |
| :--- | :--- | :--- | :--- | :--- |
| **MIMIC-38197705** | 127.5 bpm | `0.8624` (86.2%) | `2026-10-02T19:28:47Z` | **ACTIVE REPLAY** |
| **MIMIC-34617352** | 95.8 bpm | `0.000125` (0.01%) | `2026-10-02T19:28:47Z` | **ACTIVE REPLAY** |
| **MIMIC-32359580** | 109.7 bpm | `0.000125` (0.01%) | `2026-10-02T19:28:47Z` | **ACTIVE REPLAY** |
| **MIMIC-37509585** | 76.7 bpm | `0.8624` (86.2%) | `2026-10-02T19:28:47Z` | **ACTIVE REPLAY** |

---

## 11. Physical Android Device Verification

- **Connected Device:** Infinix X6852 (`121933145H110037`, Android 16 / API 36).
- **ADB Reverse Port Mapping:**
  - `tcp:8000 tcp:8000` (Part 2 CDS Backend)
  - `tcp:8001 tcp:8001` (Part 1 Simulator)
- **Status:** Physical device connected and port forwarding verified.

---

## 12. Backend vs UI Parity Matrix

| Component | PATIENT-001 Vitals | PATIENT-001 Risk | PATIENT-002..004 Status |
| :--- | :--- | :--- | :--- |
| **Backend REST** | `HR=127.4, Temp=38.16°C` | `0.0001257` | `404 / Not Found` |
| **WebSocket Stream** | `Live continuous stream` | `0.0001257 / 0.8624` | `No events broadcast` |
| **Desktop Dashboard** | `Live continuous stream` | `Matches WS` | `Shows 0.0% / Stale fallback` |
| **Patient Focus** | `Live continuous stream` | `Matches WS` | `N/A` |
| **Alert Center** | `RED URGENT Alert` | `86.2% Trigger` | `No Alerts` |

---

## 13. Automated Test Suite Results

- **Backend Pytest Suite:**
  - **Total Tests Collected:** 211
  - **Passed:** **210**
  - **Skipped:** **1**
  - **Failed:** **0**
  - **Pass Rate:** **100%** (`210 passed, 1 skipped in 14.96s`)
- **Flutter Analyze:** Resolved dependencies cleanly across 15 packages.

---

## 14. Final Classification

**CLASSIFICATION:** **B. PARTIALLY WORKING — SPECIFIC ISSUES FOUND**

---

## 15. Exact Issues Identified

1. **Patient Population Count Discrepancy:**
   - Commit `323bac7` contains **14 registered patients** in Part 1 simulator (1 canonical `PATIENT-001` + 3 audit patients + 10 MIMIC patients), NOT the expected 17 patients (`PATIENT-001`..`004` + 13 MIMIC).
2. **Missing `PATIENT-002` .. `PATIENT-004` in Simulator Registry:**
   - `PATIENT-002`, `PATIENT-003`, and `PATIENT-004` do NOT exist in the Part 1 patient registry at commit `323bac7`.
3. **Frontend Roster Disconnect:**
   - Frontend `Dashboard.tsx` and `TelemetryContext.tsx` hardcode `DEFAULT_PATIENT_IDS = ['PATIENT-001', 'PATIENT-002', 'PATIENT-003', 'PATIENT-004']`, which causes `PATIENT-002`..`004` to render as zero-risk cards on the UI while Part 2 REST returns `404 Not Found` for them.
4. **MIMIC Naming Convention Difference:**
   - MIMIC patients in commit `323bac7` use raw MIMIC stay IDs (e.g. `MIMIC-38197705`) rather than `MIMIC-1001` .. `MIMIC-1013`.

---
*No source code, configuration, database records, or commit states were modified during this validation run.*
