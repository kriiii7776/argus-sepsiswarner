# ARGUS External Integration Guide for Part 2 Consumers

**Target Audience:** External AI / Analytics Consumers (Part 2 Pipeline)  
**System Designation:** ARGUS Part 1 Data Source & Simulation Platform  

---

## 1. Connection Parameters

- **WebSocket Stream URL:** `ws://localhost:8000/api/v1/stream` (or session-filtered `ws://localhost:8000/api/v1/stream/{session_id}`)
- **REST Base API URL:** `http://localhost:8000/api/v1/`
- **Data Contract Version:** `"1.0"`
- **Demo data mode:** `mimic_iv` — recorded, de-identified MIMIC-IV Demo observations replayed at one source minute per wall-clock second. Missing observations are emitted as `null`; stale readings are labelled `stale` rather than generated.
- **Demo cohort metadata:** `GET /api/v1/replay/cohort` returns three `sepsis_warning_candidate` trajectories and seven `no_sepsis_warning_candidate` comparison trajectories. This is presentation metadata only and MUST NOT be supplied to the model as an input feature.
- **No-imputation rule:** The MIMIC replay never substitutes random or synthetic clinical values. Unrecorded source variables remain `null`. Total GCS, PaO₂/FiO₂, and six-hour urine output are deterministic, documented calculations using recorded MIMIC components only.
- **Authentication Requirements:** None (Open research/educational prototype interface).

---

## 2. Interface Examples

### 2.1 Example WebSocket Telemetry Message (`vital_update`)
```json
{
  "schema_version": "1.0",
  "message_type": "vital_update",
  "patient_id": "P-98402",
  "session_id": "SESS-2026-1001",
  "source": "synthetic",
  "timestamp": "2026-10-01T13:30:00.000Z",
  "simulation_time": "2026-10-01T08:00:00.000Z",
  "vitals": {
    "heart_rate": 84.0,
    "systolic_bp": 122.0,
    "diastolic_bp": 78.0,
    "spo2": 97.5,
    "temperature": 37.1,
    "respiratory_rate": 16.0
  },
  "vital_units": {
    "heart_rate": "bpm",
    "systolic_bp": "mmHg",
    "diastolic_bp": "mmHg",
    "spo2": "%",
    "temperature": "°C",
    "respiratory_rate": "breaths/min"
  },
  "quality_status": "valid",
  "scenario_state": "stable"
}
```

### 2.2 Example REST Request
`POST http://localhost:8000/api/v1/patients`
```json
{
  "profile_type": "hypertensive",
  "age": 62,
  "seed": 42
}
```

### 2.3 Example REST Response
`HTTP/1.1 201 Created`
```json
{
  "patient_id": "P-98402",
  "session_id": "SESS-2026-1001",
  "age": 62,
  "sex": "M",
  "profile_type": "hypertensive",
  "status": "active",
  "baseline": {
    "heart_rate": 80.0,
    "systolic_bp": 152.0,
    "diastolic_bp": 96.0,
    "spo2": 97.0,
    "temperature": 36.9,
    "respiratory_rate": 17.0
  },
  "created_at": "2026-10-01T13:30:00.000Z",
  "updated_at": "2026-10-01T13:30:00.000Z"
}
```

### 2.4 Example Error Response
`HTTP/1.1 404 Not Found`
```json
{
  "error": {
    "code": "PATIENT_NOT_FOUND",
    "message": "Patient 'P-INVALID' not found in registry.",
    "details": {},
    "timestamp": "2026-10-01T13:30:05.000Z"
  }
}
```
