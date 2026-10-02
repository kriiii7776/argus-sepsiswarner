"""
Unit tests for ERR-03: Patient Random Seed Isolation & Reproducibility.

Ensures every active patient maintains an independent, deterministic pseudo-random stream
derived from patient identity or explicit seed, eliminating hardcoded seed contamination.
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List

from app.schemas.patient import PatientProfileType
from app.schemas.contract import ScenarioState
from app.simulation.patient_generator import PatientFactory
from app.simulation.scenario_engine import ScenarioName
from app.simulation.vital_generator import VitalSignGenerator
from app.services.patient_registry import patient_registry
from app.services.simulation_service import SimulationService


def test_1_different_patients_generate_different_noise_sequences():
    """
    TEST 1: Create two equivalent patients with different IDs and no explicit seed.
    Verify generated vital sign noise patterns are NOT identical across multiple ticks.
    """
    p_a = PatientFactory.create_patient(patient_id="PATIENT-SEED-A", profile_type=PatientProfileType.STANDARD)
    p_b = PatientFactory.create_patient(patient_id="PATIENT-SEED-B", profile_type=PatientProfileType.STANDARD)
    
    gen_a = VitalSignGenerator(p_a)
    gen_b = VitalSignGenerator(p_b)
    
    assert gen_a.seed != gen_b.seed
    
    now = datetime.now(timezone.utc)
    different_count = 0
    total_samples = 10
    
    for i in range(total_samples):
        sim_time = datetime.fromtimestamp(1700000000 + i * 10, tz=timezone.utc)
        msg_a = gen_a.generate_vitals(sim_time, now)
        msg_b = gen_b.generate_vitals(sim_time, now)
        
        if (msg_a.vitals.heart_rate != msg_b.vitals.heart_rate or
            msg_a.vitals.systolic_bp != msg_b.vitals.systolic_bp or
            msg_a.vitals.spo2 != msg_b.vitals.spo2):
            different_count += 1
            
    assert different_count > 0, "Noise sequences for PATIENT-A and PATIENT-B should not be 100% identical!"


def test_2_explicitly_different_seeds_produce_different_sequences():
    """
    TEST 2: Create two patients with explicitly different seeds.
    Verify generated sequences differ.
    """
    p_a = PatientFactory.create_patient(patient_id="PAT-X", seed=100)
    p_b = PatientFactory.create_patient(patient_id="PAT-Y", seed=200)
    
    gen_a = VitalSignGenerator(p_a, seed=100)
    gen_b = VitalSignGenerator(p_b, seed=200)
    
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    msg_a = gen_a.generate_vitals(sim_time)
    msg_b = gen_b.generate_vitals(sim_time)
    
    assert (msg_a.vitals.heart_rate != msg_b.vitals.heart_rate or
            msg_a.vitals.systolic_bp != msg_b.vitals.systolic_bp)


def test_3_explicit_seed_is_100_percent_reproducible():
    """
    TEST 3: Instantiate VitalSignGenerator twice with the exact same explicit seed.
    Verify generated vital sign sequences are 100% identical and reproducible.
    """
    p = PatientFactory.create_patient(patient_id="PAT-REPRODUCE", seed=555)
    
    gen1 = VitalSignGenerator(p, seed=555)
    gen2 = VitalSignGenerator(p, seed=555)
    
    now = datetime.now(timezone.utc)
    for i in range(5):
        sim_time = datetime.fromtimestamp(1700000000 + i * 10, tz=timezone.utc)
        msg1 = gen1.generate_vitals(sim_time, now)
        msg2 = gen2.generate_vitals(sim_time, now)
        
        assert msg1.vitals.heart_rate == msg2.vitals.heart_rate
        assert msg1.vitals.systolic_bp == msg2.vitals.systolic_bp
        assert msg1.vitals.diastolic_bp == msg2.vitals.diastolic_bp
        assert msg1.vitals.spo2 == msg2.vitals.spo2


def test_4_derived_patient_seed_is_reproducible_across_instances():
    """
    TEST 4: Create VitalSignGenerator twice for the same patient without explicit seed.
    Verify the derived seed is stable and reproducible across generator instances.
    """
    p = PatientFactory.create_patient(patient_id="PAT-DERIVED-SEED")
    
    gen1 = VitalSignGenerator(p)
    gen2 = VitalSignGenerator(p)
    
    assert gen1.seed == gen2.seed
    
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    msg1 = gen1.generate_vitals(sim_time)
    msg2 = gen2.generate_vitals(sim_time)
    
    assert msg1.vitals.heart_rate == msg2.vitals.heart_rate
    assert msg1.vitals.systolic_bp == msg2.vitals.systolic_bp


def test_5_err02_scenario_isolation_remains_intact():
    """
    TEST 5: Verify ERR-02 scenario isolation is unaffected by seed changes.
    """
    patient_registry.clear()
    service = SimulationService()
    
    p_a = patient_registry.create_patient(patient_id="PATIENT-ERR02-A")
    p_b = patient_registry.create_patient(patient_id="PATIENT-ERR02-B")
    
    service.set_patient_scenario("PATIENT-ERR02-A", ScenarioName.RAPID_DETERIORATION)
    
    engine_a = service.get_scenario_engine("PATIENT-ERR02-A")
    engine_b = service.get_scenario_engine("PATIENT-ERR02-B")
    
    assert engine_a.scenario_name == ScenarioName.RAPID_DETERIORATION
    assert engine_b.scenario_name == ScenarioName.STABLE
    
    patient_registry.clear()


def test_6_rng_states_are_decoupled_between_patients():
    """
    TEST 6: Advance Patient A's generator multiple times.
    Verify Patient B's initial generation is unaffected by Patient A's iteration count.
    """
    p_a = PatientFactory.create_patient(patient_id="PAT-DECOUPLE-A")
    p_b = PatientFactory.create_patient(patient_id="PAT-DECOUPLE-B")
    
    gen_b_baseline = VitalSignGenerator(p_b)
    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    msg_b_initial = gen_b_baseline.generate_vitals(sim_time)
    
    # Instantiate gen_a and advance 50 times
    gen_a = VitalSignGenerator(p_a)
    for i in range(50):
        gen_a.generate_vitals(sim_time + timedelta(seconds=i))
        
    # Instantiate fresh gen_b
    gen_b_test = VitalSignGenerator(p_b)
    msg_b_after = gen_b_test.generate_vitals(sim_time)
    
    assert msg_b_initial.vitals.heart_rate == msg_b_after.vitals.heart_rate
    assert msg_b_initial.vitals.systolic_bp == msg_b_after.vitals.systolic_bp
