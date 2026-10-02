"""
Unit tests for ScenarioEngine state-machine trajectories and scenario effects.
"""

from datetime import datetime, timedelta, timezone
import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.schemas.contract import QualityStatus, ScenarioState
from app.schemas.patient import PatientProfileType
from app.simulation.patient_generator import PatientFactory
from app.simulation.vital_generator import VitalSignGenerator
from app.simulation.scenario_engine import (
    ScenarioEngine,
    ScenarioEngineState,
    ScenarioName,
)


def test_stable_scenario_remains_stable():
    engine = ScenarioEngine(ScenarioName.STABLE)

    for t_sec in [0.0, 100.0, 500.0, 2000.0]:
        effect = engine.update(t_sec)
        assert engine.get_current_state() == ScenarioEngineState.STABLE
        assert effect.hr_delta == 0.0
        assert effect.sys_bp_delta == 0.0
        assert effect.contract_scenario_state == ScenarioState.STABLE


def test_gradual_deterioration_trajectory_phases():
    engine = ScenarioEngine(ScenarioName.GRADUAL_DETERIORATION)

    # 0s: STABLE
    effect0 = engine.update(0.0)
    assert engine.get_current_state() == ScenarioEngineState.STABLE
    assert effect0.hr_delta == 0.0

    # 600s (10 min): EARLY_CHANGE
    effect_early = engine.update(600.0)
    assert engine.get_current_state() == ScenarioEngineState.EARLY_CHANGE
    assert effect_early.hr_delta > 0.0
    assert effect_early.sys_bp_delta < 0.0

    # 1200s (20 min): DETERIORATING
    effect_det = engine.update(1200.0)
    assert engine.get_current_state() == ScenarioEngineState.DETERIORATING
    assert effect_det.hr_delta > effect_early.hr_delta
    assert effect_det.sys_bp_delta < effect_early.sys_bp_delta

    # 1800s (30 min): CRITICAL
    effect_crit = engine.update(1800.0)
    assert engine.get_current_state() == ScenarioEngineState.CRITICAL
    assert effect_crit.hr_delta == pytest.approx(ScenarioEngine.MAX_DETERIORATION["hr"])
    assert effect_crit.sys_bp_delta == pytest.approx(ScenarioEngine.MAX_DETERIORATION["sys"])


def test_rapid_deterioration_progresses_faster():
    gradual = ScenarioEngine(ScenarioName.GRADUAL_DETERIORATION)
    rapid = ScenarioEngine(ScenarioName.RAPID_DETERIORATION)

    t_eval = 250.0  # 4.1 minutes
    eff_gradual = gradual.update(t_eval)
    eff_rapid = rapid.update(t_eval)

    # Rapid deterioration at 250s should be in DETERIORATING state while gradual is still STABLE
    assert gradual.get_current_state() == ScenarioEngineState.STABLE
    assert rapid.get_current_state() == ScenarioEngineState.DETERIORATING
    assert eff_rapid.hr_delta > eff_gradual.hr_delta


def test_recovery_reverses_trajectory():
    engine = ScenarioEngine(ScenarioName.RECOVERY)

    eff_start = engine.update(0.0)
    assert engine.get_current_state() == ScenarioEngineState.RECOVERY
    assert eff_start.hr_delta == pytest.approx(ScenarioEngine.MAX_DETERIORATION["hr"])

    eff_mid = engine.update(300.0)
    assert eff_mid.hr_delta < eff_start.hr_delta

    eff_end = engine.update(650.0)
    assert engine.get_current_state() == ScenarioEngineState.STABLE
    assert eff_end.hr_delta == 0.0


def test_noisy_scenario_effects():
    engine = ScenarioEngine(ScenarioName.NOISY)
    effect = engine.update(50.0)

    assert effect.noise_multiplier == 3.5
    assert effect.contract_scenario_state == ScenarioState.NOISY


def test_sensor_failure_scenario():
    engine = ScenarioEngine(ScenarioName.SENSOR_FAILURE)
    effect = engine.update(10.0)

    assert effect.quality_status == QualityStatus.DISCONNECTED
    assert effect.contract_scenario_state == ScenarioState.SENSOR_FAILURE


def test_reproducible_trajectories_with_same_seed_and_scenario():
    patient = PatientFactory.create_patient(seed=55, profile_type=PatientProfileType.STANDARD)

    gen1 = VitalSignGenerator(patient, seed=777)
    gen2 = VitalSignGenerator(patient, seed=777)

    engine1 = ScenarioEngine(ScenarioName.GRADUAL_DETERIORATION)
    engine2 = ScenarioEngine(ScenarioName.GRADUAL_DETERIORATION)

    sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    for step in range(5):
        t_sec = step * 300.0
        t_dt = sim_time + timedelta(seconds=t_sec)

        eff1 = engine1.update(t_sec)
        eff2 = engine2.update(t_sec)

        msg1 = gen1.generate_vitals(simulation_time=t_dt, scenario_effect=eff1)
        msg2 = gen2.generate_vitals(simulation_time=t_dt, scenario_effect=eff2)

        assert msg1.vitals.heart_rate == msg2.vitals.heart_rate
        assert msg1.vitals.systolic_bp == msg2.vitals.systolic_bp
        assert msg1.scenario_state == msg2.scenario_state


def test_metadata_generation():
    engine = ScenarioEngine(ScenarioName.GRADUAL_DETERIORATION)
    engine.update(1000.0)
    meta = engine.get_metadata()

    assert meta.scenario_name == ScenarioName.GRADUAL_DETERIORATION
    assert meta.engine_state == ScenarioEngineState.DETERIORATING
    assert meta.elapsed_seconds == 1000.0
