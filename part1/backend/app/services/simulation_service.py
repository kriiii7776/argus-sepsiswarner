"""
Simulation Runtime Orchestration Service.

Manages active simulation clock, active scenario engine, background streaming loops, and patient runtime bindings.
"""

from typing import Dict, Optional
from datetime import datetime, timezone
import asyncio

from app.schemas.control import SimulationStatusResponse
from app.schemas.patient import Patient
from app.simulation.clock import ClockState, SimulationClock
from app.simulation.scenario_engine import ScenarioEngine, ScenarioEngineState, ScenarioName
from app.core.logging import logger
from app.services.patient_registry import patient_registry
from app.core.exceptions import ARGUSException
from app.replay.mimic_historical import MIMICHistoricalReplay
from app.streaming.manager import stream_manager


class SimulationService:
    """
    Singleton service orchestrating simulation runtime components.
    """

    def __init__(self):
        self.clock = SimulationClock()
        self._scenario_engines: Dict[str, ScenarioEngine] = {}
        self._default_scenario_engine = ScenarioEngine(ScenarioName.STABLE)
        self.source_mode: str = "SIMULATION"  # "SIMULATION" or "REPLAY"
        self._active_session_id: Optional[str] = None
        self._active_patient_id: Optional[str] = None
        self._stream_task: Optional[asyncio.Task] = None
        self._historical_replay = MIMICHistoricalReplay()
        self._generators: dict = {}
        self._last_clinical_update_second: Optional[int] = None

    def get_scenario_engine(self, patient_id: Optional[str] = None) -> ScenarioEngine:
        """
        Retrieves or creates the patient-specific ScenarioEngine for patient_id,
        or active patient, or fallback default engine.
        """
        if patient_id:
            if patient_id not in self._scenario_engines:
                self._scenario_engines[patient_id] = ScenarioEngine(ScenarioName.STABLE)
            return self._scenario_engines[patient_id]
        elif self._active_patient_id:
            return self.get_scenario_engine(self._active_patient_id)
        return self._default_scenario_engine

    @property
    def scenario_engine(self) -> ScenarioEngine:
        """
        Backwards-compatible property returning the ScenarioEngine for the active patient (or default).
        """
        return self.get_scenario_engine(self._active_patient_id)

    @property
    def active_session_id(self) -> Optional[str]:
        return self._active_session_id

    @property
    def active_patient_id(self) -> Optional[str]:
        return self._active_patient_id

    def set_source_mode(self, mode: str) -> str:
        if mode.upper() in ("SIMULATION", "REPLAY"):
            self.source_mode = mode.upper()
        return self.source_mode

    def start_simulation(
        self,
        session_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        speed_factor: float = 1.0,
        initial_simulation_time: Optional[datetime] = None,
        source_mode: Optional[str] = None,
    ) -> SimulationStatusResponse:
        """
        Starts or restarts the simulation session clock.
        """
        if source_mode:
            self.set_source_mode(source_mode)

        if patient_id is not None:
            patient = patient_registry.get_patient(patient_id)
            if not patient:
                raise ARGUSException(
                    code="PATIENT_NOT_FOUND",
                    message=f"Patient '{patient_id}' not found.",
                    status_code=404,
                )
            self._active_patient_id = patient_id
            self._active_session_id = session_id or patient.session_id
        else:
            # Load the recorded, de-identified MIMIC-IV Demo cohort.
            patients = patient_registry.list_patients()
            if not patients:
                patients = [patient_registry.register_patient(patient) for patient in self._historical_replay.load()]
                self._active_patient_id = patients[0].patient_id
                self._active_session_id = session_id or patients[0].session_id
            else:
                self._active_patient_id = patients[0].patient_id
                self._active_session_id = session_id or patients[0].session_id

        self.clock.set_speed(speed_factor)
        self.clock.start(initial_simulation_time=initial_simulation_time)
        self._last_clinical_update_second = None
        self._ensure_stream_loop()
        return self.get_status()

    def pause_simulation(self) -> SimulationStatusResponse:
        """
        Pauses active simulation clock.
        """
        self.clock.pause()
        return self.get_status()

    def resume_simulation(self) -> SimulationStatusResponse:
        """
        Resumes paused simulation clock.
        """
        self.clock.resume()
        return self.get_status()

    def stop_simulation(self) -> SimulationStatusResponse:
        """
        Stops active simulation clock and resets all scenario engines.
        """
        self.clock.stop()
        for engine in self._scenario_engines.values():
            engine.set_scenario(ScenarioName.STABLE)
        self._default_scenario_engine.set_scenario(ScenarioName.STABLE)
        self._generators.clear()
        self._last_clinical_update_second = None
        return self.get_status()

    def set_speed(self, speed_factor: float) -> SimulationStatusResponse:
        """
        Updates simulation clock speed.
        """
        self.clock.set_speed(speed_factor)
        return self.get_status()

    def set_patient_scenario(self, patient_id: str, scenario_name: ScenarioName) -> SimulationStatusResponse:
        """
        Sets target scenario state-machine for a specific patient.
        """
        patient = patient_registry.get_patient(patient_id)
        if not patient:
            raise ARGUSException(
                code="PATIENT_NOT_FOUND",
                message=f"Patient '{patient_id}' not found in registry.",
                status_code=404,
            )
        self._active_patient_id = patient_id
        self._active_session_id = patient.session_id
        engine = self.get_scenario_engine(patient_id)
        engine.set_scenario(scenario_name)
        self._last_clinical_update_second = None
        return self.get_status()

    def _ensure_stream_loop(self) -> None:
        """Start one non-blocking publisher for monitor telemetry and EHR context."""
        if self._stream_task and not self._stream_task.done():
            return
        self._stream_task = asyncio.create_task(self._stream_loop())

    async def _stream_loop(self) -> None:
        from app.simulation.vital_generator import VitalSignGenerator

        logger.info("Simulation stream loop started")
        while True:
            try:
                await asyncio.sleep(1.0)
                if self.clock.status().state != ClockState.RUNNING:
                    if self.clock.status().state == ClockState.STOPPED:
                        logger.info("Simulation stream loop stopping (clock stopped)")
                        return
                    continue
                clock = self.clock.status()
                # One replay tick represents one minute of the source ICU timeline.
                replay_tick = int(clock.elapsed_sim_seconds / 60)

                # Clean up engines and generators for removed patients
                active_ids = {p.patient_id for p in patient_registry.list_patients()}
                stale_ids = set(self._scenario_engines.keys()) - active_ids
                for sid in stale_ids:
                    self._scenario_engines.pop(sid, None)
                stale_gen_ids = set(self._generators.keys()) - active_ids
                for sid in stale_gen_ids:
                    self._generators.pop(sid, None)

                for patient in patient_registry.list_patients():
                    if self.source_mode == "REPLAY" or patient.patient_id.startswith("MIMIC-"):
                        vital_message = self._historical_replay.vital_update(patient.patient_id, replay_tick)
                    else:
                        if patient.patient_id not in self._generators:
                            self._generators[patient.patient_id] = VitalSignGenerator(patient)
                        generator = self._generators[patient.patient_id]
                        engine = self.get_scenario_engine(patient.patient_id)
                        effect = engine.update(clock.elapsed_sim_seconds)
                        vital_message = generator.generate_vitals(
                            simulation_time=clock.simulation_time,
                            wall_timestamp=datetime.now(timezone.utc),
                            scenario_state=effect.contract_scenario_state,
                            quality_status=effect.quality_status,
                            scenario_effect=effect,
                        )

                    logger.debug(
                        "Broadcasting vital_update: patient_id=%s, session_id=%s, sim_time=%s",
                        vital_message.patient_id,
                        vital_message.session_id,
                        vital_message.simulation_time,
                    )
                    delivered = await stream_manager.broadcast(vital_message, session_id=vital_message.session_id)
                    logger.debug("Broadcast result: delivered_count=%d", delivered)

                    if (self.source_mode == "REPLAY" or patient.patient_id.startswith("MIMIC-")) and self._last_clinical_update_second != replay_tick:
                        clinical_message = self._historical_replay.clinical_update(patient.patient_id, replay_tick)
                        await stream_manager.broadcast(clinical_message, session_id=clinical_message.session_id)
                self._last_clinical_update_second = replay_tick
            except asyncio.CancelledError:
                logger.info("Simulation stream loop cancelled")
                break
            except Exception as exc:
                logger.error("Exception in simulation stream loop: %s", exc, exc_info=True)
                await asyncio.sleep(1.0)

    def get_status(self) -> SimulationStatusResponse:
        """
        Returns structured simulation runtime status summary.
        """
        clock_status = self.clock.status()
        engine = self.get_scenario_engine(self._active_patient_id)
        engine.update(clock_status.elapsed_sim_seconds)

        return SimulationStatusResponse(
            clock_status=clock_status,
            active_session_id=self._active_session_id,
            active_patient_id=self._active_patient_id,
            active_scenario_name=engine.scenario_name,
            active_scenario_state=engine.get_current_state(),
            registered_patients_count=len(patient_registry.list_patients()),
        )


# Global Singleton Simulation Service Instance
simulation_service = SimulationService()

