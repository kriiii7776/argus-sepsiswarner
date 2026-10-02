# ARGUS Part 2 — Phase 7A Frontend Foundation Report

## 1. Objective
Prepare the existing ARGUS frontend for Phase 7 backend integration by creating a modular, high-information-density UI foundation based on the approved ARGUS clinical design concept. This phase establishes the application shell, page routing structure, reusable components, TypeScript type contracts, isolated mock data layer, and responsive layouts without implementing live REST or WebSocket API calls.

---

## 2. Existing Frontend Audit
- **Framework:** React 19 (`react`, `react-dom`).
- **Build System:** Vite 8 (`vite`, `@vitejs/plugin-react`).
- **Language / Linter:** TypeScript 6 (`typescript`), Oxlint (`oxlint`).
- **Icon / Chart Libraries:** Lucide Icons (`lucide-react`), Recharts (`recharts`).
- **Pre-Existing State:** `src/frontend/` contained a static single-file prototype (`App.tsx`) with embedded inline CSS variables and hardcoded inline mock arrays.

---

## 3. Existing Architecture
- **Root Directory:** `src/frontend/`
- **Config Files:** `vite.config.ts`, `package.json`, `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`, `.oxlintrc.json`.
- **Source Directory:** `src/frontend/src/`

---

## 4. UI Architecture Implemented
Modular architecture created under `src/frontend/src/`:
```
src/frontend/src/
├── types/
│   └── index.ts                 # Canonical TypeScript contracts aligned with Phase 6D
├── mocks/
│   └── mockData.ts              # Isolated mock data layer for UI development
├── styles/
│   ├── variables.css            # Clinical design system CSS variables
│   └── index.css                # Layouts, card primitives, badges, scrollbars
├── components/
│   ├── layout/                  # AppShell, Sidebar, Header
│   ├── common/                  # Badge, StatCard, ConnectionStatus, FeedbackStates
│   ├── patients/                # PatientRosterTable
│   ├── vitals/                  # VitalCard
│   ├── risk/                    # RiskBadge, RiskTrajectoryChart, RiskAnalysisCard
│   ├── explainability/          # ShapExplainabilityCard, UncertaintyCard
│   ├── data-quality/            # DataQualityCard
│   ├── alerts/                  # AlertBadge, AlertCard
│   └── charts/                  # VitalTrendCharts
├── pages/
│   ├── Dashboard.tsx            # ICU Overview & Patient Roster
│   ├── PatientsPage.tsx         # Patient Directory & Filtering
│   ├── PatientDetailsPage.tsx   # Patient Intensive Focus & Explainability
│   └── AlertsPage.tsx           # Clinical Alert Center
├── App.tsx                      # Page router & layout orchestration
└── main.tsx                     # React application entrypoint
```

---

## 5. Pages Implemented
1. **Dashboard (`Dashboard.tsx`):** ICU Overview metrics (Total ICU Bed Roster, Critical Risk Count, Warning Patients, Active Alerts), Patient Monitoring Table, Recent Urgent Alerts feed, Data Quality overview.
2. **Patients (`PatientsPage.tsx`):** Patient directory with real-time search, risk severity filter tabs (`ALL`, `CRITICAL`, `WARNING`, `STABLE`), and full ICU Patient Roster Table.
3. **Patient Details (`PatientDetailsPage.tsx`):** Patient Header banner with SIRS/qSOFA/NEWS scores, Risk Analysis card, 6-Vital Cards grid, 24h Deterioration Trajectory area chart (with 80% critical threshold), 31-Feature SHAP Explainability card, Explicit Uncertainty status card (`UNAVAILABLE`), 24h Vital Trend charts, and Patient Active Alerts history.
4. **Alerts (`AlertsPage.tsx`):** Alert Level summary banner (`RED URGENT`, `ORANGE REVIEW`, `YELLOW WATCH`), severity filter tabs, detailed Alert Cards with recommended clinical actions and patient focus links.

---

## 6. Components Implemented
- **Layout:** `AppShell`, `Sidebar` (dark clinical sidebar with bottom connection status indicator), `Header` (sticky header with search bar, model badge, notifications).
- **Common:** `Badge`, `RiskBadge`, `AlertBadge`, `SignalQualityBadge`, `StatCard`, `ConnectionStatus`, `EmptyState`, `LoadingState`, `ErrorState`.
- **Domain:** `VitalCard`, `RiskAnalysisCard`, `RiskTrajectoryChart`, `ShapExplainabilityCard`, `UncertaintyCard`, `DataQualityCard`, `PatientRosterTable`, `AlertCard`, `VitalTrendCharts`.

---

## 7. Type Definitions
- Defined in `src/frontend/src/types/index.ts`.
- Strictly mirrors Phase 6D backend contracts:
  - `Patient` (`patient_id`, `name`, `bed`, `age`, `sirs_score`, `qsofa_score`, `news_score`, `current_risk_score`, `risk_level`, `risk_trend`, `alert_severity`).
  - `VitalEvent` (`patient_id`, `timestamp`, `heart_rate`, `map`, `resp_rate`, `spo2`, `temperature_c`, `lactate`, `signal_quality`).
  - `PredictionResponse` (`model_version: "logistic-regression-v1"`, `is_demo_model: false`, `risk_probability`, `shap_explanation`, `uncertainty_summary`).
  - `ShapExplanation` (`explanation_available`, `base_value`, `feature_attributions: Array<{ feature_name, feature_value, shap_value, description }>`).
  - `UncertaintySummary` (`uncertainty_available: false`, `method: "UNAVAILABLE"`, `reason`).
  - `AlertItem` (`alert_id`, `patient_id`, `severity`, `message`, `recommended_action`, `timestamp`, `status`).
  - `ConnectionStatus` (`backend_connected`, `websocket_connected`, `database_status`, `active_model`).

---

## 8. Responsive Design
- **Desktop (1440px+):** 12-column grid layout, multi-card density, side-by-side charts and explainability panels.
- **Tablet / Small Screen (768px - 1024px):** Sidebar collapses to compact icon bar, 6-column grid stacks, patient tables retain horizontal scroll.
- **Mobile (<768px):** Grid columns collapse to full width (12-column span), vertical stacking for vital cards and alert feeds.

---

## 9. Mock Data Strategy
- All mock data is strictly isolated in [`src/frontend/src/mocks/mockData.ts`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/mocks/mockData.ts).
- Marked explicitly: `// PHASE 7A UI MOCK DATA - Will be replaced by backend integration in Phase 7B/7C.`
- Zero hardcoded mock values embedded inside reusable component logic.

---

## 10. Backend Integration Status
Backend REST and WebSocket integration were intentionally NOT implemented in Phase 7A. UI components consume isolated mock data structures that reflect Phase 6D backend contracts.

---

## 11. Validation
- **Dependencies:** `npm install` added packages successfully with 0 vulnerabilities.
- **Linter (`npm run lint`):** `oxlint` executed on 25 files with 0 warnings and 0 errors.
- **Type Check & Build (`npm run build`):** `tsc -b && vite build` completed cleanly with exit code 0 (`dist/` generated successfully).
- **Backend Regression Suite (`python -m pytest tests/`):** 167/167 tests passed, 0 failed, 0 blocked.

---

## 12. Files Changed
- [`src/frontend/package.json`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/package.json)
- [`src/frontend/src/App.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/App.tsx)
- [`src/frontend/src/index.css`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/index.css)

---

## 13. Files Created
- [`src/frontend/src/types/index.ts`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/types/index.ts)
- [`src/frontend/src/mocks/mockData.ts`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/mocks/mockData.ts)
- [`src/frontend/src/styles/variables.css`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/styles/variables.css)
- [`src/frontend/src/components/common/Badge.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/common/Badge.tsx)
- [`src/frontend/src/components/common/StatCard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/common/StatCard.tsx)
- [`src/frontend/src/components/common/ConnectionStatus.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/common/ConnectionStatus.tsx)
- [`src/frontend/src/components/common/FeedbackStates.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/common/FeedbackStates.tsx)
- [`src/frontend/src/components/layout/Sidebar.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/layout/Sidebar.tsx)
- [`src/frontend/src/components/layout/Header.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/layout/Header.tsx)
- [`src/frontend/src/components/layout/AppShell.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/layout/AppShell.tsx)
- [`src/frontend/src/components/vitals/VitalCard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/vitals/VitalCard.tsx)
- [`src/frontend/src/components/risk/RiskTrajectoryChart.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/risk/RiskTrajectoryChart.tsx)
- [`src/frontend/src/components/risk/RiskAnalysisCard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/risk/RiskAnalysisCard.tsx)
- [`src/frontend/src/components/explainability/ShapExplainabilityCard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/explainability/ShapExplainabilityCard.tsx)
- [`src/frontend/src/components/explainability/UncertaintyCard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/explainability/UncertaintyCard.tsx)
- [`src/frontend/src/components/data-quality/DataQualityCard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/data-quality/DataQualityCard.tsx)
- [`src/frontend/src/components/patients/PatientRosterTable.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/patients/PatientRosterTable.tsx)
- [`src/frontend/src/components/alerts/AlertCard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/alerts/AlertCard.tsx)
- [`src/frontend/src/components/charts/VitalTrendCharts.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/components/charts/VitalTrendCharts.tsx)
- [`src/frontend/src/pages/Dashboard.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/pages/Dashboard.tsx)
- [`src/frontend/src/pages/PatientsPage.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/pages/PatientsPage.tsx)
- [`src/frontend/src/pages/PatientDetailsPage.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/pages/PatientDetailsPage.tsx)
- [`src/frontend/src/pages/AlertsPage.tsx`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/src/frontend/src/pages/AlertsPage.tsx)
- [`docs/ARGUS_PART2_PHASE7A_FRONTEND_FOUNDATION_REPORT.md`](file:///c:/Users/HP/Desktop/Argus/argus-sepsiswarner/docs/ARGUS_PART2_PHASE7A_FRONTEND_FOUNDATION_REPORT.md)

---

## 14. Issues / Blockers
None.

---

## 15. Phase 7B Readiness
The frontend foundation has been validated. Type definitions, isolated mock data, page routing, and reusable components are complete and ready for Phase 7B REST API integration.
