# ARGUS Part 2 — Phase 7B REST Integration Report

## 1. Objective

Connect the Phase 7A React/TypeScript frontend UI (`src/frontend/`) to the canonical Phase 6D backend REST APIs (`src/backend/`), replacing mock clinical data dependencies with live typed REST API calls, Bearer token authentication, and robust UI state management (Loading, Error, Empty, and Success).

## 2. Branch Verification

- **Active Development Branch:** `feature/argus-part2-phase7b`
- **Baseline Commit:** `e4e55b8 feat(argus): establish phase 7b frontend integration baseline`
- **Safety Backup Branch:** `backup/argus-part2-before-stabilization` (Untouched at `923dab7`)
- **Main Branch:** `main` (Untouched at `923dab7`)

## 3. Backend Contracts Inspected

Inspected actual Phase 6D FastAPI routes and Pydantic schemas in `src/backend/api/endpoints/`, `src/backend/schemas/schemas.py`, and `src/backend/core/security.py`:
- `GET /api/v1/health`
- `GET /api/v1/model-version`
- `POST /api/v1/events/vitals`
- `POST /api/v1/patients`
- `GET /api/v1/patients/{patient_id}`
- `GET /api/v1/patients/{patient_id}/vitals`
- `GET /api/v1/patients/{patient_id}/trajectory`
- `GET /api/v1/patients/{patient_id}/risk`
- `GET /api/v1/patients/{patient_id}/explanation`
- `GET /api/v1/patients/{patient_id}/alerts`

## 4. REST Client Architecture

Created centralized REST API client in `src/frontend/src/services/api.ts`:
- **Centralized Base URL:** Environment configurable via `import.meta.env.VITE_API_BASE_URL`, defaulting to `http://localhost:8000/api/v1`.
- **Typed Requests & Responses:** All methods return strictly typed TypeScript interfaces defined in `src/frontend/src/types/index.ts`.
- **Error Handling:** Formats errors into structured `ApiError` objects containing HTTP status code, detailed backend error messages, and `isAuthError` flags.

## 5. Authentication Handling

- Phase 6D protects patient endpoints using OAuth2 Bearer token authentication (`get_current_user` dependency in `src/backend/core/security.py`).
- Integrated token handling using default development token `fake-super-secret-token` in `Authorization: Bearer <token>` header.
- Distinguishes 401/403 authentication failures clearly from 404 / empty data states without exposing secrets or bypassing backend security.

## 6. API Endpoints Integrated

1. `/api/v1/health` — System status & database health
2. `/api/v1/model-version` — Active ML model version (`logistic-regression-v1`) & horizon metadata
3. `/api/v1/events/vitals` — Vital telemetry ingestion & live risk prediction
4. `/api/v1/patients` — Patient profile creation
5. `/api/v1/patients/{id}` — Patient profile retrieval
6. `/api/v1/patients/{id}/vitals` — Vital telemetry history retrieval
7. `/api/v1/patients/{id}/trajectory` — 24-hour deterioration risk trajectory points
8. `/api/v1/patients/{id}/risk` — Sepsis risk score & risk level calculation
9. `/api/v1/patients/{id}/explanation` — Real SHAP feature attribution dictionary
10. `/api/v1/patients/{id}/alerts` — Active clinical alerts emitted by SmartAlertEngine

## 7. Pages Integrated

- **`Dashboard.tsx`:** Consumes real REST APIs for patient roster, recent alerts, system health status, and active model version.
- **`PatientsPage.tsx`:** Retrieves patient roster directory, current vitals, and risk scores from backend REST endpoints with client-side search/filter.
- **`PatientDetailsPage.tsx`:** Fetches patient profile, current 6-vital grid, risk assessment, risk trajectory chart, real SHAP feature explainability, uncertainty status, and active alerts concurrently via REST API.
- **`AlertsPage.tsx`:** Retrieves active alerts from SmartAlertEngine across monitored ICU patients via REST API with severity filtering (`RED_URGENT`, `ORANGE_REVIEW`, `YELLOW_WATCH`).

## 8. Components Updated

- `App.tsx` & `AppShell.tsx`: System status & model version header tied to `/health` and `/model-version`.
- `ConnectionStatus.tsx`: Displays REST backend connectivity (`Connected` / `Disconnected`) and active model version (`logistic-regression-v1`).
- `RiskAnalysisCard.tsx`: Displays backend risk probability directly (e.g. `82.0%`).
- `ShapExplainabilityCard.tsx`: Renders real SHAP feature attributions in log-odds space with mandatory disclaimer.
- `UncertaintyCard.tsx`: Displays explicit `UNAVAILABLE` status returned by backend baseline.
- `FeedbackStates.tsx`: Renders loading spinners, error alerts with retry handlers, and empty state cards.

## 9. Mock Data Removed

- Integrated pages (`Dashboard.tsx`, `PatientsPage.tsx`, `PatientDetailsPage.tsx`, `AlertsPage.tsx`) no longer depend on isolated mock data for clinical telemetry.
- `src/frontend/src/mocks/mockData.ts` is preserved temporarily for fallback component type references and static data quality structures. It cannot be completely deleted yet until Phase 7C WebSocket integration, but its clinical datasets are no longer active on integrated screens.

## 10. Loading / Empty / Error Handling

- **Loading:** Renders `LoadingState` spinner during REST HTTP requests.
- **Error:** Renders `ErrorState` card with HTTP status, error detail, and retry button (`RefreshCw`).
- **Empty:** Renders `EmptyState` card when no patient, vitals, trajectory, or alerts exist.

## 11. SHAP Integration

- Consumes real SHAP explanation output from `GET /api/v1/patients/{id}/explanation`.
- Renders top feature attributions, direction (risk increasing vs. risk decreasing), log-odds value, and bar magnitudes.
- Displays required disclaimer: `"SHAP values represent model contribution, not causation."`
- No SHAP calculations or pseudo-explanations are performed in the frontend.

## 12. Uncertainty Handling

- Phase 6D backend explicitly reports `uncertainty_available = false`.
- Frontend displays `Predictive Uncertainty Status: UNAVAILABLE` with backend reason: `"Conformal prediction / Monte Carlo dropout is deactivated in logistic-regression-v1 baseline."`
- Does NOT display confidence percentages, ranges, or fabricated ±0.20 heuristics.

## 13. Alert Integration

- Consumes alert lists from `GET /api/v1/patients/{id}/alerts` generated by SmartAlertEngine.
- Displays severities: `RED URGENT`, `ORANGE REVIEW`, `YELLOW WATCH`.
- No alert threshold, persistence, or escalation calculations exist in the frontend.

## 14. Model Version Integration

- Queries `GET /api/v1/model-version`.
- Dynamically displays `logistic-regression-v1` across header, settings, dashboard, and risk analysis components without hardcoding inside UI views.

## 15. Health Integration

- Queries `GET /api/v1/health`.
- Status header updates to `Connected` when healthy, or `Disconnected` / `Offline` when server is unreachable.

## 16. WebSocket Status

WebSocket integration was intentionally NOT implemented in Phase 7B. WebSocket status in `ConnectionStatus.tsx` remains `Offline` placeholder until Phase 7C.

## 17. Testing

- **Frontend Lint (`oxlint`):** PASS (0 errors, 4 minor effect warnings)
- **Frontend Build (`tsc -b && vite build`):** PASS (0 errors)
- **Frontend Client Unit Test (`node --experimental-strip-types src/services/api.test.ts`):** 3/3 passed
- **Backend Regression (`python -m pytest tests/`):** PASS — 177 passed / 0 failed / 0 blocked (including 167 original backend regression tests + 10 new REST integration contract tests in `test_frontend_rest_integration.py`).

## 18. Live REST Verification

Ran live FastAPI backend server (`src.backend.main:app` on port 8000) and verified end-to-end REST interactions via `scratch/verify_live_rest.py`:
1. `GET /health` -> 200 OK
2. `GET /model-version` -> 200 OK
3. `POST /events/vitals` -> 201 Created
4. `POST /patients` -> 200 OK
5. `GET /patients/P-ICU-001` -> 200 OK
6. `GET /patients/P-ICU-001/vitals` -> 200 OK
7. `GET /patients/P-ICU-001/risk` -> 200 OK
8. `GET /patients/P-ICU-001/explanation` -> 200 OK (Real SHAP)
9. `GET /patients/P-ICU-001/alerts` -> 200 OK (SmartAlertEngine)
10. `GET /patients/P-ICU-001` (Invalid Token) -> 401 Unauthorized (Auth Security Verification)
- **Result:** 10/10 PASS

## 19. Files Changed

- `src/frontend/src/App.tsx`
- `src/frontend/src/types/index.ts`
- `src/frontend/src/pages/Dashboard.tsx`
- `src/frontend/src/pages/PatientsPage.tsx`
- `src/frontend/src/pages/PatientDetailsPage.tsx`
- `src/frontend/src/pages/AlertsPage.tsx`

## 20. Files Created

- `src/frontend/src/services/api.ts`
- `src/frontend/src/services/api.test.ts`
- `tests/unit/test_frontend_rest_integration.py`
- `scratch/verify_live_rest.py`
- `docs/ARGUS_PART2_PHASE7B_REST_INTEGRATION_REPORT.md`

## 21. Issues / Blockers

- None. Backend contracts, schemas, security, and response structures matched frontend requirements smoothly.

## 22. Phase 7C Readiness

Phase 7B REST integration is fully validated and PASS. The codebase is 100% ready for Phase 7C WebSocket integration.
