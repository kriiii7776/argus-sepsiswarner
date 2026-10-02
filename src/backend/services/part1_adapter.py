"""
Part 1 Simulator to Part 2 Clinical Intelligence Contract Adapter.

Converts Part 1 contract v1.0 JSON payloads (vital_update messages)
into Part 2 VitalEvent instances, mapping simulation_time to Part 2 clinical timestamps
and preserving patient identity, data quality, and session metadata without importing Part 1 code.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from src.backend.schemas.schemas import VitalEvent, PredictionResponse
from src.backend.services.inference_service import InferenceService

log = logging.getLogger("sepsisguard.part1_adapter")


class Part1Adapter:
    """
    Contract Adapter converting Part 1 Simulator contract v1.0 payloads into canonical Part 2 VitalEvents.
    """

    @staticmethod
    def parse_timestamp(sim_time_str: str) -> datetime:
        """
        Parses simulation_time string to UTC datetime object for Part 2 clinical timeline processing.
        """
        if not sim_time_str:
            return datetime.now(timezone.utc)
        
        sim_time_str = sim_time_str.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(sim_time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            log.warning("Invalid simulation_time format '%s'; falling back to UTC now.", sim_time_str)
            return datetime.now(timezone.utc)

    @classmethod
    def transform_vital_update(cls, payload: Dict[str, Any]) -> VitalEvent:
        """
        Transforms Part 1 vital_update contract v1.0 message into Part 2 VitalEvent.
        """
        msg_type = payload.get("message_type")
        if msg_type != "vital_update":
            raise ValueError(f"Unsupported Part 1 message type '{msg_type}'. Only 'vital_update' is supported.")

        patient_id = payload.get("patient_id")
        if not patient_id:
            raise ValueError("Part 1 payload missing mandatory 'patient_id' field.")

        sim_time_str = payload.get("simulation_time") or payload.get("timestamp") or ""
        clinical_ts = cls.parse_timestamp(sim_time_str)

        vitals = payload.get("vitals") or {}
        hr = vitals.get("heart_rate")
        sbp = vitals.get("systolic_bp")
        dbp = vitals.get("diastolic_bp")
        spo2 = vitals.get("spo2")
        temp = vitals.get("temperature")
        rr = vitals.get("respiratory_rate")

        # Mean Arterial Pressure (MAP) derivation from SBP/DBP
        calculated_map: Optional[float] = vitals.get("map")
        if calculated_map is None and sbp is not None and dbp is not None:
            try:
                calculated_map = float(dbp) + (float(sbp) - float(dbp)) / 3.0
            except (TypeError, ValueError):
                calculated_map = None

        return VitalEvent(
            patient_id=str(patient_id),
            session_id=str(payload['session_id']) if payload.get('session_id') else None,
            timestamp=clinical_ts,
            heart_rate=float(hr) if hr is not None else None,
            map=float(calculated_map) if calculated_map is not None else None,
            resp_rate=float(rr) if rr is not None else None,
            spo2=float(spo2) if spo2 is not None else None,
            temperature_c=float(temp) if temp is not None else None,
            source='simulator'
        )

    @classmethod
    async def process_part1_message(cls, payload: Dict[str, Any]) -> PredictionResponse:
        """
        Processes a Part 1 message through the contract transformation and Part 2 inference runtime.
        """
        event = cls.transform_vital_update(payload)
        return await InferenceService.ingest(event)
