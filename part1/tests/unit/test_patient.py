"""
Unit tests for Patient, PatientFactory, and PatientRegistry subsystems.
"""

import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.schemas.patient import (
    Patient,
    PatientBaseline,
    PatientProfileType,
    PatientSex,
    PatientStatus,
)
from app.simulation.patient_generator import PatientFactory
from app.services.patient_registry import PatientRegistry
from app.core.exceptions import ARGUSException


def test_patient_baseline_validation():
    baseline = PatientBaseline(
        heart_rate=75.0,
        systolic_bp=120.0,
        diastolic_bp=80.0,
        spo2=98.0,
        temperature=36.8,
        respiratory_rate=16.0,
    )
    assert baseline.heart_rate == 75.0
    assert baseline.systolic_bp == 120.0
    assert baseline.diastolic_bp == 80.0


def test_invalid_bp_ratio_rejected():
    with pytest.raises(ValueError):
        PatientBaseline(
            heart_rate=75.0,
            systolic_bp=100.0,
            diastolic_bp=110.0,  # Diastolic >= Systolic
            spo2=98.0,
            temperature=36.8,
            respiratory_rate=16.0,
        )


def test_deterministic_seeded_patient_factory():
    patient1 = PatientFactory.create_patient(seed=42, profile_type=PatientProfileType.STANDARD)
    patient2 = PatientFactory.create_patient(seed=42, profile_type=PatientProfileType.STANDARD)

    assert patient1.baseline.heart_rate == patient2.baseline.heart_rate
    assert patient1.baseline.systolic_bp == patient2.baseline.systolic_bp
    assert patient1.baseline.diastolic_bp == patient2.baseline.diastolic_bp
    assert patient1.baseline.spo2 == patient2.baseline.spo2
    assert patient1.baseline.temperature == patient2.baseline.temperature
    assert patient1.baseline.respiratory_rate == patient2.baseline.respiratory_rate


def test_different_patient_profiles():
    athletic = PatientFactory.create_patient(seed=10, profile_type=PatientProfileType.ATHLETIC)
    hypertensive = PatientFactory.create_patient(seed=10, profile_type=PatientProfileType.HYPERTENSIVE)
    icu = PatientFactory.create_patient(seed=10, profile_type=PatientProfileType.ICU_BASELINE)

    # Athletic HR should be lower than ICU baseline HR
    assert athletic.baseline.heart_rate < icu.baseline.heart_rate
    # Hypertensive systolic BP should be significantly higher than athletic
    assert hypertensive.baseline.systolic_bp > athletic.baseline.systolic_bp


def test_stable_and_unique_ids():
    patient_a = PatientFactory.create_patient(patient_id="P-STABLE-01", session_id="SESS-01")
    patient_b = PatientFactory.create_patient(patient_id="P-STABLE-02", session_id="SESS-01")

    assert patient_a.patient_id == "P-STABLE-01"
    assert patient_b.patient_id == "P-STABLE-02"
    assert patient_a.patient_id != patient_b.patient_id


def test_patient_registry_lifecycle():
    registry = PatientRegistry()
    registry.clear()

    # Create & Register Patients
    p1 = registry.create_patient(patient_id="P-201", profile_type=PatientProfileType.STANDARD)
    p2 = registry.create_patient(patient_id="P-202", profile_type=PatientProfileType.GERIATRIC)

    assert len(registry.list_patients()) == 2
    assert registry.get_patient("P-201").patient_id == "P-201"
    assert registry.get_patient("P-202").profile_type == PatientProfileType.GERIATRIC

    # Update Status
    updated_p1 = registry.update_patient_status("P-201", PatientStatus.PAUSED)
    assert updated_p1.status == PatientStatus.PAUSED
    assert registry.get_patient("P-201").status == PatientStatus.PAUSED

    # List by Status
    paused_list = registry.list_patients(status=PatientStatus.PAUSED)
    assert len(paused_list) == 1
    assert paused_list[0].patient_id == "P-201"

    # Remove Patient
    removed = registry.remove_patient("P-201")
    assert removed is True
    assert registry.get_patient("P-201") is None
    assert len(registry.list_patients()) == 1


def test_registry_update_nonexistent_patient_raises_exception():
    registry = PatientRegistry()
    registry.clear()
    with pytest.raises(ARGUSException) as exc_info:
        registry.update_patient_status("NONEXISTENT", PatientStatus.DISCHARGED)
    assert exc_info.value.code == "PATIENT_NOT_FOUND"
