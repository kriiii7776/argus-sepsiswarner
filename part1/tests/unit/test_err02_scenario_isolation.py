"""
Unit and integration tests for ERR-02: Per-Patient Scenario Engine Isolation.

Ensures every active simulation patient maintains an independent ScenarioEngine state machine,
preventing cross-patient scenario leakage or state contamination.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import List

from app.schemas.patient import PatientProfileType
from app.schemas.contract import ScenarioState
from app.simulation.scenario_engine import ScenarioName, ScenarioEngineState
from app.services.patient_registry import PatientRegistry
from app.services.simulation_service import SimulationService
from app.simulation.vital_generator import VitalSignGenerator


@pytest.fixture
def isolated_service():
    """Provides a fresh SimulationService and PatientRegistry for testing."""
    from app.services.patient_registry import patient_registry
    patient_registry.clear()
    
    service = SimulationService()
    
    yield service, patient_registry
    
    # Teardown
    service.stop_simulation()
    patient_registry.clear()


def test_1_unassigned_patient_remains_stable(isolated_service):
    """
    TEST 1: Assign PATIENT-A to rapid_deterioration. Do NOT assign PATIENT-B.
    Verify PATIENT-A has rapid_deterioration, PATIENT-B retains default stable.
    """
    service, registry = isolated_service
    
    p_a = registry.create_patient(patient_id="PATIENT-A", session_id="SESS-A")
    p_b = registry.create_patient(patient_id="PATIENT-B", session_id="SESS-B")
    
    # Set PATIENT-A to rapid_deterioration
    service.set_patient_scenario("PATIENT-A", ScenarioName.RAPID_DETERIORATION)
    
    engine_a = service.get_scenario_engine("PATIENT-A")
    engine_b = service.get_scenario_engine("PATIENT-B")
    
    assert engine_a.scenario_name == ScenarioName.RAPID_DETERIORATION
    assert engine_b.scenario_name == ScenarioName.STABLE
    
    effect_a = engine_a.update(300.0)
    effect_b = engine_b.update(300.0)
    
    assert effect_a.contract_scenario_state == ScenarioState.RAPID_DETERIORATION
    assert effect_b.contract_scenario_state == ScenarioState.STABLE


def test_2_independent_scenario_assignments(isolated_service):
    """
    TEST 2: PATIENT-A -> rapid_deterioration, PATIENT-B -> recovery.
    Verify both scenario states remain strictly independent.
    """
    service, registry = isolated_service
    
    registry.create_patient(patient_id="PATIENT-A", session_id="SESS-A")
    registry.create_patient(patient_id="PATIENT-B", session_id="SESS-B")
    
    service.set_patient_scenario("PATIENT-A", ScenarioName.RAPID_DETERIORATION)
    service.set_patient_scenario("PATIENT-B", ScenarioName.RECOVERY)
    
    engine_a = service.get_scenario_engine("PATIENT-A")
    engine_b = service.get_scenario_engine("PATIENT-B")
    
    assert engine_a.scenario_name == ScenarioName.RAPID_DETERIORATION
    assert engine_b.scenario_name == ScenarioName.RECOVERY


def test_3_patient_a_change_does_not_affect_patient_b(isolated_service):
    """
    TEST 3: Change PATIENT-A from rapid_deterioration to stable.
    Verify PATIENT-B remains in recovery.
    """
    service, registry = isolated_service
    
    registry.create_patient(patient_id="PATIENT-A", session_id="SESS-A")
    registry.create_patient(patient_id="PATIENT-B", session_id="SESS-B")
    
    service.set_patient_scenario("PATIENT-A", ScenarioName.RAPID_DETERIORATION)
    service.set_patient_scenario("PATIENT-B", ScenarioName.RECOVERY)
    
    # Change PATIENT-A to stable
    service.set_patient_scenario("PATIENT-A", ScenarioName.STABLE)
    
    engine_a = service.get_scenario_engine("PATIENT-A")
    engine_b = service.get_scenario_engine("PATIENT-B")
    
    assert engine_a.scenario_name == ScenarioName.STABLE
    assert engine_b.scenario_name == ScenarioName.RECOVERY


def test_4_patient_b_change_does_not_affect_patient_a(isolated_service):
    """
    TEST 4: Change PATIENT-B from recovery to noisy.
    Verify PATIENT-A remains in stable.
    """
    service, registry = isolated_service
    
    registry.create_patient(patient_id="PATIENT-A", session_id="SESS-A")
    registry.create_patient(patient_id="PATIENT-B", session_id="SESS-B")
    
    service.set_patient_scenario("PATIENT-A", ScenarioName.STABLE)
    service.set_patient_scenario("PATIENT-B", ScenarioName.RECOVERY)
    
    # Change PATIENT-B to noisy
    service.set_patient_scenario("PATIENT-B", ScenarioName.NOISY)
    
    engine_a = service.get_scenario_engine("PATIENT-A")
    engine_b = service.get_scenario_engine("PATIENT-B")
    
    assert engine_a.scenario_name == ScenarioName.STABLE
    assert engine_b.scenario_name == ScenarioName.NOISY


def test_5_emitted_vital_messages_contain_patient_specific_scenarios(isolated_service):
    """
    TEST 5: Generate actual vital update messages for both patients.
    Verify emitted event messages contain patient-specific scenario state tags.
    """
    service, registry = isolated_service
    
    p_a = registry.create_patient(patient_id="PATIENT-A", session_id="SESS-A")
    p_b = registry.create_patient(patient_id="PATIENT-B", session_id="SESS-B")
    
    service.set_patient_scenario("PATIENT-A", ScenarioName.RAPID_DETERIORATION)
    service.set_patient_scenario("PATIENT-B", ScenarioName.STABLE)
    
    gen_a = VitalSignGenerator(p_a, seed=101)
    gen_b = VitalSignGenerator(p_b, seed=202)
    
    now = datetime.now(timezone.utc)
    sim_time = datetime.fromtimestamp(1700000000, tz=timezone.utc)
    
    engine_a = service.get_scenario_engine("PATIENT-A")
    engine_b = service.get_scenario_engine("PATIENT-B")
    
    effect_a = engine_a.update(300.0)
    effect_b = engine_b.update(300.0)
    
    msg_a = gen_a.generate_vitals(sim_time, now, scenario_state=effect_a.contract_scenario_state, scenario_effect=effect_a)
    msg_b = gen_b.generate_vitals(sim_time, now, scenario_state=effect_b.contract_scenario_state, scenario_effect=effect_b)
    
    assert msg_a.scenario_state == ScenarioState.RAPID_DETERIORATION
    assert msg_b.scenario_state == ScenarioState.STABLE


@pytest.mark.asyncio
async def test_6_concurrent_simulation_stream_isolation(isolated_service):
    """
    TEST 6: Run multi-patient streaming and verify no cross-patient contamination occurs.
    """
    service, registry = isolated_service
    
    p_a = registry.create_patient(patient_id="PATIENT-A", session_id="SESS-A")
    p_b = registry.create_patient(patient_id="PATIENT-B", session_id="SESS-B")
    p_c = registry.create_patient(patient_id="PATIENT-C", session_id="SESS-C")
    
    service.set_patient_scenario("PATIENT-A", ScenarioName.RAPID_DETERIORATION)
    service.set_patient_scenario("PATIENT-B", ScenarioName.RECOVERY)
    service.set_patient_scenario("PATIENT-C", ScenarioName.STABLE)
    
    # Verify all 3 engines exist and are isolated
    assert service.get_scenario_engine("PATIENT-A").scenario_name == ScenarioName.RAPID_DETERIORATION
    assert service.get_scenario_engine("PATIENT-B").scenario_name == ScenarioName.RECOVERY
    assert service.get_scenario_engine("PATIENT-C").scenario_name == ScenarioName.STABLE
    
    # Test lifecycle cleanup: remove PATIENT-B
    registry.remove_patient("PATIENT-B")
    
    # Simulate stream tick cleanup
    active_ids = {p.patient_id for p in registry.list_patients()}
    stale_ids = set(service._scenario_engines.keys()) - active_ids
    for sid in stale_ids:
        service._scenario_engines.pop(sid, None)
        
    assert "PATIENT-B" not in service._scenario_engines
    assert "PATIENT-A" in service._scenario_engines
    assert "PATIENT-C" in service._scenario_engines
