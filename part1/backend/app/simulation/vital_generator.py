"""
Continuous Vital Sign Generator & Physiological Variation Subsystem.

Generates smooth, coupled, baseline-anchored physiological vitals for synthetic patients,
incorporating scenario effects, noise scaling, and sensor fault simulation.
"""

import hashlib
from datetime import datetime, timezone
import math
from typing import Optional
import numpy as np

from app.schemas.contract import (
    DataSource,
    QualityStatus,
    ScenarioState,
    VitalSignSet,
    VitalUnits,
    VitalUpdateMessage,
)
from app.schemas.patient import Patient, PatientBaseline
from app.simulation.scenario_engine import ScenarioEffect


class VitalSignGenerator:
    """
    Continuous physiological vital sign generator.
    Generates realistic micro-variability (respiratory sinus arrhythmia, Mayer waves)
    around patient baseline, modified by continuous scenario trajectory effects.
    """

    def __init__(self, patient: Patient, seed: Optional[int] = None):
        self.patient = patient
        if seed is None:
            digest = hashlib.sha256(patient.patient_id.encode("utf-8")).hexdigest()
            self.seed = int(digest[:8], 16)
        else:
            self.seed = seed
        self.rng = np.random.default_rng(self.seed)

        # Base phase offsets for physiological wave coupling
        self._hr_phase = self.rng.uniform(0, 2 * math.pi)
        self._rr_phase = self.rng.uniform(0, 2 * math.pi)
        self._bp_phase = self.rng.uniform(0, 2 * math.pi)
        self._temp_phase = self.rng.uniform(0, 2 * math.pi)

        # Ornstein-Uhlenbeck continuous noise state tracking
        self._hr_ou_state = 0.0
        self._bp_ou_state = 0.0
        self._spo2_ou_state = 0.0

    def generate_vitals(
        self,
        simulation_time: datetime,
        wall_timestamp: Optional[datetime] = None,
        scenario_state: ScenarioState = ScenarioState.STABLE,
        quality_status: QualityStatus = QualityStatus.VALID,
        scenario_effect: Optional[ScenarioEffect] = None,
    ) -> VitalUpdateMessage:
        """
        Generates continuous physiological vitals at the given simulation_time,
        incorporating any active ScenarioEffect trajectory parameters.
        """
        if wall_timestamp is None:
            wall_timestamp = datetime.now(timezone.utc)

        effect = scenario_effect or ScenarioEffect(
            quality_status=quality_status,
            contract_scenario_state=scenario_state,
        )

        base: PatientBaseline = self.patient.baseline
        elapsed_seconds = simulation_time.timestamp()
        noise_mult = effect.noise_multiplier

        # 1. Respiratory Rate & Respiratory Sinus Arrhythmia (RSA)
        rr_wave = 1.5 * math.sin(2 * math.pi * 0.25 * elapsed_seconds + self._rr_phase)
        rr_val = float(np.clip(base.respiratory_rate + effect.rr_delta + rr_wave, 8.0, 45.0))

        # 2. Heart Rate Coupling (RSA + Mayer waves ~0.1 Hz)
        rsa_coupling = 2.5 * math.sin(2 * math.pi * 0.25 * elapsed_seconds + self._hr_phase)
        mayer_wave = 1.2 * math.sin(2 * math.pi * 0.1 * elapsed_seconds + self._hr_phase * 0.5)

        self._hr_ou_state = 0.85 * self._hr_ou_state + self.rng.normal(0, 0.3 * noise_mult)
        hr_val = float(np.clip(base.heart_rate + effect.hr_delta + rsa_coupling + mayer_wave + self._hr_ou_state, 30.0, 250.0))

        # 3. Blood Pressure (Systolic / Diastolic)
        bp_mayer = 2.0 * math.sin(2 * math.pi * 0.1 * elapsed_seconds + self._bp_phase)
        self._bp_ou_state = 0.85 * self._bp_ou_state + self.rng.normal(0, 0.4 * noise_mult)

        sys_val = float(np.clip(base.systolic_bp + effect.sys_bp_delta + bp_mayer + self._bp_ou_state, 40.0, 260.0))
        dia_val = float(np.clip(base.diastolic_bp + effect.dia_bp_delta + 0.6 * bp_mayer + 0.6 * self._bp_ou_state, 20.0, 150.0))

        if dia_val >= sys_val:
            dia_val = round(sys_val - 15.0, 1)

        # 4. SpO2 micro-fluctuations
        self._spo2_ou_state = 0.9 * self._spo2_ou_state + self.rng.normal(0, 0.05 * noise_mult)
        spo2_val = float(np.clip(base.spo2 + effect.spo2_delta + self._spo2_ou_state, 70.0, 100.0))

        # 5. Temperature circadian/micro drift
        temp_diurnal = 0.2 * math.sin(2 * math.pi * (elapsed_seconds / 86400.0) + self._temp_phase)
        temp_val = float(np.clip(base.temperature + effect.temp_delta + temp_diurnal, 34.0, 43.0))

        # Data quality fault simulation: handle disconnected/missing status
        if effect.quality_status in (QualityStatus.DISCONNECTED, QualityStatus.SENSOR_UNAVAILABLE, QualityStatus.MISSING):
            vital_set = VitalSignSet(
                heart_rate=None,
                systolic_bp=None,
                diastolic_bp=None,
                spo2=None,
                temperature=None,
                respiratory_rate=None,
            )
        else:
            vital_set = VitalSignSet(
                heart_rate=round(hr_val, 1),
                systolic_bp=round(sys_val, 1),
                diastolic_bp=round(dia_val, 1),
                spo2=round(spo2_val, 1),
                temperature=round(temp_val, 2),
                respiratory_rate=round(rr_val, 1),
            )

        return VitalUpdateMessage(
            schema_version="1.0",
            message_type="vital_update",
            patient_id=self.patient.patient_id,
            session_id=self.patient.session_id,
            source=DataSource.SYNTHETIC,
            timestamp=wall_timestamp,
            simulation_time=simulation_time,
            vitals=vital_set,
            vital_units=VitalUnits(),
            quality_status=effect.quality_status,
            scenario_state=effect.contract_scenario_state,
        )
