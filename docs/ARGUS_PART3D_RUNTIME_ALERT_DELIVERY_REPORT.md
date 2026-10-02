# ARGUS PART 3D — PERSISTENT RUNTIME, DEMO PATIENT & ANDROID CLINICAL ALERT DELIVERY REPORT

## 1. Current Architecture Overview
ARGUS operates as a multi-tier clinical decision-support ecosystem:
1. **Part 1 Simulator (`part1/backend`)**: Simulates synthetic patient trajectories, patient baselines, and streams vital signs over WebSocket (`ws://0.0.0.0:8001/api/v1/stream`).
2. **Part 2 Backend & Ingestion (`src/backend`)**: Connects to Part 1 via `Part1WSBridge` (`ws://part1:8001/api/v1/stream`), executes feature extraction, Logistic Regression inference, SHAP attributions, and `SmartAlertEngine` rules.
3. **Part 3 Flutter Mobile Client (`part3/mobile`)**: Connects to Part 2 via WebSocket (`ws://172.27.45.54:8000/ws/stream` or `ws://127.0.0.1:8000/ws/stream`), presenting ICU overview, live patient cards, and immediate bedside reviews.

---

## 2. Root Cause of Terminal Dependency
Previously, running ARGUS required keeping multiple interactive PowerShell terminals open to run `uvicorn` instances for Part 1 (port 8001) and Part 2 (port 8000) manually. Restarting processes resulted in memory wipes of registered patients (e.g. `PATIENT-001`), requiring manual HTTP POST creation calls (`POST /api/v1/patients`) and manual simulation triggers (`POST /api/v1/simulation/start`).

---

## 3. Persistent Runtime Solution
To eliminate manual setup and terminal fragility, two automated orchestration options were created:
1. **Docker Compose Orchestration (`docker-compose.yml`)**:
   - `part1`: Runs Part 1 simulator on port `8001` with `ARGUS_DEMO_MODE=true`.
   - `part2`: Runs Part 2 backend on port `8000` with `ARGUS_PART1_BRIDGE_ENABLED=true` and `ARGUS_PART1_WS_URL=ws://part1:8001/api/v1/stream`.
   - Built-in container health checks ensure Part 2 waits until Part 1 is healthy.
   - Command: `docker compose up -d`
2. **Single-Command PowerShell Startup (`scripts/start_argus.ps1`)**:
   - Automated local process runner configuring host environments (`0.0.0.0:8001` & `0.0.0.0:8000`) and starting both services seamlessly without manual intervention.

---

## 4. Patient Persistence Solution
In `part1/backend/app/services/patient_registry.py`, `PatientRegistry` was upgraded with disk persistence (`patient_registry.json`).
- On startup, existing patient registries are reloaded from disk.
- `create_patient()` checks if `patient_id` (e.g., `PATIENT-001`) already exists before creation, preventing duplicate errors or duplicate records on process restarts.

---

## 5. Demo Mode (`ARGUS_DEMO_MODE=true`)
In `part1/backend/app/main.py`, FastAPI lifespan hooks check `settings.DEMO_MODE`:
- If `PATIENT-001` is missing, it auto-seeds `PATIENT-001` (Age 65, Male, `icu_baseline`, seed 42).
- When `ARGUS_DEMO_MODE=true`, Part 1 automatically activates the `rapid_deterioration` scenario for `PATIENT-001` and starts the simulation engine at 10x speed, generating automatic clinical deterioration without manual REST setup.

---

## 6. Android Notification Architecture
Implemented local notification delivery in `part3/mobile/lib/core/services/notification_service.dart` using `flutter_local_notifications` (v17.2.4):
- **Channel ID**: `argus_urgent_alerts`
- **Channel Name**: `ARGUS Urgent Clinical Alerts`
- **Importance / Priority**: `Importance.max` / `Priority.high`
- **Permissions**: Added `POST_NOTIFICATIONS`, `VIBRATE`, and `INTERNET` to `AndroidManifest.xml`.
- **Core Library Desugaring**: Enabled `isCoreLibraryDesugaringEnabled = true` in `build.gradle.kts` with `desugar_jdk_libs:2.1.4`.

---

## 7. Sound & Vibration Implementation
- **Sound**: Standard high-priority notification sound enabled on channel creation.
- **Vibration**: Configured custom clinical urgency vibration pattern (`Int64List.fromList([0, 500, 200, 500, 200, 500])`).

---

## 8. Notification Permission Handling
Android 13+ (API 33+) permission is requested gracefully during app startup via `NotificationService.instance.initialize()`. If permission is denied or restricted by Android settings, visual in-app banners and cards remain fully functional without app crashes.

---

## 9. Deduplication Mechanism
`NotificationService` maintains per-patient notification tracking (`_lastNotifiedSeverity`):
- Notifications trigger **only** when a patient first enters `RED / URGENT` rank or escalates into `RED / URGENT`.
- Subsequent prediction stream updates for an already notified patient do not re-trigger sound or vibration spam.
- If patient risk drops below URGENT, tracking resets so future risk escalations generate a fresh alert.

---

## 10. Immediate Review Routing
Notifications include the target `patientId` as the notification payload. Tapping an alert fires `onNotificationTap`, calling `appState.selectPatient(patientId)` and immediately navigating the mobile UI to the `ImmediateReviewScreen` for that specific patient.

---

## 11. Testing Summary
1. **Backend Integration Tests**: Executed `python -m pytest part1/tests` — **100/100 PASSED**.
2. **Flutter Static Analysis**: Executed `flutter analyze` — **0 ISSUES**.
3. **Flutter Test Suite**: Executed `flutter test` — **20/20 PASSED**.
4. **Docker Compose Validation**: Executed `docker compose config` — **PASSED**.

---

## 12. Build Results & Distribution Artifacts

* **Development Debug APK**:
  - Path: `part3/mobile/build/app/outputs/flutter-apk/app-debug.apk`
  - Command: `flutter build apk --debug`
  - Deployment: Installed on physical/emulator devices via `adb install -r app-debug.apk`.

* **Release Build Process for Distribution**:
  - Command: `flutter build apk --release`
  - Note: Release builds require configuring custom keystore signing credentials in `android/app/build.gradle.kts` (`signingConfigs`).

---

## 13. Remaining Limitations
* Android system Do-Not-Disturb and Silent mode settings are respected per system security policies.
