"""
Unit tests for ERR-04: Structured Persistence Error Logging.

Verifies that disk I/O and JSON deserialization failures in PatientRegistry
are properly logged at ERROR level instead of being silently swallowed,
while preserving valid load/save functionality and regression safety.
"""

import pytest
import logging
from pathlib import Path
from app.schemas.patient import PatientStatus, PatientProfileType
from app.services.patient_registry import PatientRegistry
from app.simulation.patient_generator import PatientFactory
from app.simulation.scenario_engine import ScenarioName
from app.simulation.vital_generator import VitalSignGenerator
from app.services.simulation_service import SimulationService


def test_1_save_failure_logs_error(tmp_path, caplog, monkeypatch):
    """
    TEST 1: Simulate a controlled disk write failure during _save_to_disk().
    Verify ERROR level log is emitted containing file path and exception context.
    """
    persistence_file = str(tmp_path / "test_save_fail.json")
    reg = PatientRegistry(persistence_file=persistence_file)
    
    # Monkeypatch write_text to raise PermissionError
    def mock_write_text(self, data, encoding=None, errors=None):
        raise PermissionError("Access denied: disk write failure simulation")
        
    monkeypatch.setattr(Path, "write_text", mock_write_text)
    
    with caplog.at_level(logging.ERROR, logger="argus"):
        caplog.clear()
        reg.create_patient(patient_id="PAT-SAVE-FAIL")
        
    # Verify ERROR log was emitted
    error_records = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert len(error_records) >= 1
    assert "Failed to save patient registry to disk file" in error_records[0].message
    assert "Access denied" in error_records[0].message or error_records[0].exc_info is not None


def test_2_load_invalid_json_logs_error(tmp_path, caplog):
    """
    TEST 2: Create a corrupted JSON persistence file.
    Verify loading logs an ERROR level message and safely falls back to empty registry.
    """
    corrupt_file = tmp_path / "corrupt_registry.json"
    corrupt_file.write_text("{ CORRUPTED INVALID JSON CONTENT ::: ")
    
    with caplog.at_level(logging.ERROR, logger="argus"):
        caplog.clear()
        reg = PatientRegistry(persistence_file=str(corrupt_file))
        
    error_records = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert len(error_records) >= 1
    assert "Failed to load patient registry from disk file" in error_records[0].message
    assert len(reg.list_patients()) == 0


def test_3_load_file_read_failure_logs_error(tmp_path, caplog, monkeypatch):
    """
    TEST 3: Simulate a controlled disk read failure during _load_from_disk().
    Verify ERROR level log is emitted.
    """
    file_path = tmp_path / "read_fail.json"
    file_path.write_text("[]")
    
    def mock_read_text(self, encoding=None, errors=None):
        raise OSError("I/O failure: disk read error simulation")
        
    monkeypatch.setattr(Path, "read_text", mock_read_text)
    
    with caplog.at_level(logging.ERROR, logger="argus"):
        caplog.clear()
        reg = PatientRegistry(persistence_file=str(file_path))
        
    error_records = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert len(error_records) >= 1
    assert "Failed to load patient registry from disk file" in error_records[0].message


def test_4_valid_load_succeeds_without_error_log(tmp_path, caplog):
    """
    TEST 4: Load a valid registry file.
    Verify no ERROR logs are emitted and patients load normally.
    """
    valid_file = str(tmp_path / "valid_registry.json")
    reg1 = PatientRegistry(persistence_file=valid_file)
    reg1.create_patient(patient_id="PAT-VALID-LOAD")
    
    with caplog.at_level(logging.ERROR, logger="argus"):
        caplog.clear()
        reg2 = PatientRegistry(persistence_file=valid_file)
        
    error_records = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert len(error_records) == 0
    assert reg2.get_patient("PAT-VALID-LOAD") is not None


def test_5_valid_save_succeeds_without_error_log(tmp_path, caplog):
    """
    TEST 5: Perform a normal patient mutation.
    Verify save succeeds, no ERROR log is emitted, and file is reloaded.
    """
    valid_file = str(tmp_path / "valid_save.json")
    reg = PatientRegistry(persistence_file=valid_file)
    
    with caplog.at_level(logging.ERROR, logger="argus"):
        caplog.clear()
        p = reg.create_patient(patient_id="PAT-VALID-SAVE")
        reg.update_patient_status(p.patient_id, PatientStatus.DISCHARGED)
        
    error_records = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert len(error_records) == 0
    
    reloaded = PatientRegistry(persistence_file=valid_file)
    assert reloaded.get_patient("PAT-VALID-SAVE").status == PatientStatus.DISCHARGED


def test_6_err01_mutation_persistence_regression(tmp_path):
    """
    TEST 6: ERR-01 Regression Check.
    Verify status updates, removals, and clears continue to persist correctly.
    """
    file_path = str(tmp_path / "err01_regression.json")
    reg = PatientRegistry(persistence_file=file_path)
    
    p = reg.create_patient(patient_id="PAT-REG-01")
    reg.update_patient_status("PAT-REG-01", PatientStatus.DISCHARGED)
    
    r1 = PatientRegistry(persistence_file=file_path)
    assert r1.get_patient("PAT-REG-01").status == PatientStatus.DISCHARGED
    
    reg.remove_patient("PAT-REG-01")
    r2 = PatientRegistry(persistence_file=file_path)
    assert r2.get_patient("PAT-REG-01") is None
    
    reg.create_patient(patient_id="PAT-REG-02")
    reg.clear()
    r3 = PatientRegistry(persistence_file=file_path)
    assert len(r3.list_patients()) == 0


def test_7_err02_scenario_isolation_regression():
    """
    TEST 7: ERR-02 Regression Check.
    Verify scenario engine isolation remains intact.
    """
    service = SimulationService()
    
    from app.services.patient_registry import patient_registry
    patient_registry.clear()
    
    p_a = patient_registry.create_patient(patient_id="PAT-ISO-A")
    p_b = patient_registry.create_patient(patient_id="PAT-ISO-B")
    
    service.set_patient_scenario("PAT-ISO-A", ScenarioName.RAPID_DETERIORATION)
    
    assert service.get_scenario_engine("PAT-ISO-A").scenario_name == ScenarioName.RAPID_DETERIORATION
    assert service.get_scenario_engine("PAT-ISO-B").scenario_name == ScenarioName.STABLE
    
    patient_registry.clear()


def test_8_err03_seed_isolation_regression():
    """
    TEST 8: ERR-03 Regression Check.
    Verify random seed isolation remains intact.
    """
    p_a = PatientFactory.create_patient(patient_id="PAT-SEED-REG-A")
    p_b = PatientFactory.create_patient(patient_id="PAT-SEED-REG-B")
    
    gen_a = VitalSignGenerator(p_a)
    gen_b = VitalSignGenerator(p_b)
    
    assert gen_a.seed != gen_b.seed
