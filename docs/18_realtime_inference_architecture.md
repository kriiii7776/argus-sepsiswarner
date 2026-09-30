# SepsisGuard Real-Time Local Architecture

## Flow

```
Synthetic patient simulator → POST /v1/events/vitals → validation → causal feature generation → model inference → uncertainty → explanation → smart alert → PostgreSQL + WebSocket → React dashboard
```

The local implementation is under `deployment/`. The simulator generates parameterized noisy mathematical trajectories for integration testing only. It does not represent actual patient physiology, clinical distributions, or outcomes.

## Components

| Component | Local implementation | Responsibility |
|---|---|---|
| Ingestion/API | FastAPI | Validate timestamped vital events, inference, response. |
| Feature service | `backend/app/service.py` | Current/past-only history and tabular feature contract. |
| Prediction | Saved XGBoost or explicit development fallback | Risk estimate; fallback status is in every response. |
| Uncertainty/explanation | Existing layers; compact factors in local serving | Reliability and non-causal factors. |
| Alerts | Stateful smart-alert engine | Hysteresis, persistence, de-duplication. |
| PostgreSQL | `vital_events`, `predictions`, `alerts` | Durable event/audit store. |
| WebSocket | `/v1/stream` | Prediction and alert delivery. |
| React/Vite | Development console | Risk and alert display. |

Redis is not required for the single-process local service. Enable it for multi-worker/multi-instance production as Pub/Sub fan-out and short-retention replay; in-memory WebSocket subscribers cannot scale across processes.

## API and event contracts

| Method/path | Request | Response |
|---|---|---|
| `GET /health` | none | service/model state and demo-model status |
| `POST /v1/events/vitals` | `VitalEvent` | `PredictionResponse`, 201 |
| `GET /v1/patients/{patient_id}/latest` | none | latest persisted prediction |
| `POST /v1/simulator/start` | count, duration, cadence | synthetic-stream status |
| `WS /v1/stream` | keepalive text | prediction and alert envelopes |

`VitalEvent` has patient ID, source, timestamp, HR, MAP, RR, SpO₂, temperature, and optional lactate. `PredictionResponse` has prediction timestamp, six-hour horizon, risk, interval, confidence, signal quality, severity/review level, factors, latency, model version, and `is_demo_model`.

WebSocket JSON envelope:

```json
{"type":"prediction","occurred_at":"2026-01-01T12:00:00Z","patient_id":"SIM-001","payload":{"risk_probability":0.42}}
```

Types: `vital_event`, `prediction`, `alert`, `simulator_status`, `error`.

## Database, latency, and failures

`vital_events(id, patient_id, timestamp, payload JSON, source)` is raw ingestion audit data. `predictions(id, patient_id, timestamp, risk, payload JSON, model_version)` is the served response. `alerts(id, patient_id, timestamp, severity, payload JSON)` stores alert decisions. Add `(patient_id,timestamp)` indexes, migrations, retention, encryption, and access control before non-local use.

Initial targets to measure under load: p95 event-to-response under 250 ms, p99 under 500 ms, WebSocket fan-out under 1 second, and alert logic under 10 ms excluding inference. TreeSHAP and temporal integrated gradients can exceed the synchronous budget: cache same-anchor results or emit a follow-up explanation event, never reuse a different timestamp.

Schema errors return 422 and create no prediction. Inference errors are logged with patient ID, timestamp, model version, and error type, return sanitized 422, and emit no alert. Production database-write failure must return 503 via a transaction/outbox flow. Logs must not expose secrets or unauthorized identifiers.

## Local deployment

```powershell
docker compose -f deployment/docker-compose.yml up --build
```

Open `http://localhost:5173`; click **Start synthetic stream**. OpenAPI docs: `http://localhost:8000/docs`. Stop using `docker compose -f deployment/docker-compose.yml down`. This is development infrastructure only, not a clinical deployment.
