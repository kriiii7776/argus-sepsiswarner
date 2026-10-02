# ARGUS Patient Focus Forensic Baseline Document

## System Metadata
- **Date**: October 2, 2026
- **Branch**: `main`
- **Frontend URL**: `http://localhost:5173`
- **Backend REST URL**: `http://127.0.0.1:8000/api/v1`
- **Backend WebSocket Stream**: `ws://127.0.0.1:8000/api/v1/ws/stream`
- **Part 1 Simulator REST URL**: `http://127.0.0.1:8001/api/v1`
- **Part 1 WebSocket Stream**: `ws://127.0.0.1:8001/api/v1/stream`
- **PostgreSQL Connection**: `postgresql://sepsisguard:sepsisguard@argus_postgres:5432/sepsisguard`
- **Authentication**: JWT Bearer token authentication (`argus-auth-*` / `fake-super-secret-token`)

---

## Architectural State Inventory

### TelemetryContext State Architecture
- **Global Maps**:
  - `patientsMap`: `Record<string, Patient>`
  - `vitalsMap`: `Record<string, VitalEvent>`
  - `predictionsMap`: `Record<string, PredictionResponse>`
  - `trajectoriesMap`: `Record<string, Array<{ timestamp: string; risk_probability: number; alert_severity?: string }>>`
  - `alertsMap`: `Record<string, AlertItem>`
- **Dynamic Patient Discovery**:
  All active keys across `patientsMap`, `vitalsMap`, `predictionsMap`, and `trajectoriesMap` are dynamically enumerated, ensuring MIMIC stays (`MIMIC-38197705`, `MIMIC-34617352`, etc.) are exposed in `patients` list.

### Patient Focus Hydration Flow
1. User selects a patient from Dashboard, Patients Roster, or Alert Center.
2. `activePatientId` is set to the specific selected ID (e.g. `MIMIC-38197705`).
3. `PatientDetailsPage` queries REST API endpoints (`/patients/{id}`, `/vitals`, `/risk`, `/trajectory`, `/explanation`, `/alerts`).
4. Live telemetry updates arriving over WebSocket merge into `TelemetryContext` and update `PatientDetailsPage` without throwing React errors.
5. `ErrorBoundary` wraps `PatientDetailsPage` to ensure unhandled React exceptions display a structured recovery UI instead of a black screen.
