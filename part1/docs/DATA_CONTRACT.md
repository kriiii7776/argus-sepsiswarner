# ARGUS Data Contract Specification v1.0

**Status:** Frozen  
**System Layer:** ARGUS Part 1 — Data Source & Simulation Platform  
**Target Consumer:** ARGUS Part 2 & External Analytics Pipeline  

---

## 1. Overview & Architectural Boundary

The ARGUS Data Contract v1.0 defines the strict JSON payload structures exchanged between ARGUS Part 1 (Data Source & Simulation Platform) and external consumers (such as ARGUS Part 2 AI/Analytics Pipeline).

### Key Constraints:
- **Contract-Driven Decoupling:** Part 2 MUST NOT import simulator internal Python classes, access the simulator database directly, or rely on scenario engine internals. All data exchange occurs exclusively over REST APIs and WebSockets adhering strictly to this contract.
- **Non-Clinical Designation:** Part 1 generates synthetic observations or replays historical data. Scenario and quality metadata describe simulation/sensor states only and DO NOT represent clinical diagnoses, risk scores, or treatment recommendations.

---

## 2. Global Message Header & Identity Rules

Every message emitted by the ARGUS platform MUST include explicit identity, schema versioning, time tracking, and source tags.

### Mandatory Metadata Fields:
| Field | Type | Format / Constraints | Description |
|---|---|---|---|
| `schema_version` | String | Fixed (e.g., `"1.0"`) | Contract version for backward compatibility validation. |
| `message_type` | Enum | `vital_update`, `patient_event`, `sensor_event`, `simulation_event`, `clinical_update` | Identifies the payload type. |
| `patient_id` | String | Non-empty string / UUID | Stable, unique identifier for the simulated patient across session lifecycle. |
| `session_id` | String | Non-empty string / UUID | Unique identifier for the specific simulation run or replay session. |
| `source` | Enum / String | `"synthetic"`, `"csv_replay"`, `"mimic_iv"` | Source origin of the observation or event. |
| `timestamp` | String (ISO-8601) | YYYY-MM-DDTHH:MM:SS.sssZ | Wall-clock time (UTC) when the message was constructed/emitted. |
| `simulation_time` | String (ISO-8601) | YYYY-MM-DDTHH:MM:SS.sssZ | Virtual time (UTC) of the simulated patient observation. |

### Time Semantics:
- **Wall-Clock Time (`timestamp`):** The actual system execution time when the payload is serialized and dispatched.
- **Simulation Time (`simulation_time`):** The internal time axis of the ICU patient model. For time-accelerated (e.g., 5x, 10x) or historical replay simulations, consumers (Part 2) MUST use `simulation_time` to reconstruct chronological patient timelines accurately.
- **Timezone Requirement:** All timestamps MUST be formatted as ISO-8601 with explicit `Z` suffix representing UTC (e.g., `2026-10-01T13:30:00.000Z`).

---

## 3. Vital Sign Observations & Quality Metadata

The `vital_update` message type encapsulates high-frequency physiological vital sign observations.

### Vital Fields & Explicit Units:
| Vital Field | Target Type | Unit | Range / Constraints | Description |
|---|---|---|---|---|
| `heart_rate` | Float / Null | `bpm` | 0 – 300 | Heart rate in beats per minute. |
| `systolic_bp` | Float / Null | `mmHg` | 0 – 300 | Systolic blood pressure. |
| `diastolic_bp` | Float / Null | `mmHg` | 0 – 300 | Diastolic blood pressure. |
| `spo2` | Float / Null | `%` | 0.0 – 100.0 | Oxygen saturation percentage. |
| `temperature` | Float / Null | `°C` | 20.0 – 45.0 | Core body temperature in Celsius. |
| `respiratory_rate` | Float / Null | `breaths/min` | 0 – 100 | Respiratory rate in breaths per minute. |

### Data Quality Metadata (`quality_status`):
Every vital reading or update includes a `quality_status` enum indicating measurement fidelity:
- `valid`: Reading measured within expected sensor operating tolerances.
- `missing`: Measurement value missing or unavailable from source stream.
- `sensor_unavailable`: Hardware sensor not connected or non-responsive.
- `delayed`: Measurement received after transmission lag.
- `stale`: Measurement value un-updated past expected refresh interval.
- `invalid`: Out-of-bounds artifact or unphysiological corrupted value.
- `disconnected`: Sensor lead disconnected during monitoring.
- `reconnected`: Sensor lead restored after disconnect.

*Note:* Part 1 does NOT impute missing values. If a vital is missing or invalid, the value MAY be `null` and the `quality_status` MUST explicitly reflect the degraded state.

### Scenario State Metadata (`scenario_state`):
Describes the active state machine condition of the simulation model (NOT a clinical diagnosis):
- `stable`: Patient baseline physiological equilibrium.
- `gradual_deterioration`: Progressive trend change in baseline physiological parameters.
- `rapid_deterioration`: Acute trend change in baseline parameters.
- `recovery`: Physiological trend returning toward baseline.
- `noisy`: Heightened measurement variation and noise injection active.
- `sensor_failure`: Active simulation of lead detachment or signal degradation.
- `data_quality_problem`: Injected intermittent missingness or packet corruption.

---

## 4. Message Schemas

### 4.1 `vital_update`
Emitted periodically (e.g., every 1 second simulated time) containing current vital measurements.

```json
{
  "schema_version": "1.0",
  "message_type": "vital_update",
  "patient_id": "P-98402",
  "session_id": "SESS-2026-1001-01",
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

### 4.2 `patient_event`
Emitted when patient baseline or static demographic/session parameters are updated.

```json
{
  "schema_version": "1.0",
  "message_type": "patient_event",
  "patient_id": "P-98402",
  "session_id": "SESS-2026-1001-01",
  "source": "synthetic",
  "timestamp": "2026-10-01T13:30:00.000Z",
  "simulation_time": "2026-10-01T08:00:00.000Z",
  "event_name": "admission_baseline_set",
  "payload": {
    "age": 62,
    "gender": "M",
    "baseline_heart_rate": 75.0,
    "baseline_systolic_bp": 120.0,
    "baseline_diastolic_bp": 80.0
  }
}
```

### 4.3 `sensor_event`
Emitted when a physical or simulated sensor state transition occurs.

```json
{
  "schema_version": "1.0",
  "message_type": "sensor_event",
  "patient_id": "P-98402",
  "session_id": "SESS-2026-1001-01",
  "source": "synthetic",
  "timestamp": "2026-10-01T13:30:05.000Z",
  "simulation_time": "2026-10-01T08:00:05.000Z",
  "sensor_type": "spo2_probe",
  "event_type": "disconnected",
  "details": "Lead detached or motion artifact saturated photodiode"
}
```

### 4.4 `simulation_event`
Emitted when simulation engine parameters or state transitions occur (e.g. clock speed changes, scenario state transitions, pause/resume).

```json
{
  "schema_version": "1.0",
  "message_type": "simulation_event",
  "patient_id": "P-98402",
  "session_id": "SESS-2026-1001-01",
  "source": "synthetic",
  "timestamp": "2026-10-01T13:30:10.000Z",
  "simulation_time": "2026-10-01T08:00:10.000Z",
  "event_type": "scenario_transition",
  "previous_state": "stable",
  "new_state": "gradual_deterioration",
  "speed_factor": 1.0
}
```

### 4.5 `clinical_update`

Emitted at a lower cadence than monitor telemetry. It represents laboratory, charted-output, neurological, and medication context from the EHR/replay stream. Consumers must select results using `recorded_at <= simulation_time`; they must never use a future clinical result for an earlier prediction.

```json
{
  "schema_version": "1.0",
  "message_type": "clinical_update",
  "patient_id": "P-98402",
  "session_id": "SESS-2026-1001-01",
  "source": "csv_replay",
  "timestamp": "2026-10-01T13:31:00.000Z",
  "simulation_time": "2026-10-01T08:01:00.000Z",
  "recorded_at": "2026-10-01T08:01:00.000Z",
  "data_origin": "synthetic_demo_replay",
  "clinical_context": {
    "platelets": 105,
    "bilirubin": 2.8,
    "creatinine": 2.1,
    "lactate": 3.9,
    "pao2_fio2_ratio": 210,
    "glasgow_coma_scale": 11,
    "urine_output_6h": 170,
    "norepinephrine_dose": 0.12
  }
}
```

---

## 5. Standard API Error Format

All REST and WebSocket error notifications produced by the simulator MUST conform to this standard JSON error schema:

```json
{
  "error": {
    "code": "INVALID_SIMULATION_STATE",
    "message": "Cannot speed up a paused simulation session.",
    "details": {
      "session_id": "SESS-2026-1001-01",
      "current_status": "paused"
    },
    "timestamp": "2026-10-01T13:30:15.000Z"
  }
}
```

---

## 6. Transport Specifications

### 6.1 WebSocket Stream
- **Endpoint:** `ws://<host>:<port>/api/v1/ws/simulation/{session_id}`
- **Format:** JSON strings compliant with section 4 message formats.
- **Heartbeat:** Periodical `simulation_event` with `event_type: "heartbeat"`.

### 6.2 REST Control Expectations
- **Endpoints:**
  - `POST /api/v1/simulation/start`: Initiates a new simulation session.
  - `POST /api/v1/simulation/pause`: Pauses active simulation clock.
  - `POST /api/v1/simulation/speed`: Updates simulation speed multiplier (e.g., `1.0`, `5.0`, `10.0`).
  - `GET /api/v1/patients/{patient_id}/vitals`: Retrieves recent vital sign history.
  - `GET /api/v1/patients/{patient_id}/clinical-context`: Retrieves the latest clinical result available as of the current (or supplied) simulation timestamp.
- Response payloads match specified Pydantic schemas or standard error format.

---

## 7. Versioning & Backward Compatibility Strategy

- **Major Schema Changes (e.g. 1.0 -> 2.0):** Incompatible structural changes (field removals or renames) increment the major version number.
- **Minor Schema Changes (e.g. 1.0 -> 1.1):** Additive optional fields do not break consumer contracts.
- **Strict Validation:** Consumers validating with Pydantic schemas set `extra = "ignore"` or `"forbid"` as configured by consumer policy. Part 1 strictly emits `schema_version: "1.0"`.
