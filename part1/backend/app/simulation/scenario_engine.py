"""
Scenario and Trajectory State-Machine Engine.

Simulates physiological trajectories, state transitions (STABLE -> EARLY_CHANGE -> DETERIORATING -> CRITICAL -> RECOVERY),
and sensor fault injection.
"""

from enum import Enum
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field

from app.schemas.contract import QualityStatus, ScenarioState


class ScenarioEngineState(str, Enum):
    STABLE = "STABLE"
    EARLY_CHANGE = "EARLY_CHANGE"
    DETERIORATING = "DETERIORATING"
    CRITICAL = "CRITICAL"
    RECOVERY = "RECOVERY"


class ScenarioName(str, Enum):
    STABLE = "stable"
    GRADUAL_DETERIORATION = "gradual_deterioration"
    RAPID_DETERIORATION = "rapid_deterioration"
    RECOVERY = "recovery"
    NOISY = "noisy"
    SENSOR_FAILURE = "sensor_failure"
    DATA_QUALITY_PROBLEM = "data_quality_problem"


class ScenarioEffect(BaseModel):
    hr_delta: float = Field(0.0, description="HR offset in bpm")
    sys_bp_delta: float = Field(0.0, description="Systolic BP offset in mmHg")
    dia_bp_delta: float = Field(0.0, description="Diastolic BP offset in mmHg")
    spo2_delta: float = Field(0.0, description="SpO2 offset in %")
    temp_delta: float = Field(0.0, description="Temperature offset in °C")
    rr_delta: float = Field(0.0, description="RR offset in breaths/min")
    noise_multiplier: float = Field(1.0, ge=0.1, description="Noise scaling factor")
    quality_status: QualityStatus = Field(QualityStatus.VALID, description="Data quality classification")
    contract_scenario_state: ScenarioState = Field(ScenarioState.STABLE, description="Data contract scenario metadata")


class ScenarioMetadata(BaseModel):
    scenario_name: ScenarioName
    engine_state: ScenarioEngineState
    elapsed_seconds: float
    contract_scenario_state: ScenarioState


class ScenarioEngine:
    """
    Trajectory State Machine Engine.
    Computes deterministic physiological offsets and state transitions driven by simulation time.
    """

    # Maximum deterioration deltas
    MAX_DETERIORATION = {
        "hr": 35.0,        # +35 bpm
        "sys": -30.0,      # -30 mmHg
        "dia": -20.0,      # -20 mmHg
        "spo2": -7.0,      # -7.0 %
        "temp": 1.5,       # +1.5 °C
        "rr": 10.0,        # +10 breaths/min
    }

    def __init__(self, scenario_name: ScenarioName = ScenarioName.STABLE):
        self._scenario_name = scenario_name
        self._elapsed_seconds = 0.0
        self._start_time_seconds: Optional[float] = None

    @property
    def scenario_name(self) -> ScenarioName:
        return self._scenario_name

    def set_scenario(self, scenario_name: ScenarioName) -> None:
        """
        Switches active scenario and resets scenario timer.
        """
        self._scenario_name = scenario_name
        self._elapsed_seconds = 0.0
        self._start_time_seconds = None

    def update(self, elapsed_sim_seconds: float) -> ScenarioEffect:
        """
        Updates scenario state machine given current simulation elapsed time.
        Returns the computed ScenarioEffect.
        """
        self._elapsed_seconds = max(0.0, float(elapsed_sim_seconds))
        return self._compute_effect()

    def get_current_state(self) -> ScenarioEngineState:
        """
        Evaluates and returns current engine state machine phase.
        """
        effect, state, contract_state = self._evaluate_state_and_ratio()
        return state

    def get_metadata(self) -> ScenarioMetadata:
        effect, state, contract_state = self._evaluate_state_and_ratio()
        return ScenarioMetadata(
            scenario_name=self._scenario_name,
            engine_state=state,
            elapsed_seconds=self._elapsed_seconds,
            contract_scenario_state=contract_state,
        )

    def _compute_effect(self) -> ScenarioEffect:
        effect, state, contract_state = self._evaluate_state_and_ratio()
        return effect

    def _evaluate_state_and_ratio(self) -> Tuple[ScenarioEffect, ScenarioEngineState, ScenarioState]:
        t = self._elapsed_seconds
        s_name = self._scenario_name

        if s_name == ScenarioName.STABLE:
            return (
                ScenarioEffect(
                    contract_scenario_state=ScenarioState.STABLE,
                    quality_status=QualityStatus.VALID,
                ),
                ScenarioEngineState.STABLE,
                ScenarioState.STABLE,
            )

        elif s_name == ScenarioName.GRADUAL_DETERIORATION:
            # 30-min horizon (1800s):
            # 0 - 300s: STABLE (0%)
            # 300 - 900s: EARLY_CHANGE (0% -> 35%)
            # 900 - 1500s: DETERIORATING (35% -> 80%)
            # 1500s+: CRITICAL (100%)
            if t < 300.0:
                state = ScenarioEngineState.STABLE
                ratio = 0.0
            elif t < 900.0:
                state = ScenarioEngineState.EARLY_CHANGE
                ratio = 0.35 * ((t - 300.0) / 600.0)
            elif t < 1500.0:
                state = ScenarioEngineState.DETERIORATING
                ratio = 0.35 + 0.45 * ((t - 900.0) / 600.0)
            else:
                state = ScenarioEngineState.CRITICAL
                ratio = min(1.0, 0.80 + 0.20 * ((t - 1500.0) / 300.0))

            contract_state = (
                ScenarioState.GRADUAL_DETERIORATION
                if state != ScenarioEngineState.STABLE
                else ScenarioState.STABLE
            )
            return self._build_deterioration_effect(ratio, contract_state), state, contract_state

        elif s_name == ScenarioName.RAPID_DETERIORATION:
            # 10-min horizon (600s):
            # 0 - 60s: STABLE (0%)
            # 60 - 180s: EARLY_CHANGE (0% -> 40%)
            # 180 - 360s: DETERIORATING (40% -> 85%)
            # 360s+: CRITICAL (100%)
            if t < 60.0:
                state = ScenarioEngineState.STABLE
                ratio = 0.0
            elif t < 180.0:
                state = ScenarioEngineState.EARLY_CHANGE
                ratio = 0.40 * ((t - 60.0) / 120.0)
            elif t < 360.0:
                state = ScenarioEngineState.DETERIORATING
                ratio = 0.40 + 0.45 * ((t - 180.0) / 180.0)
            else:
                state = ScenarioEngineState.CRITICAL
                ratio = min(1.0, 0.85 + 0.15 * ((t - 360.0) / 120.0))

            contract_state = (
                ScenarioState.RAPID_DETERIORATION
                if state != ScenarioEngineState.STABLE
                else ScenarioState.STABLE
            )
            return self._build_deterioration_effect(ratio, contract_state), state, contract_state

        elif s_name == ScenarioName.RECOVERY:
            # Starts in CRITICAL (100%), over 600s returns to 0% (STABLE)
            if t >= 600.0:
                state = ScenarioEngineState.STABLE
                ratio = 0.0
            else:
                state = ScenarioEngineState.RECOVERY
                ratio = 1.0 - (t / 600.0)

            contract_state = ScenarioState.RECOVERY
            return self._build_deterioration_effect(ratio, contract_state), state, contract_state

        elif s_name == ScenarioName.NOISY:
            return (
                ScenarioEffect(
                    noise_multiplier=3.5,
                    contract_scenario_state=ScenarioState.NOISY,
                    quality_status=QualityStatus.VALID,
                ),
                ScenarioEngineState.STABLE,
                ScenarioState.NOISY,
            )

        elif s_name == ScenarioName.SENSOR_FAILURE:
            return (
                ScenarioEffect(
                    noise_multiplier=1.0,
                    contract_scenario_state=ScenarioState.SENSOR_FAILURE,
                    quality_status=QualityStatus.DISCONNECTED,
                ),
                ScenarioEngineState.STABLE,
                ScenarioState.SENSOR_FAILURE,
            )

        elif s_name == ScenarioName.DATA_QUALITY_PROBLEM:
            # Alternates missing/invalid data quality states
            quality = QualityStatus.MISSING if int(t) % 2 == 0 else QualityStatus.INVALID
            return (
                ScenarioEffect(
                    noise_multiplier=2.0,
                    contract_scenario_state=ScenarioState.DATA_QUALITY_PROBLEM,
                    quality_status=quality,
                ),
                ScenarioEngineState.STABLE,
                ScenarioState.DATA_QUALITY_PROBLEM,
            )

        return (
            ScenarioEffect(contract_scenario_state=ScenarioState.STABLE),
            ScenarioEngineState.STABLE,
            ScenarioState.STABLE,
        )

    def _build_deterioration_effect(self, ratio: float, contract_state: ScenarioState) -> ScenarioEffect:
        max_d = self.MAX_DETERIORATION
        return ScenarioEffect(
            hr_delta=max_d["hr"] * ratio,
            sys_bp_delta=max_d["sys"] * ratio,
            dia_bp_delta=max_d["dia"] * ratio,
            spo2_delta=max_d["spo2"] * ratio,
            temp_delta=max_d["temp"] * ratio,
            rr_delta=max_d["rr"] * ratio,
            noise_multiplier=1.0 + (0.5 * ratio),
            quality_status=QualityStatus.VALID,
            contract_scenario_state=contract_state,
        )
