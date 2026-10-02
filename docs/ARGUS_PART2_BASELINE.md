# ARGUS Part 2 Baseline

## Purpose
This document records the exact baseline state of ARGUS Part 2 before any stabilization, bug fixes, refactoring, or feature development work begins. It serves as an official reference and safety checkpoint.

## Current Branch
- **Original Branch:** `main`
- **Active Working Branch:** `backup/argus-part2-before-stabilization`

## Baseline Commit
- **Commit Hash (Full):** `923dab718b6c3529099d42b160e6f0e60e275c19`
- **Commit Hash (Short):** `923dab7`
- **Commit Message:** `Add SepsisGuard AI technical documentation and prototypes`

## Baseline Tag
- **Tag Name:** `argus-part2-baseline-before-stabilization`

## Backup Branch
- **Backup Branch Name:** `backup/argus-part2-before-stabilization`

## Working Tree Status
- **Status:** Clean (`nothing to commit, working tree clean`)
- **Uncommitted Changes:** None present at baseline snapshot.

## Important Existing Components
The following major components were discovered in the project structure:

- **Backend Application (`src/backend`, `deployment/backend`)**:
  - FastAPI application entrypoint (`src/backend/main.py`, `deployment/backend/app/main.py`)
  - API Routes & Endpoints (`/health`, `/patients`, patient monitoring REST & WebSocket endpoints)
  - Core configuration, logging, security, patient service, alert engine, and inference service integration.
- **Frontend Interface (`src/frontend`, `deployment/frontend`)**:
  - React + Vite web frontend UI application with TypeScript support (`App.tsx`, `main.tsx`, styling and SVG assets).
- **ML Models & Artifacts (`model/`, `src/pipeline/`)**:
  - Tabular models (`lgb_model.txt`, `xgb_model.json`, `lr_model.pkl`) and corresponding probability calibrators (`.pkl`).
  - Temporal PyTorch models (`gru_temporal.pt`, `lstm_temporal.pt`, `tcn_temporal.pt`).
  - Evaluation & training pipeline scripts (`05_train_models.py` through `11_smart_alert_engine.py`).
  - Scaler (`scaler.pkl`) and decision matrix configurations (`model_selection_decision.json`, `temporal_model_selection.json`).
- **Database Schema (`deployment/database/schema.sql`)**:
  - PostgreSQL schema definitions for clinical data, physiological signals, patient records, and alert triggers.
- **WebSocket & Realtime Event Broker (`deployment/backend/app/services/event_broker.py`, WebSocket handlers)**:
  - Real-time patient data stream delivery and alerting broadcast channel.
- **Patient Simulator (`src/simulator/simulator.py`)**:
  - Clinical data stream simulation script for real-time inference testing.
- **Inference Service (`src/inference/main.py`)**:
  - Standalone model inference engine container service.
- **Tests (`tests/`)**:
  - Test suites covering unit (`tests/unit`), integration (`tests/integration`), model (`tests/model`), safety (`tests/safety`), and system (`tests/system`) tests.
- **Deployment & Containerization (`docker-compose.yml`, `deployment/docker-compose.yml`, Dockerfiles)**:
  - Multi-container Docker setup for backend, frontend, database, and inference services.
- **Clinical Data & Documentation (`docs/`, `data/`)**:
  - Sample MIMIC-IV clinical dataset demo (`data/raw/mimic-iv-clinical-database-demo-2.2/`).
  - Comprehensive documentation suite covering architecture, data dictionaries, temporal labeling, security, MLOps, and safety reviews.

## Safety Note
This baseline must be strictly preserved. If stabilization or repair work introduces regression or unexpected breaking changes, this baseline branch and tag provide an immutable recovery point to restore the codebase to its exact original state.
