# ARGUS — Full System Forensic Audit Baseline Report

**Document ID:** `ARGUS-DOC-AUDIT-BASELINE-20261002`  
**Date:** October 2, 2026  
**Status:** PHASE 0 SAFE BASELINE ESTABLISHED  
**Target Repository:** `c:\Users\HP\Desktop\Argus\argus-sepsiswarner`

---

## 1. Repository & Branch State

- **Active Branch:** `feature/argus-part2-phase7b`
- **Upstream:** `origin/feature/argus-part2-phase7b`
- **Latest Commit:** `29c18fc9283d7c326307147896a0d2b4c23fb3d4` (`feat(argus): integrate part1 simulator with part2`)
- **System Operating System:** Windows 11 (PowerShell)

---

## 2. Infrastructure & Component Architecture

### Part 1 Simulator (`argus_part1_simulator`)
- **Location:** `part1/backend`
- **Container Port:** `8001:8001`
- **Data Dir:** `part1/data/mimic-iv-demo`
- **Source Modes:** `SIMULATION` / `REPLAY`

### Part 2 Clinical Intelligence Backend (`argus_part2_backend`)
- **Location:** `src/backend`
- **Container Port:** `8000:8000`
- **DB Connection:** `postgresql+psycopg://sepsisguard:sepsisguard@postgres:5432/sepsisguard`
- **Inference Runtime:** Calibrated `logistic-regression-v1` with 31 canonical temporal features & SHAP explainability.

### Database (`argus_postgres`)
- **Engine:** PostgreSQL 16 Alpine
- **Container Port:** `5432:5432`
- **Database:** `sepsisguard` (Tables: `patients`, `vital_events`, `predictions`, `alerts`, `staff_users`, `patient_assignments`, `device_registrations`)

### Part 3 Desktop Command Center
- **Framework:** React 19 + TypeScript + Vite
- **Dev Server Port:** `5173`
- **Key State Store:** `TelemetryContext` + `AuthContext`

### Part 3 Mobile Application
- **Framework:** Flutter (Android)
- **Target Package:** `com.example.argus_mobile`
- **Physical Device ID:** `121933145H110037`

---

## 3. Observed Diagnostic Findings (Pre-Fix Audit)

1. **Patient Focus 401 Auth Error:** Patient Details page makes fetch calls to `/api/v1/patients/{id}`, `/vitals`, `/risk`, `/alerts` requiring JWT Bearer token authentication. When token is missing, invalid, or headers fail, API returns HTTP 401 Unauthorized.
2. **Analytics Empty Graph:** Analytics page relied on local or isolated state stores instead of reading live `predictionsMap` / `trajectoriesMap` from `TelemetryContext`.
3. **Settings Loading State:** Settings page lacked loading/error/fallback handling when optional staff profile metadata returned empty or non-200.
4. **Dashboard MIMIC Cohort Visibility:** Dashboard default patient list was restricted to `DEFAULT_PATIENT_IDS` (`['PATIENT-001', 'PATIENT-002', 'PATIENT-003', 'PATIENT-004']`), omitting MIMIC cohort stays (`MIMIC-*`) unless fetched dynamically.
5. **Mobile Acknowledgement State Handling:** Acknowledgement must set alert lifecycle status to `ACKNOWLEDGED` without clearing patient risk score, vitals, or roster presence.

---

## 4. Baseline Sign-Off

Baseline audit documented. Proceeding to systematic forensic investigation and pipeline repairs.
