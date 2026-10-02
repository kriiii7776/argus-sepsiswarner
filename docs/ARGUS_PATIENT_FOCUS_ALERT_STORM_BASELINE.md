# ARGUS Patient Focus & Alert Storm Forensic Baseline Document

## System Metadata
- **Date**: October 2, 2026
- **Branch**: `main`
- **Frontend URL**: `http://localhost:5173`
- **Backend REST URL**: `http://127.0.0.1:8000/api/v1`
- **Backend WebSocket Stream**: `ws://127.0.0.1:8000/api/v1/ws/stream`
- **Part 1 Simulator REST URL**: `http://127.0.0.1:8001/api/v1`
- **Part 1 WebSocket Stream**: `ws://127.0.0.1:8001/api/v1/stream`
- **Database**: PostgreSQL (`sepsisguard` database on `argus_postgres:5432`)
- **Active ML Model**: `logistic-regression-v1` (Calibrated, 31 Temporal Features)
- **Current Database Row Counts**:
  - `vital_events`: 79,248
  - `predictions`: 79,248
  - `alerts`: 58
  - `alert_acknowledgements`: 52
  - `patients`: 26

---

## Observed Runtime Issues

### 1. Patient Focus Infinite Update Loop
- **Symptom**: `Maximum update depth exceeded` exception caught by React `ErrorBoundary`.
- **Root Cause**: In `PatientDetailsPage.tsx`, `getPatientTelemetry(patientId)` returned a newly instantiated object `{ patient, vitals, prediction, trajectory, alerts }` on every render pass. An `useEffect` depending on `[liveData, patientId]` executed on every render and called `setState(...)` (`setPatient`, `setVitals`, etc.), driving an infinite React state update loop.

### 2. Alert Storm / Duplicate Alert Emission
- **Symptom**: Alert Center showed over 180 duplicate RED URGENT alert cards for the same patient.
- **Root Cause**: In `TelemetryContext.tsx`, WebSocket prediction events with `alert_severity !== 'NONE'` generated a new timestamp-based key `alert-${eventPatientId}-${timestamp}` in `alertsMap` for every single incoming prediction event (1 per second), treating continuous predictions for an active alert episode as 180 separate alert cards.

---

## Repair Strategy
1. **Patient Focus Data Flow**:
   - Refactor `PatientDetailsPage.tsx` to read `liveData` directly from `useTelemetry()` context alongside REST fallback state.
   - Remove state-synchronization `useEffect` hooks that call `setState` on every `liveData` object change.
   - Keep REST hydration effect strictly dependent on `[patientId, refreshTrigger]`.

2. **Alert Episode Deduplication**:
   - Update `TelemetryContext.tsx` alert mapping to key active alerts per patient episode (`alert-${eventPatientId}`).
   - Update existing active alert card values (risk score, timestamp, severity, recommended action) in-place during ongoing prediction streams instead of appending new duplicate cards.
   - Respect backend `alert_emitted` lifecycle signals for notification sounds/vibrations.
