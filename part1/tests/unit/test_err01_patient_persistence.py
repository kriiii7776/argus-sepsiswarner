"""
Unit tests for ERR-01: Patient Mutation Persistence.

Verifies that all registry mutations (update_patient_status, remove_patient, clear)
properly persist to disk and survive reloading into a new PatientRegistry instance.
"""

import pytest
from app.schemas.patient import PatientStatus
from app.services.patient_registry import PatientRegistry
from app.core.exceptions import ARGUSException


def test_1_status_update_persists_across_reloads(tmp_path):
    """
    Test 1: Create a patient, change its status, reload registry from disk.
    Verify the updated status survives reload.
    """
    persistence_file = str(tmp_path / "test_registry.json")
    reg1 = PatientRegistry(persistence_file=persistence_file)
    
    # 1. Create patient with default ACTIVE status
    p1 = reg1.create_patient(patient_id="PAT-ERR01-1", status=PatientStatus.ACTIVE)
    assert p1.status == PatientStatus.ACTIVE
    
    # 2. Update status to DISCHARGED
    updated_p1 = reg1.update_patient_status("PAT-ERR01-1", PatientStatus.DISCHARGED)
    assert updated_p1.status == PatientStatus.DISCHARGED
    
    # 3. Reload registry from disk using a fresh instance
    reg2 = PatientRegistry(persistence_file=persistence_file)
    reloaded_p1 = reg2.get_patient("PAT-ERR01-1")
    
    assert reloaded_p1 is not None
    assert reloaded_p1.status == PatientStatus.DISCHARGED


def test_2_patient_removal_persists_across_reloads(tmp_path):
    """
    Test 2: Create two patients, remove one, reload registry from disk.
    Verify removed patient is absent and remaining patient is present.
    """
    persistence_file = str(tmp_path / "test_registry.json")
    reg1 = PatientRegistry(persistence_file=persistence_file)
    
    reg1.create_patient(patient_id="PAT-KEEP-1")
    reg1.create_patient(patient_id="PAT-REMOVE-2")
    
    assert len(reg1.list_patients()) == 2
    
    # Remove patient 2
    removed = reg1.remove_patient("PAT-REMOVE-2")
    assert removed is True
    assert len(reg1.list_patients()) == 1
    
    # Reload registry from disk
    reg2 = PatientRegistry(persistence_file=persistence_file)
    assert reg2.get_patient("PAT-REMOVE-2") is None
    assert reg2.get_patient("PAT-KEEP-1") is not None
    assert len(reg2.list_patients()) == 1


def test_3_clear_registry_persists_across_reloads(tmp_path):
    """
    Test 3: Create multiple patients, clear registry, reload registry from disk.
    Verify registry contains zero patients.
    """
    persistence_file = str(tmp_path / "test_registry.json")
    reg1 = PatientRegistry(persistence_file=persistence_file)
    
    reg1.create_patient(patient_id="PAT-CLEAR-1")
    reg1.create_patient(patient_id="PAT-CLEAR-2")
    reg1.create_patient(patient_id="PAT-CLEAR-3")
    
    assert len(reg1.list_patients()) == 3
    
    # Clear registry
    reg1.clear()
    assert len(reg1.list_patients()) == 0
    
    # Reload registry from disk
    reg2 = PatientRegistry(persistence_file=persistence_file)
    assert len(reg2.list_patients()) == 0


def test_4_update_nonexistent_patient_raises_exception(tmp_path):
    """
    Test 4: Attempt to update a non-existent patient.
    Verify ARGUSException (404) is raised.
    """
    persistence_file = str(tmp_path / "test_registry.json")
    reg1 = PatientRegistry(persistence_file=persistence_file)
    
    with pytest.raises(ARGUSException) as exc_info:
        reg1.update_patient_status("PAT-NONEXISTENT", PatientStatus.DISCHARGED)
    
    assert exc_info.value.status_code == 404


def test_5_remove_nonexistent_patient_returns_false(tmp_path):
    """
    Test 5: Attempt to remove a non-existent patient.
    Verify return value is False.
    """
    persistence_file = str(tmp_path / "test_registry.json")
    reg1 = PatientRegistry(persistence_file=persistence_file)
    
    result = reg1.remove_patient("PAT-NONEXISTENT")
    assert result is False


def test_6_clear_empty_registry_succeeds(tmp_path):
    """
    Test 6: Clear an already empty registry.
    Verify no exception occurs and reloaded registry remains empty.
    """
    persistence_file = str(tmp_path / "test_registry.json")
    reg1 = PatientRegistry(persistence_file=persistence_file)
    
    reg1.clear()
    assert len(reg1.list_patients()) == 0
    
    reg2 = PatientRegistry(persistence_file=persistence_file)
    assert len(reg2.list_patients()) == 0
