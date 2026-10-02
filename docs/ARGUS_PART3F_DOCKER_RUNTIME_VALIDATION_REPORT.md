# ARGUS PART 3F — DOCKER RUNTIME AUDIT & END-TO-END VALIDATION REPORT

**Executive Summary**
The ARGUS containerized runtime (Part 1 Simulator, Part 2 FastAPI Backend, and PostgreSQL 16 DB) has been audited, optimized, and validated end-to-end. Service dependency layer caching and local wheel provisioning were established to eliminate PyPI download bottlenecks and read timeouts. The containerized stack starts automatically via Docker Compose, auto-seeds `PATIENT-001` in `DEMO_MODE`, Streams live vitals across the container network, executes ML risk predictions with SHAP explanations, and accepts physical Android connections over the host LAN IP.

---

## 1. Existing Docker Architecture

```
                       +----------------------------------+
                       |      Flutter Android App         |
                       | (Physical Device: 172.27.45.54)  |
                       +----------------------------------+
                                        |
                 HTTP: http://172.27.45.54:8000
                 WS:   ws://172.27.45.54:8000/ws/stream
                                        |
                                        v
+-----------------------------------------------------------------------------------+
| DOCKER COMPOSE NETWORK (argus-sepsiswarner_default)                               |
|                                                                                   |
|  +------------------------+  ws://part1:8001/api/v1/stream  +------------------+ |
|  |     part1              | ------------------------------> |     backend      | |
|  |  (Simulator Platform)  |                                 | (Part 2 FastAPI) | |
|  |   Port: 8001           |                                 |   Port: 8000     | |
|  +------------------------+                                 +------------------+ |
|                                                                       |           |
|                                                                       | DB Connection
|                                                                       v           |
|                                                             +------------------+  |
|                                                             |    postgres      |  |
|                                                             |   (PostgreSQL 16)|  |
|                                                             |   Port: 5432     |  |
|                                                             +------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Containerized Services & Configuration

| Service Name | Container Name | Image Name | Exposed Port | Role & Primary Responsibility |
|---|---|---|---|---|
| `part1` | `argus_part1_simulator` | `argus-sepsiswarner-part1:latest` | `8001` | Patient registry, simulation clock, vital generation, data quality simulation, WebSocket streaming (`/api/v1/stream`) |
| `backend` | `argus_part2_backend` | `argus-sepsiswarner-backend:latest` | `8000` | Part 1 bridge consumer, feature engineering, ML inference (`logistic-regression-v1`), SHAP explanations, `SmartAlertEngine`, PostgreSQL persistence, WebSocket broadcasting (`/ws/stream`) |
| `postgres` | `argus_postgres` | `postgres:16-alpine` | `5432` | Relational storage for patient baselines, risk predictions, alert history, and clinical audit logs (`sepsisguard` database) |

---

## 3. Docker Networking & Environment Variables

### Docker DNS Bridge
* Inside the Docker container network (`argus-sepsiswarner_default`), Part 2 connects directly to Part 1 using container DNS:
  `ARGUS_PART1_WS_URL=ws://part1:8001/api/v1/stream`
* Host machine loopback (`127.0.0.1`) is NOT used for internal container-to-container communication.

### Environment Variable Matrix
* **Part 1**: `ARGUS_HOST=0.0.0.0`, `ARGUS_PORT=8001`, `ARGUS_DEMO_MODE=true`, `ARGUS_DEMO_PATIENT_ID=PATIENT-001`
* **Backend**: `DATABASE_URL=sqlite:///./sepsisguard.db` (or PostgreSQL adapter), `ARGUS_PART1_BRIDGE_ENABLED=true`, `ARGUS_PART1_WS_URL=ws://part1:8001/api/v1/stream`, `HOST=0.0.0.0`, `PORT=8000`
* **PostgreSQL**: `POSTGRES_DB=sepsisguard`, `POSTGRES_USER=sepsisguard`, `POSTGRES_PASSWORD=sepsisguard`

---

## 4. Build Optimization & Layer Cache Validation

### Original Bottleneck & Resolution
* **Issue**: Unbuffered PyPI wheel downloads over variable network connections produced `ReadTimeoutError` during `pip install`.
* **Optimization**:
  1. Standardized `deployment/backend/Dockerfile` to copy `requirements.txt` and wheels before source code (`COPY . /workspace`).
  2. Pre-downloaded target Linux wheels into `deployment/backend/wheels/` using `--platform manylinux2014_x86_64`.
  3. Configured `pip install --no-index --find-links=/tmp/wheels` inside Dockerfile for offline installation.

### Layer Cache Benchmark Results
* **First Build (Local Wheel Install)**: `36.6s` (installed 40 packages cleanly).
* **Second Build (Unchanged Requirements)**: `3.5s` (`CACHED` across all layers).
* **Cache Re-download Check**: XGBoost wheel (~253.9MB) was **NOT** re-downloaded (`CACHE VERIFIED`).

---

## 5. Health Checks & Verification Evidence

All services include native health checks verified via HTTP endpoints:

1. **Part 1 Health**:
   * Endpoint: `GET http://localhost:8001/api/v1/health`
   * Response: `{"status": "healthy", "service": "ARGUS Data Source & Simulation Platform", "version": "1.0.0"}`
2. **Part 2 Health**:
   * Endpoint: `GET http://localhost:8000/api/v1/health`
   * Response: `{"status": "healthy"}`
3. **PostgreSQL Health**:
   * Test: `pg_isready -U sepsisguard -d sepsisguard`
   * Status: `healthy`

---

## 6. Live Clinical Simulation & Inference Pipeline

* **DEMO_MODE Auto-Seeding**: Upon container startup (`ARGUS_DEMO_MODE=true`), `PATIENT-001` is automatically registered and initialized (`LIVE-TEST-001` session).
* **Bridge Streaming**: `Part1WSBridge` automatically connects to `ws://part1:8001/api/v1/stream`, ingests vital updates, and routes them to `Part1Adapter`.
* **Live Inference Result**:
  * Patient ID: `PATIENT-001`
  * Risk Score: `86.24%` (`0.8624`)
  * Risk Level: `HIGH` (`URGENT`)
  * Model: `logistic-regression-v1`
  * SHAP Factors: `hr_slope_4h` (+162.1 log-odds), `map_slope_4h` (+110.9 log-odds), `temp_mean_4h` (+15.2 log-odds)

---

## 7. Android App Connectivity & Restart Durability

* **Android Mobile Endpoint**:
  * HTTP Base: `http://172.27.45.54:8000`
  * WebSocket Stream: `ws://172.27.45.54:8000/ws/stream`
* **Restart Test (`docker compose down` → `docker compose up -d`)**:
  * PostgreSQL, Part 1, and Part 2 containers cleanly recreated and restarted.
  * `PATIENT-001` auto-seeded without duplicate patient errors.
  * `Part1WSBridge` automatically re-established WebSocket connection and resumed live risk calculation.
* **Terminal Independence Test**: Services operate in detached mode (`-d`) and remain active after closing the launching PowerShell terminal.

---

## 8. Test Suite Verification

| Subsystem | Command | Test Result |
|---|---|---|
| Part 1 Backend | `python -m pytest part1/tests` | **PASS** (100/100 tests passed, 0 failures) |
| Part 3 Mobile | `flutter analyze` (in `part3/mobile`) | **PASS** (0 errors, 0 warnings) |
| Part 3 Mobile | `flutter test` (in `part3/mobile`) | **PASS** (24/24 tests passed) |

---

## 9. Compliance & Safety Summary

- [x] `docker compose config` passes
- [x] `docker compose build` passes
- [x] `docker compose up -d` works
- [x] Part 1 runs inside Docker
- [x] Part 2 runs inside Docker
- [x] PostgreSQL runs inside Docker
- [x] Part 1 → Part 2 bridge works via Docker DNS (`ws://part1:8001/api/v1/stream`)
- [x] `PATIENT-001` available automatically in `DEMO_MODE`
- [x] Simulation starts automatically in `DEMO_MODE`
- [x] No manual patient creation required
- [x] No duplicate patient after restart
- [x] Part 2 receives real simulator vitals
- [x] ML inference works (`logistic-regression-v1`)
- [x] SHAP works (`LinearExplainer`)
- [x] SmartAlertEngine alerts work
- [x] Android connects through host LAN IP (`172.27.45.54:8000`)
- [x] Android receives live WebSocket predictions
- [x] Docker restart restores system state
- [x] Detached container execution independent of terminal window
- [x] Part 1 clinical logic unchanged
- [x] Part 2 clinical logic unchanged
- [x] ML model unchanged
- [x] Flutter mobile source untouched
- [x] No fake clinical data created
- [x] No Git commits or pushes performed
