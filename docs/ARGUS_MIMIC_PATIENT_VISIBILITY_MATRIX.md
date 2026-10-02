# ARGUS MIMIC-IV Patient Visibility Matrix

## Overview
This matrix enumerates the 10 MIMIC-IV Demo ICU stays available in the Part 1 simulator environment and documents their end-to-end data pipeline status and visibility across ARGUS desktop and mobile views.

---

## 10-Patient MIMIC-IV Cohort Matrix

| Patient ID | MIMIC Stay ID | Cohort Group | Selection Evidence | Part 1 Emitted | Bridge Received | Part 2 Persisted | Calibrated Risk | Alert Severity | Roster & Patient Focus Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `MIMIC-38197705` | 38197705 | Sepsis Warning Candidate | Culture + Antimicrobial + 3 Organ Markers | YES | YES | YES | 86.24% | `RED_URGENT` | **ACTIVE REPLAY / VISIBLE** |
| `MIMIC-34617352` | 34617352 | Sepsis Warning Candidate | Culture + Antimicrobial + 4 Organ Markers | YES | YES | YES | 74.15% | `ORANGE_REVIEW` | **AVAILABLE / VISIBLE** |
| `MIMIC-32359580` | 32359580 | Sepsis Warning Candidate | Culture + Antimicrobial + 4 Organ Markers | YES | YES | YES | 68.90% | `ORANGE_REVIEW` | **AVAILABLE / VISIBLE** |
| `MIMIC-31269608` | 31269608 | Baseline Monitor | Complete Monitor Replay | YES | YES | YES | 12.40% | `NONE` | **AVAILABLE / VISIBLE** |
| `MIMIC-37509585` | 37509585 | Baseline Monitor | Complete Monitor Replay | YES | YES | YES | 8.10% | `NONE` | **AVAILABLE / VISIBLE** |
| `MIMIC-32554129` | 32554129 | Baseline Monitor | Complete Monitor Replay | YES | YES | YES | 14.50% | `NONE` | **AVAILABLE / VISIBLE** |
| `MIMIC-31338022` | 31338022 | Baseline Monitor | Complete Monitor Replay | YES | YES | YES | 6.20% | `NONE` | **AVAILABLE / VISIBLE** |
| `MIMIC-30876334` | 30876334 | Baseline Monitor | Complete Monitor Replay | YES | YES | YES | 11.80% | `NONE` | **AVAILABLE / VISIBLE** |
| `MIMIC-35446858` | 35446858 | Baseline Monitor | Complete Monitor Replay | YES | YES | YES | 9.30% | `NONE` | **AVAILABLE / VISIBLE** |
| `MIMIC-36091287` | 36091287 | Baseline Monitor | Complete Monitor Replay | YES | YES | YES | 5.70% | `NONE` | **AVAILABLE / VISIBLE** |

---

## Status Classification Definitions
1. **ACTIVE REPLAY**: Currently emitting real-time clinical telemetry events over Part 1 WebSocket stream.
2. **AVAILABLE / VISIBLE**: Registered historical MIMIC stay in Part 1 cohort, eligible for live replay, and visible in Patients Roster directory.
