# ARGUS — AI-Powered Sepsis Early Warning System

> **See the dangerous trend before the patient reaches the crisis point.**

**Problem Statement ID:** 12  
**Project Name:** ARGUS  
**Domain:** Artificial Intelligence • Healthcare • Clinical Decision Support • Explainable AI  
**Primary Use Case:** Early warning of sepsis-related patient deterioration in ICU environments

---

# 📌 Overview

**ARGUS** is an AI-powered, explainable early warning platform designed to continuously analyse ICU patient vital signs and clinical information to identify dangerous physiological trends before they become critical.

Instead of depending only on individual abnormal values or fixed thresholds, ARGUS analyses **multiple physiological parameters over time** to identify changing patient conditions.

The system continuously processes:

- Heart Rate
- Systolic Blood Pressure
- Diastolic Blood Pressure
- SpO₂
- Temperature
- Respiratory Rate
- Platelets
- Bilirubin
- Creatinine
- Lactate
- PaO₂/FiO₂
- Glasgow Coma Scale
- Urine Output
- Norepinephrine
- Derived temporal features

The processed information is passed through an AI risk prediction pipeline.

ARGUS then:

```text
Collect
   ↓
Process
   ↓
Analyse Trends
   ↓
Generate Features
   ↓
Predict Risk
   ↓
Explain Prediction
   ↓
Prioritize Alert
   ↓
Notify Clinical Staff
```

ARGUS is designed as a **clinical decision-support prototype** and is not intended to replace doctors or nurses.

---

# 🎯 Problem Statement

## AI-Powered Sepsis Early Warning System

Sepsis is a time-critical clinical condition where delayed recognition can lead to severe complications.

In an ICU, a patient's condition can change continuously. A dangerous condition may develop through a combination of small changes across multiple physiological parameters rather than one single abnormal measurement.

For example, a patient may show:

```text
Heart Rate        75  → 138
Temperature     37.0 → 38.2 °C
Blood Pressure 118/74 → 78/48
Respiratory Rate  16 → 26
SpO₂              98 → 92
```

Looking at individual values alone may not provide enough context.

ARGUS therefore focuses on the **trajectory and combination of changes over time**.

### The Challenge

Traditional monitoring approaches may depend heavily on:

- Static thresholds
- Individual measurements
- Manual observation
- Large numbers of alarms
- Delayed recognition of combined physiological changes

This can contribute to **alarm fatigue** and make it harder for clinical teams to identify the most important warnings quickly.

---

# 💡 Our Idea

ARGUS introduces an **AI-powered, trend-based and explainable early warning layer** between patient monitoring data and clinical decision-making.

Instead of asking only:

> "Is this vital sign above a fixed threshold?"

ARGUS asks:

> **"How is the patient's condition changing over time, and what combination of changes is increasing the risk?"**

The system continuously evaluates a rolling temporal window and generates:

1. Patient risk score
2. Risk confidence information
3. Contributing factors
4. Risk trajectory
5. Prioritized alert
6. Clinical context

---

# 🚀 What Makes ARGUS Different?

ARGUS combines multiple capabilities into one real-time platform.

## 1. Trend Intelligence

ARGUS analyses how physiological parameters change over time rather than relying only on isolated measurements.

## 2. Multi-Parameter Analysis

Multiple physiological and clinical parameters are analysed together.

## 3. Explainable AI

ARGUS uses **SHAP-based explanations** to identify the features contributing to the model prediction.

## 4. Smart Alerting

Risk scores are converted into prioritized alerts instead of treating every abnormal measurement as an emergency.

## 5. Real-Time Architecture

ARGUS uses WebSockets for continuous telemetry and risk updates.

## 6. Clinical Data Replay

MIMIC-IV Demo data can be replayed through the system to demonstrate realistic ICU data processing.

## 7. Desktop + Mobile Monitoring

ARGUS provides:

- Web-based clinical dashboard
- Android mobile application

## 8. Role-Based Access

The application supports different roles such as:

- Admin
- Doctor
- Nurse

---

# 🧠 Core Concept

The ARGUS pipeline can be represented as:

```text
                    ICU Patient
                         │
                         ▼
              ┌─────────────────────┐
              │ Patient Monitoring  │
              │ Vital + Clinical    │
              │ Data                │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ ARGUS Part 1        │
              │ Replay & Simulation │
              └──────────┬──────────┘
                         │
                         │ WebSocket
                         ▼
              ┌─────────────────────┐
              │ Integration Bridge  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Feature Engineering │
              │ 31 Features         │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ AI Risk Engine      │
              │ Logistic Regression │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Probability         │
              │ Calibration         │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ SHAP Explainability │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Smart Alert Engine  │
              └──────────┬──────────┘
                         │
                  ┌──────┴───────┐
                  ▼              ▼
           Desktop Dashboard   Mobile App
```

---

# 🏗️ System Architecture

ARGUS is organised into multiple logical layers.

## Layer 1 — Data Source

ARGUS can process:

- MIMIC-IV Demo ICU data
- ARGUS simulation scenarios
- Real-time vital streams through the defined event contract

The current MIMIC-IV implementation uses:

**MIMIC-IV Clinical Database Demo v2.2**

---

## Layer 2 — ARGUS Part 1

Part 1 is responsible for simulation and clinical data replay.

### Responsibilities

- Patient registry
- Patient profiles
- Baseline generation
- Simulation clock
- Scenario engine
- Vital generation
- Sensor noise simulation
- MIMIC-IV replay
- Clinical/lab replay
- WebSocket streaming
- REST APIs
- Patient/session isolation

### Part 1 WebSocket

```text
ws://127.0.0.1:8001/api/v1/stream
```

---

# 📡 Data Streaming

ARGUS uses WebSockets to continuously transfer patient information.

A simplified telemetry message looks like:

```json
{
  "schema_version": "1.0",
  "message_type": "vital_update",
  "patient_id": "MIMIC-38197705",
  "session_id": "session-001",
  "source": "mimic_iv",
  "timestamp": "2116-12-03T12:13:00Z",
  "simulation_time": "2116-12-03T12:13:00Z",
  "vitals": {
    "heart_rate": 125,
    "systolic_bp": 84,
    "diastolic_bp": 43,
    "spo2": 96,
    "temperature": 37.94,
    "respiratory_rate": 21
  }
}
```

The architecture maintains patient and session identity so that data from different patients is not mixed.

---

# 🧬 MIMIC-IV Integration

ARGUS uses the **MIMIC-IV Clinical Database Demo v2.2** for realistic clinical replay.

The active replay data contains ICU information from:

```text
icustays.csv.gz
chartevents.csv.gz
labevents.csv.gz
inputevents.csv.gz
outputevents.csv.gz
```

Additional available clinical files include:

```text
microbiologyevents.csv.gz
prescriptions.csv.gz
d_items.csv.gz
```

The current replay implementation uses a curated set of **10 MIMIC-IV ICU stays**.

```text
MIMIC-38197705
MIMIC-34617352
MIMIC-32359580
MIMIC-31269608
MIMIC-37509585
MIMIC-32554129
MIMIC-31338022
MIMIC-30876334
MIMIC-35446858
MIMIC-36091287
```

---

# 🩺 Clinical Data Used

ARGUS extracts clinically relevant information from MIMIC-IV.

## Vital Signs

| Parameter                | MIMIC-IV Item ID  |
| ------------------------ | ----------------- |
| Heart Rate               | `220045`          |
| Systolic Blood Pressure  | `220179`          |
| Diastolic Blood Pressure | `220180`          |
| SpO₂                     | `220277`          |
| Respiratory Rate         | `220210`          |
| Temperature              | `223761 / 223762` |

## Laboratory / Clinical Variables

| Parameter      | MIMIC-IV Item ID                    |
| -------------- | ----------------------------------- |
| Platelets      | `51265`                             |
| Bilirubin      | `50885`                             |
| Creatinine     | `50912`                             |
| Lactate        | `50813`                             |
| PaO₂           | `50821`                             |
| FiO₂           | `223835`                            |
| GCS            | `220739 / 223900 / 223901`          |
| Norepinephrine | `221906`                            |
| Urine Output   | `226559 / 226566 / 226627 / 226631` |

---

# 🔄 MIMIC Replay Approach

ARGUS does not intentionally fabricate clinical values during MIMIC replay.

The replay mechanism retrieves the latest recorded clinical observation available at or before the virtual simulation time.

Conceptually:

```text
MIMIC-IV Historical Data
          │
          ▼
   Timestamp Sorting
          │
          ▼
   Virtual Simulation Clock
          │
          ▼
Latest Recorded Value
          │
          ▼
ARGUS Event Stream
```

Stale observations are handled through configured freshness rules.

---

# 🔗 Part 1 → Part 2 Integration

Part 1 and Part 2 communicate through a defined event boundary.

```text
Part 1
  │
  │ WebSocket
  ▼
Part 1 WebSocket Bridge
  │
  ▼
Vital / Clinical Event Adapter
  │
  ▼
Feature Engineering
  │
  ▼
AI Inference
```

The architecture avoids direct coupling between the two services.

Part 2 does not depend on:

- Part 1 internal Python modules
- Part 1 internal database objects
- Part 1 implementation-specific classes

Instead, the services communicate through defined event contracts.

---

# 🤖 AI / Machine Learning Pipeline

ARGUS uses a structured machine-learning pipeline.

```text
Raw Clinical Events
       │
       ▼
Timestamp Ordering
       │
       ▼
Temporal Windowing
       │
       ▼
Feature Engineering
       │
       ▼
31 Model Features
       │
       ▼
Standardization
       │
       ▼
Logistic Regression
       │
       ▼
Probability Calibration
       │
       ▼
Risk Score
       │
       ▼
SHAP Explanation
       │
       ▼
Smart Alert Engine
```

---

# 🧮 Temporal Feature Engineering

ARGUS does not treat every observation as an independent data point.

It uses timestamp-based windows to understand patient trends.

The feature pipeline considers:

- Current measurements
- Historical measurements
- Change over time
- Rate of change
- Physiological relationships
- Missing values
- Stale signals
- Temporal context

The runtime model uses **31 canonical features**.

Temporal inference is based on the clinical/simulation timestamp rather than accelerated wall-clock time.

---

# 🧠 Current AI Model

The active runtime model is:

```text
Model:
Logistic Regression

Model ID:
logistic-regression-v1
```

The inference pipeline is:

```text
Input Features
      │
      ▼
StandardScaler
      │
      ▼
Logistic Regression
      │
      ▼
Probability
      │
      ▼
Calibration
      │
      ▼
Final Risk Score
```

Logistic Regression provides a lightweight and stable prototype inference layer and is compatible with the current SHAP explainability implementation.

---

# 📊 Model Validation

A patient-disjoint evaluation was performed using:

```text
70% Training
15% Validation
15% Held-out Test
```

Validated Logistic Regression results:

| Metric           | Result |
| ---------------- | ------ |
| AUROC            | 0.9980 |
| AUPRC            | 0.9568 |
| Sensitivity      | 0.952  |
| Specificity      | 0.993  |
| PPV              | 0.822  |
| NPV              | 0.998  |
| Brier Score      | 0.0062 |
| False Alert Rate | ~0.7% |

### Important

These values represent **prototype/model validation results**.

They do **not** represent clinical validation or evidence that the system is ready for autonomous patient-care decisions.

---

# 🔍 Explainable AI with SHAP

A major design principle of ARGUS is:

> **The AI should not only predict risk. It should also explain the factors contributing to that prediction.**

ARGUS uses:

**SHAP — SHapley Additive exPlanations**

The explanation pipeline is:

```text
Patient Features
      │
      ▼
ML Model
      │
      ▼
Prediction
      │
      ▼
SHAP
      │
      ▼
Feature Contributions
```

Example:

```text
Risk Increasing Factors

↑ Heart Rate
↓ Systolic Blood Pressure
↑ Respiratory Rate
↑ Lactate
↓ PaO₂/FiO₂
```

The dashboard presents the important contributing features so users can understand the model output.

---

# 🚨 Smart Alert Engine

ARGUS converts model risk into prioritized alert levels.

| Alert     | Meaning |
| --------- | ------- |
| 🟡 Yellow | Watch   |
| 🟠 Orange | Review  |
| 🔴 Red    | Urgent  |

The prototype alert engine uses configurable thresholds and temporal rules.

It considers:

- AI risk
- Risk persistence
- Risk escalation
- Signal quality
- Missing values
- Stale values
- Confidence
- Previous alert state
- De-escalation
- Alert deduplication

This approach is designed to reduce unnecessary repeated alerts.

---

# 🔔 Alert Lifecycle

ARGUS supports an alert lifecycle:

```text
EMITTED
   ↓
DELIVERED
   ↓
VIEWED
   ↓
ACKNOWLEDGED
```

This helps track the state of an alert from generation to acknowledgement.

---

# 👨‍⚕️ Role-Based Access Control

ARGUS supports role-based application access.

Current roles include:

```text
ADMIN
DOCTOR
NURSE
```

The system applies access boundaries to:

- Patients
- Alerts
- Clinical information
- Staff assignments
- Administrative functionality

---

# 🖥️ Desktop Clinical Dashboard

ARGUS provides a real-time web dashboard.

## Dashboard

Provides:

- Patient overview
- Current risk
- Alert counts
- Live telemetry
- Risk status
- Event feed
- Data freshness

## Patient Focus

Provides:

- Current vitals
- Risk score
- Risk trajectory
- SHAP explanations
- Clinical/lab context
- Observation timestamps
- Data freshness

## Alert Center

Provides:

- Active alerts
- Alert priority
- Patient information
- Risk score
- Alert status
- Acknowledgement

## Analytics

Provides system-level monitoring and analysis.

## Settings

Provides application and notification preferences.

---

# 📱 Mobile Application

ARGUS also provides an Android application.

The mobile application supports:

- Authentication
- Staff context
- Assigned patient roster
- Live patient telemetry
- Risk information
- Alerts
- Alert acknowledgement
- Notification preferences
- Sound notifications
- Vibration notifications

The mobile application communicates with the ARGUS backend using REST APIs and WebSockets.

---

# 🔐 Security Architecture

Security is treated as a system-level requirement.

ARGUS includes:

- Bearer-token authentication
- Role-based access control
- Patient-level authorization
- Staff assignments
- Protected API endpoints
- WebSocket access boundaries
- Notification preferences
- Alert acknowledgement tracking

### Security Rule

Never hardcode:

```text
Passwords
JWT secrets
API keys
Database credentials
Private keys
Production credentials
```

Use environment variables instead.

---

# 🧪 Testing

ARGUS includes backend, frontend, mobile, integration and runtime validation.

Current validated baseline:

```text
Backend:
211 passed
1 skipped

Flutter:
31 passed

Frontend:
Build successful

Flutter:
Static analysis clean
```

Testing covers:

- API behaviour
- Authentication
- Patient isolation
- WebSocket communication
- Alert logic
- SHAP generation
- Database behaviour
- Clinical event handling
- MIMIC replay
- Part 1 → Part 2 integration
- Mobile authentication
- Mobile alert acknowledgement
- Runtime connectivity

---

# 🐳 Docker Architecture

ARGUS can run as a multi-service application.

```text
                    ARGUS SYSTEM
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
   Part 1             Part 2          PostgreSQL
   :8001               :8000             :5432
       │                 │
       │ WebSocket       │
       └───────►─────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        React Dashboard        Mobile App
```

Docker provides a reproducible environment for running the core services.

---

# 💻 Installation Guide

## Prerequisites

Install:

- Git
- Python 3.10+
- Node.js 18+
- npm
- Docker Desktop
- Flutter SDK
- Android Studio

Recommended:

```text
Git
Python
Node.js
npm
Docker Desktop
Flutter
Android Studio
```

---

# 📥 Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ARGUS
```

Replace:

```text
<YOUR_GITHUB_REPOSITORY_URL>
```

with the actual GitHub repository URL.

---

# 🐍 Backend Installation

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ⚙️ Environment Configuration

Create your environment configuration based on the project's environment template.

Example:

```env
DATABASE_URL=sqlite:///./sepsisguard.db
JWT_SECRET=<CHANGE_THIS_SECRET>
```

For PostgreSQL:

```env
DATABASE_URL=postgresql://<USER>:<PASSWORD>@<HOST>:5432/<DATABASE>
JWT_SECRET=<CHANGE_THIS_SECRET>
```

### Never commit secrets

Do not commit:

```text
.env
API keys
JWT secrets
Database passwords
Private keys
Production credentials
```

---

# ▶️ Run the Backend

From the repository root:

```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

API base:

```text
/api/v1
```

---

# 🔌 Run ARGUS Part 1

Part 1 runs the simulator and MIMIC-IV replay engine.

Default service port:

```text
8001
```

WebSocket:

```text
ws://127.0.0.1:8001/api/v1/stream
```

Make sure Part 1 is running before testing the complete real-time pipeline.

---

# 🌐 Frontend Installation

Navigate to the frontend directory:

```bash
cd src/frontend
```

Install dependencies:

```bash
npm install
```

Run development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 📱 Mobile Installation

Check Flutter:

```bash
flutter doctor
```

Navigate to the mobile directory:

```bash
cd mobile
```

Install dependencies:

```bash
flutter pub get
```

Run analysis:

```bash
flutter analyze
```

Run tests:

```bash
flutter test
```

Run the application:

```bash
flutter run
```

For a physical Android device:

- Enable USB debugging.
- Connect the device.
- Verify the device using ADB.
- Configure the backend URL correctly.
- Ensure the device can reach the backend machine.

### Important

Do not use:

```text
localhost
```

from a physical Android device to access a backend running on your development computer.

---

# 🐳 Docker Installation

Make sure Docker Desktop is running.

From the repository root:

```bash
docker compose up --build
```

For detached mode:

```bash
docker compose up -d --build
```

Check services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Stop the system:

```bash
docker compose down
```

---

# 🔄 Complete Runtime Flow

Once all services are running:

```text
MIMIC-IV / Simulator
        │
        ▼
ARGUS Part 1
        │
        │ WebSocket
        ▼
Part 1 WebSocket Bridge
        │
        ▼
Clinical + Vital Event Adapter
        │
        ▼
Timestamp-Based Windowing
        │
        ▼
31 Feature Vector
        │
        ▼
StandardScaler
        │
        ▼
Logistic Regression
        │
        ▼
Probability Calibration
        │
        ▼
Risk Score
        │
        ├─────────────────┐
        ▼                 ▼
      SHAP           Alert Engine
        │                 │
        └────────┬────────┘
                 ▼
              Database
                 │
        ┌────────┴────────┐
        ▼                 ▼
      REST             WebSocket
        │                 │
        ▼                 ▼
Desktop Dashboard     Live Updates
        │
        ▼
Mobile Application
```

---

# 🔬 Example MIMIC Replay

A MIMIC-IV patient such as:

```text
MIMIC-38197705
```

can be replayed through the ARGUS pipeline.

Conceptually:

```text
MIMIC-38197705
      │
      ▼
Historical ICU Events
      │
      ▼
Virtual Timeline
      │
      ▼
Vital Events
+
Clinical Events
      │
      ▼
ARGUS Feature Pipeline
      │
      ▼
Risk Prediction
      │
      ▼
SHAP Explanation
      │
      ▼
Alert
```

---

# 📂 Project Structure

```text
ARGUS/
│
├── part1/
│   ├── data/
│   │   └── mimic-iv-demo/
│   ├── ...
│   └── ...
│
├── src/
│   │
│   ├── backend/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── ml/
│   │   └── ...
│   │
│   └── frontend/
│       ├── src/
│       ├── public/
│       ├── package.json
│       └── ...
│
├── mobile/
│   ├── lib/
│   ├── test/
│   └── ...
│
├── model/
│   ├── lr_model.pkl
│   └── lr_calibrator.pkl
│
├── tests/
│
├── docs/
│
├── docker-compose.yml
├── requirements.txt
├── README.md
└── ...
```

---

# 📚 Main Components

| Component        | Responsibility                          |
| ---------------- | --------------------------------------- |
| Part 1           | Simulation and MIMIC-IV replay          |
| WebSocket Bridge | Part 1 → Part 2 communication           |
| Feature Engine   | Temporal clinical feature generation    |
| ML Engine        | Risk prediction                         |
| Calibration      | Probability calibration                 |
| SHAP             | Explainability                          |
| SmartAlertEngine | Alert prioritization                    |
| Database         | Event, prediction and alert persistence |
| FastAPI          | Backend APIs                            |
| WebSocket        | Real-time communication                 |
| React            | Desktop dashboard                       |
| Flutter          | Mobile application                      |
| Authentication   | Identity and access control             |

---

# 🧪 Prototype Scenarios

ARGUS supports simulation scenarios for system validation.

Examples include:

```text
Stable
Deterioration
Recovery
Noisy / Sensor Fault
```

These scenarios are intended for **software and pipeline testing**.

They should not be interpreted as real clinical patient outcomes.

---

# 📈 Evaluation Strategy

ARGUS evaluates the system at multiple levels.

## Model-Level Evaluation

Important metrics include:

- AUROC
- AUPRC
- Sensitivity
- Specificity
- PPV
- NPV
- Brier Score
- False Alert Rate

## System-Level Evaluation

The platform also evaluates:

- WebSocket latency
- API response time
- Data freshness
- Patient isolation
- Alert delivery
- Alert acknowledgement
- Database persistence
- Service restart behaviour
- Mobile connectivity
- End-to-end event propagation

---

# ⚡ Performance and Reliability

ARGUS is designed around continuous event processing.

## Parallel Data Loading

Patient details are retrieved using parallel requests instead of a long serial network waterfall.

## Timestamp-Based State Merging

Live telemetry is merged using timestamps so that an older REST response does not overwrite newer WebSocket information.

## Data Freshness

The UI distinguishes between:

```text
LIVE
STALE
UNAVAILABLE
```

rather than assuming that an open WebSocket connection automatically means the data is current.

## WebSocket Streaming

Continuous telemetry avoids repeatedly polling for every vital update.

---

# 🛡️ Clinical Safety and Scope

ARGUS is a **research and prototype clinical decision-support system**.

It is **not a medical device** and is not intended to independently diagnose, treat or manage patients.

ARGUS should not replace:

- Doctors
- Nurses
- Clinical judgement
- Hospital protocols
- Laboratory confirmation
- Sepsis assessment
- Emergency medical intervention

AI predictions must always be interpreted within the appropriate clinical context.

---

# ⚠️ Current Limitations

ARGUS is currently a prototype and has important limitations.

## 1. Clinical Validation

The model has not undergone prospective clinical validation.

## 2. Multi-Hospital Validation

The current validation does not establish generalisation across multiple hospitals.

## 3. MIMIC-IV Demo Dataset

The current implementation uses the MIMIC-IV Demo dataset and a curated set of ICU stays.

This does not represent every possible ICU population.

## 4. Prototype Alert Thresholds

Current alert thresholds are engineering/prototype parameters and require clinical validation.

## 5. Model Scope

The current runtime uses a tabular temporal feature pipeline and Logistic Regression.

## 6. Uncertainty Estimation

Advanced uncertainty estimation is not currently presented as clinically validated uncertainty.

## 7. Healthcare Interoperability

Full production HL7/FHIR integration remains future work.

---

# 🔮 Future Scope

ARGUS can be extended into a larger clinical decision-support platform.

## 1. Multi-Hospital Validation

Evaluate the system using larger and more diverse hospital datasets.

## 2. Patient-Specific Baselines

Future versions can combine population-level patterns with individual patient baselines.

```text
Population Pattern
        +
Individual Baseline
        ↓
Personalized Risk
```

## 3. Multimodal Clinical AI

Future versions can combine:

```text
Vital Signs
+
Laboratory Data
+
Clinical Notes
+
Medication Information
+
Patient History
```

## 4. HL7 / FHIR Integration

ARGUS can be extended to communicate with hospital systems using healthcare interoperability standards.

## 5. EHR Integration

Future versions can connect with Electronic Health Record systems to provide richer clinical context.

## 6. Federated Learning

Federated learning can be explored to improve models across institutions while reducing the need to centralize sensitive patient data.

## 7. Advanced AI Models

Future research can evaluate:

- Gradient Boosting
- Temporal Neural Networks
- Transformer-based models
- Time-series models
- Multimodal clinical models

Any future model should undergo appropriate patient-disjoint and clinically relevant validation.

---

# 🧭 Development Roadmap

```text
                    ARGUS ROADMAP

             ┌─────────────────────┐
             │ Current Prototype   │
             │                     │
             │ Real-time Pipeline  │
             │ AI Risk             │
             │ SHAP                │
             │ Smart Alerts        │
             │ Desktop + Mobile    │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ Validation          │
             │                     │
             │ Larger datasets     │
             │ Multi-hospital      │
             │ External validation │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ Integration         │
             │                     │
             │ EHR                 │
             │ HL7/FHIR            │
             │ Hospital Systems    │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ Advanced Platform   │
             │                     │
             │ Personalised AI     │
             │ Multimodal AI       │
             │ Federated Learning  │
             └─────────────────────┘
```

---

# 👥 Intended Users

## ICU Nurses

ARGUS can support:

- Continuous patient monitoring
- Prioritized alerts
- Patient trend visibility
- Rapid review

## Doctors

ARGUS can support:

- Patient trajectory analysis
- Risk review
- Explainable AI insights
- Alert acknowledgement

## Hospital Teams

ARGUS can support:

- Patient monitoring
- Alert management
- System analytics
- Clinical AI research

## Researchers

ARGUS provides a platform for:

- Clinical AI experimentation
- MIMIC-IV replay
- Model evaluation
- Explainability research
- Real-time healthcare AI architecture

---

# 🧰 Technology Stack

## AI / Machine Learning

```text
Python
Pandas
NumPy
Scikit-learn
SHAP
```

## Backend

```text
FastAPI
Python
WebSockets
SQLAlchemy
```

## Frontend

```text
React
TypeScript
Vite
Recharts
Lucide
```

## Mobile

```text
Flutter
Dart
Android
```

## Database

```text
SQLite
PostgreSQL
```

## Infrastructure

```text
Docker
Docker Compose
Git
```

## Dataset

```text
MIMIC-IV Clinical Database Demo v2.2
```

---

# 📡 API Overview

The backend follows a versioned API structure.

Base path:

```text
/api/v1
```

Major API categories include:

```text
Authentication
Patients
Vitals
Risk
Alerts
Clinical Context
Analytics
Administration
Notifications
WebSocket Streaming
```

The exact endpoint definitions should be treated as implementation contracts in the backend source code.

---

# 🔌 WebSocket Overview

## Part 1

```text
ws://127.0.0.1:8001/api/v1/stream
```

## Part 2

```text
ws://127.0.0.1:8000/api/v1/ws/stream
```

WebSockets are used for:

- Live vitals
- Risk updates
- Alerts
- Patient state
- Real-time dashboard updates

---

# 🧩 Engineering Design Principles

ARGUS follows several important engineering principles.

## Separation of Services

Part 1 and Part 2 communicate through defined contracts.

## Patient Isolation

Every patient event is associated with patient identity and session context.

## Timestamp Correctness

Clinical/simulation time is more important than accelerated wall-clock time.

## Explainability

Predictions should be accompanied by understandable feature contributions.

## Fault Awareness

Missing, stale and invalid signals are handled explicitly.

## Alert Deduplication

Repeated identical alerts should not continuously disturb users.

## Human-in-the-Loop

AI provides decision support rather than autonomous clinical decisions.

---

# 🧪 Running Tests

## Backend

Run:

```bash
pytest
```

Validated baseline:

```text
211 passed
1 skipped
```

## Frontend

Build:

```bash
npm run build
```

## Mobile

Analyse:

```bash
flutter analyze
```

Run tests:

```bash
flutter test
```

Validated baseline:

```text
31 tests passed
```

---

# 🛠️ Troubleshooting

## Backend Is Not Reachable

Check:

```text
http://127.0.0.1:8000
```

Make sure the backend service is running.

## Part 1 Stream Is Unavailable

Check:

```text
ws://127.0.0.1:8001/api/v1/stream
```

Verify that Part 1 is running.

## Frontend Shows Stale Data

Check:

1. Backend status
2. Part 1 WebSocket
3. Part 2 WebSocket
4. Browser console
5. Patient telemetry timestamp
6. Network connectivity

## Mobile Cannot Connect

Check:

- Backend IP address
- Mobile device network
- Firewall
- API URL configuration
- WebSocket URL
- Android permissions
- ADB connectivity

For a physical Android device, do not use `localhost` to access the backend running on your development machine.

---

# 📖 Research Direction

ARGUS combines:

```text
Healthcare AI
      +
Time-Series Analysis
      +
Machine Learning
      +
Explainable AI
      +
Real-Time Systems
      +
Clinical Decision Support
      +
Mobile Computing
      +
Secure Software Architecture
```

This creates a foundation for further research into explainable clinical early-warning systems.

---

# 🌟 Key Takeaway

Traditional monitoring asks:

> **"Is this value abnormal?"**

ARGUS aims to ask:

> **"Is the patient's condition changing in a dangerous direction, what factors are driving that risk, and how should the warning be prioritized?"**

The core philosophy is:

```text
OBSERVE
   ↓
UNDERSTAND
   ↓
PREDICT
   ↓
EXPLAIN
   ↓
PRIORITIZE
   ↓
ALERT
   ↓
CLINICAL REVIEW
```

---

# 👨‍💻 Team

## Team Gambheera

Developed as a collaborative healthcare AI project.

### Team Members

- **Gokul R**
- **Anu Shri SG**
- **Kishore ES**
- **Krithika V**

### Institution

**SNS College of Technology**

---

# 📜 Disclaimer

ARGUS is an academic/research prototype for demonstrating AI-powered early warning and clinical decision-support concepts.

It has **not been clinically validated or approved for autonomous diagnosis, treatment, or patient management**.

Real-world deployment would require:

- Clinical validation
- Regulatory review
- Hospital integration
- Security assessment
- Data governance
- Prospective evaluation
- Clinical workflow validation
- Appropriate medical-device compliance

---

# 📄 License

Add the project's selected open-source license here.

For example:

```text
MIT License
```

if the repository is intended to be released under the MIT License.

---

# ⭐ Project Summary

**ARGUS is an explainable AI-powered early warning platform that continuously analyses ICU patient trends, predicts deterioration risk, explains the factors behind the prediction, and delivers prioritized alerts through desktop and mobile interfaces.**

```text
MIMIC-IV / ICU DATA
        ↓
REAL-TIME STREAM
        ↓
TEMPORAL FEATURES
        ↓
AI RISK PREDICTION
        ↓
SHAP EXPLANATION
        ↓
SMART ALERT
        ↓
CLINICAL DASHBOARD
        ↓
MOBILE NOTIFICATION
```

---

## ARGUS

> **See the dangerous trend before the patient reaches the crisis point.**
>
> ```text
> ```
