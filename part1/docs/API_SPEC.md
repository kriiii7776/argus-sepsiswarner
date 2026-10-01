# ARGUS Simulator REST & WebSocket API Specification v1.0

**Status:** Frozen  
**Base REST URL:** `http://localhost:8000/api/v1`  
**WebSocket Stream:** `ws://localhost:8000/api/v1/stream`  

---

## 1. Global API Standards

- **API Versioning:** All endpoints are versioned with the `/api/v1/` route prefix.
- **Payload Validation:** Request bodies are strictly validated using Pydantic schemas. Unprocessable payloads return HTTP `422 Unprocessable Entity` formatted according to the standard error contract.
- **Error Contract:** All REST errors (HTTP 4xx / 5xx) adhere strictly to `APIErrorResponse`:
  ```json
  {
    "error": {
      "code": "PATIENT_NOT_FOUND",
      "message": "Patient 'P-INVALID' not found.",
      "details": {},
      "timestamp": "2026-10-01T13:30:00.000Z"
    }
  }
  ```

---

## 2. System & Health Endpoints

### 2.1 `GET /health`
- **Description:** Returns high-level operational status, version, and active environment.
- **Headers:** None required.
- **Response `200 OK`:**
  ```json
  {
    "status": "healthy",
    "service": "ARGUS Data Source & Simulation Platform",
    "version": "1.0.0",
    "environment": "development",
    "timestamp": "2026-10-01T13:30:00.000Z"
  }
  ```

---

## 3. Patient Baseline & Lifecycle Management

### 3.1 `GET /api/v1/patients`
- **Description:** Lists registered simulation patients with options to filter by status (`active`, `paused`, `discharged`, `inactive`).
- **Query Parameters:** `status` (optional enum)
- **Response `200 OK`:**
  ```json
  [
    {
      "patient_id": "P-98402",
      "session_id": "SESS-1001",
      "age": 62,
      "sex": "M",
      "profile_type": "standard",
      "status": "active",
      "baseline": {
        "heart_rate": 74.0,
        "systolic_bp": 122.0,
        "diastolic_bp": 78.0,
        "spo2": 98.0,
        "temperature": 36.8,
        "respiratory_rate": 15.0
      },
      "created_at": "2026-10-01T12:00:00.000Z",
      "updated_at": "2026-10-01T12:00:00.000Z"
    }
  ]
  ```

### 3.2 `GET /api/v1/patients/{patient_id}`
- **Description:** Retrieves patient profile and baseline details.
- **Error Response `404 Not Found`:** Returned when `patient_id` is missing in registry.

### 3.3 `POST /api/v1/patients`
- **Description:** Creates a new synthetic patient with a baseline generated from a specified `profile_type` (`standard`, `athletic`, `geriatric`, `hypertensive`, `icu_baseline`) and optional random `seed`.
- **Request Body:**
  ```json
  {
    "profile_type": "hypertensive",
    "age": 58,
    "seed": 42
  }
  ```
- **Response `201 Created`:** Patient object JSON payload.

### 3.4 `POST /api/v1/patients/{patient_id}/scenario`
- **Description:** Sets the active state-machine trajectory scenario (`stable`, `gradual_deterioration`, `rapid_deterioration`, `recovery`, `noisy`, `sensor_failure`, `data_quality_problem`) for the given patient.
- **Request Body:**
  ```json
  {
    "scenario_name": "gradual_deterioration"
  }
  ```
- **Response `200 OK`:** `SimulationStatusResponse` summary payload.

---

## 4. Simulation Clock & Control Endpoints

### 4.1 `POST /api/v1/simulation/start`
- **Description:** Starts or restarts the virtual simulation clock.
- **Request Body (Optional):**
  ```json
  {
    "speed_factor": 1.0,
    "patient_id": "P-98402"
  }
  ```
- **Response `200 OK`:** `SimulationStatusResponse`.

### 4.2 `POST /api/v1/simulation/pause`
- **Description:** Pauses simulation clock time advancement without losing accumulated state.
- **Response `200 OK`:** `SimulationStatusResponse` (`clock_status.state = "paused"`).

### 4.3 `POST /api/v1/simulation/resume`
- **Description:** Resumes simulation clock time progression.
- **Response `200 OK`:** `SimulationStatusResponse` (`clock_status.state = "running"`).

### 4.4 `POST /api/v1/simulation/stop`
- **Description:** Stops clock execution and resets scenario state machine.
- **Response `200 OK`:** `SimulationStatusResponse` (`clock_status.state = "stopped"`).

### 4.5 `POST /api/v1/simulation/speed`
- **Description:** Sets simulation clock speed multiplier (`1.0`, `5.0`, `10.0`, `30.0`, `60.0`).
- **Request Body:**
  ```json
  {
    "speed_factor": 10.0
  }
  ```
- **Response `200 OK`:** `SimulationStatusResponse`.

### 4.6 `GET /api/v1/simulation/status`
- **Description:** Retrieves structured status summary of current clock state, active patient, active session, and active scenario trajectory phase.
- **Response `200 OK`:**
  ```json
  {
    "clock_status": {
      "state": "running",
      "speed_factor": 5.0,
      "wall_clock_time": "2026-10-01T13:30:00.000Z",
      "simulation_time": "2026-10-01T14:15:00.000Z",
      "elapsed_sim_seconds": 2700.0,
      "elapsed_wall_seconds": 540.0
    },
    "active_session_id": "SESS-1001",
    "active_patient_id": "P-98402",
    "active_scenario_name": "gradual_deterioration",
    "active_scenario_state": "DETERIORATING",
    "registered_patients_count": 1
  }
  ```
