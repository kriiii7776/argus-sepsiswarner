# SepsisGuard AI: Hospital Interoperability Architecture

This document outlines the design for integrating SepsisGuard AI into existing hospital IT infrastructures. 

> **WARNING:** This is an architectural design document. SepsisGuard AI must **never** be connected to live hospital systems (e.g., Epic, Cerner) without explicit administrative authorization, IRB approval (if applicable), and strict adherence to HIPAA/GDPR data governance protocols.

## 1. System Architecture Overview

To ensure the Core ML Engine remains completely agnostic to the quirks of individual hospital EHRs, we utilize an **Adapter Architecture (Anti-Corruption Layer)**. 

The data flow is structured as follows:

```mermaid
flowchart LR
    A[Hospital EHR] -->|HL7v2 / FHIR| B(Integration Interface)
    B --> C{Adapter / Anti-Corruption Layer}
    C -->|Normalized JSON| D[Clinical Data Normalization]
    D --> E((SepsisGuard AI Engine))
    E -->|Risk & Alerts| F[React Dashboard]
    E -->|Writeback (Optional)| B
```

### Why an Adapter Architecture?
Every hospital implements EHR interfaces differently (e.g., local LOINC codes for labs, non-standard unit strings, varying HL7 v2.x segment usages). The Adapter Layer ingests these varied streams, maps them to standard interoperability formats (FHIR R4), and translates them into the strictly typed Pydantic models required by the SepsisGuard AI Engine.

## 2. Healthcare Interoperability Standards Mapping

SepsisGuard AI expects data in the paradigm of **HL7 FHIR (Fast Healthcare Interoperability Resources)**. Below is the mapping of clinical concepts to their appropriate FHIR resources:

| Clinical Concept | FHIR Resource | Purpose for SepsisGuard AI |
| :--- | :--- | :--- |
| **Patient Demographics** | `Patient` | Age, Sex (used for baseline physiology adjustments). |
| **Admission/Location** | `Encounter` | Identifies ICU status, admission time, and bed location. |
| **Vital Signs** | `Observation` (Category: `vital-signs`) | Heart Rate, Blood Pressure, Respiratory Rate, Temperature, SpO2. |
| **Laboratory Results** | `Observation` (Category: `laboratory`) | Lactate, WBC, Creatinine, Bilirubin, Platelets (Requires LOINC mapping). |
| **Medication Information** | `MedicationAdministration` / `MedicationRequest` | Tracking administration of Vasopressors or broad-spectrum IV antibiotics. |
| **Clinical Observations** | `Observation` / `Condition` | GCS (Glasgow Coma Scale), urine output, and clinician-documented SIRS/Sepsis flags. |

## 3. Data Pipeline Breakdown

### 3.1 Ingress (Integration Layer)
*   **Modern Hospitals:** Provide event-driven Webhooks via **FHIR R4 Subscriptions** or SMART on FHIR apps.
*   **Legacy Hospitals:** Provide TCP/IP feeds of **HL7 v2.x** messages (e.g., `ADT^A01` for admissions, `ORU^R01` for lab/vital results). A parsing engine (like Mirth Connect or NextGen Connect) will convert these to FHIR JSON before hitting our Adapter.

### 3.2 Adapter & Normalization (Anti-Corruption Layer)
1.  **Terminology Binding:** Converts local hospital codes (e.g., Hospital A's internal code for Lactate `LAC-BLD`) into standard terminology (`LOINC 2160-0`).
2.  **Unit Conversion:** Normalizes measurements (e.g., converting Temperature from Fahrenheit to Celsius).
3.  **Schema Enforcement:** Transforms the deeply nested FHIR JSON into the flat, dense `Patient`, `Vital`, and `Lab` Pydantic schemas expected by the `InferenceService`.

### 3.3 Core AI Engine & Dashboard
*   The AI Engine computes the Sepsis Risk Score, completely isolated from how the data was acquired.
*   The React Dashboard subscribes to the AI Engine via WebSockets for sub-second, real-time ICU monitoring updates.

### 3.4 Egress (Optional EHR Writeback)
If the hospital permits, SepsisGuard AI can write alerts back to the EHR:
*   Sends a `CommunicationRequest` or `Flag` FHIR resource to trigger an in-basket notification for the attending clinician inside Epic/Cerner.
