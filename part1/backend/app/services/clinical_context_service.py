"""Low-frequency laboratory/EHR replay stream for the simulator demo.

This service intentionally keeps the monitor and clinical streams separate.  The
included values are synthetic demonstration fixtures, not MIMIC-IV patient data.
Replace ``_build_demo_timeline`` with a credentialed MIMIC-IV importer when data
access is available; the REST and WebSocket contract remains unchanged.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.schemas.contract import ClinicalContext, ClinicalContextUnits, ClinicalUpdateMessage, DataSource
from app.simulation.scenario_engine import ScenarioName


class ClinicalContextService:
    UPDATE_INTERVAL_SECONDS = 60

    def __init__(self) -> None:
        self._timelines: Dict[str, List[ClinicalUpdateMessage]] = {}

    def reset_patient(self, patient_id: str) -> None:
        self._timelines.pop(patient_id, None)

    def as_of(
        self,
        patient_id: str,
        session_id: str,
        simulation_time: datetime,
        elapsed_seconds: float,
        scenario: ScenarioName,
    ) -> ClinicalUpdateMessage:
        """Return the newest result available at ``simulation_time`` (never a future value)."""
        timeline = self._timeline(patient_id, session_id, simulation_time, scenario)
        available = [item for item in timeline if item.recorded_at <= simulation_time]
        if available:
            return available[-1]
        return timeline[0]

    def _timeline(
        self, patient_id: str, session_id: str, simulation_time: datetime, scenario: ScenarioName
    ) -> List[ClinicalUpdateMessage]:
        key = f"{patient_id}:{session_id}:{scenario.value}"
        if key not in self._timelines:
            self._timelines[key] = self._build_demo_timeline(patient_id, session_id, simulation_time, scenario)
        return self._timelines[key]

    def _build_demo_timeline(
        self, patient_id: str, session_id: str, start: datetime, scenario: ScenarioName
    ) -> List[ClinicalUpdateMessage]:
        start = start.astimezone(timezone.utc)
        stable = ClinicalContext(platelets=230, bilirubin=0.7, creatinine=0.9, lactate=1.2,
            pao2_fio2_ratio=390, glasgow_coma_scale=15, urine_output_6h=480, norepinephrine_dose=0.0)
        worsening = ClinicalContext(platelets=105, bilirubin=2.8, creatinine=2.1, lactate=3.9,
            pao2_fio2_ratio=210, glasgow_coma_scale=11, urine_output_6h=170, norepinephrine_dose=0.12)
        critical = ClinicalContext(platelets=65, bilirubin=4.7, creatinine=3.1, lactate=5.6,
            pao2_fio2_ratio=145, glasgow_coma_scale=8, urine_output_6h=80, norepinephrine_dose=0.28)
        if scenario in (ScenarioName.GRADUAL_DETERIORATION, ScenarioName.RAPID_DETERIORATION):
            values = [stable, stable, worsening, critical]
        elif scenario == ScenarioName.RECOVERY:
            values = [critical, worsening, stable, stable]
        else:
            values = [stable, stable, stable, stable]
        return [ClinicalUpdateMessage(
            patient_id=patient_id, session_id=session_id, source=DataSource.CSV_REPLAY,
            timestamp=start, simulation_time=start + timedelta(seconds=index * self.UPDATE_INTERVAL_SECONDS),
            recorded_at=start + timedelta(seconds=index * self.UPDATE_INTERVAL_SECONDS),
            clinical_context=context, clinical_units=ClinicalContextUnits(), data_origin="synthetic_demo_replay",
        ) for index, context in enumerate(values)]


clinical_context_service = ClinicalContextService()
