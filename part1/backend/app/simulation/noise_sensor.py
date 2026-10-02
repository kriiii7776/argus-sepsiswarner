"""
Data Quality and Sensor Failure Simulation Subsystem.

Injects per-vital sensor faults (disconnections, missingness, staleness, artifacts, sudden jumps)
and generates contract-compliant QualityMetadata and SensorEventMessage objects without hidden imputation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.schemas.contract import (
    QualityStatus,
    SensorEventMessage,
    VitalSignSet,
    VitalUpdateMessage,
)


class SensorState(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class PerVitalQuality(BaseModel):
    heart_rate: QualityStatus = QualityStatus.VALID
    systolic_bp: QualityStatus = QualityStatus.VALID
    diastolic_bp: QualityStatus = QualityStatus.VALID
    spo2: QualityStatus = QualityStatus.VALID
    temperature: QualityStatus = QualityStatus.VALID
    respiratory_rate: QualityStatus = QualityStatus.VALID


class DataQualityEngine:
    """
    Per-vital Sensor Fault and Data Quality Engine.
    Tracks individual sensor leads and applies explicit quality conditions without imputing missing values.
    """

    VITAL_NAMES = [
        "heart_rate",
        "systolic_bp",
        "diastolic_bp",
        "spo2",
        "temperature",
        "respiratory_rate",
    ]

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

        # Per-vital sensor operational states
        self.sensor_states: Dict[str, SensorState] = {
            v: SensorState.CONNECTED for v in self.VITAL_NAMES
        }
        self.vital_quality: Dict[str, QualityStatus] = {
            v: QualityStatus.VALID for v in self.VITAL_NAMES
        }

        # Cached values for staleness simulation
        self._stale_cache: Dict[str, Optional[float]] = {v: None for v in self.VITAL_NAMES}

        # Fault override configurations per vital
        self._fault_overrides: Dict[str, Optional[QualityStatus]] = {
            v: None for v in self.VITAL_NAMES
        }

    def set_vital_fault(self, vital_name: str, quality: QualityStatus) -> None:
        """
        Manually injects a specific fault state for a given vital sensor.
        """
        if vital_name not in self.VITAL_NAMES:
            raise ValueError(f"Unknown vital sign '{vital_name}'")
        self._fault_overrides[vital_name] = quality

        if quality in (QualityStatus.DISCONNECTED, QualityStatus.SENSOR_UNAVAILABLE):
            self.sensor_states[vital_name] = SensorState.DISCONNECTED
        elif quality == QualityStatus.STALE:
            self.sensor_states[vital_name] = SensorState.STALE
        else:
            self.sensor_states[vital_name] = SensorState.CONNECTED

    def clear_vital_fault(self, vital_name: str) -> None:
        """
        Clears manual fault override for a vital sensor.
        """
        if vital_name in self.VITAL_NAMES:
            self._fault_overrides[vital_name] = None
            self.sensor_states[vital_name] = SensorState.CONNECTED
            self.vital_quality[vital_name] = QualityStatus.VALID

    def inject_sensor_event(
        self,
        patient_id: str,
        session_id: str,
        vital_name: str,
        new_status: QualityStatus,
        simulation_time: datetime,
        wall_timestamp: Optional[datetime] = None,
        details: Optional[str] = None,
    ) -> Tuple[SensorEventMessage, QualityStatus]:
        """
        Triggers a sensor state transition event (e.g. Lead Disconnected / Reconnected)
        and constructs a contract-compliant SensorEventMessage.
        """
        if wall_timestamp is None:
            wall_timestamp = datetime.now(timezone.utc)

        prev_status = self.vital_quality.get(vital_name, QualityStatus.VALID)
        self.set_vital_fault(vital_name, new_status)
        self.vital_quality[vital_name] = new_status

        event_msg = SensorEventMessage(
            schema_version="1.0",
            message_type="sensor_event",
            patient_id=patient_id,
            session_id=session_id,
            source="synthetic",
            timestamp=wall_timestamp,
            simulation_time=simulation_time,
            sensor_type=f"{vital_name}_sensor",
            event_type=new_status.value,
            details=details or f"Sensor {vital_name} transitioned from {prev_status.value} to {new_status.value}",
        )
        return event_msg, new_status

    def process(
        self,
        msg: VitalUpdateMessage,
        stale_vitals: Optional[List[str]] = None,
        jump_vitals: Optional[Dict[str, float]] = None,
    ) -> VitalUpdateMessage:
        """
        Processes a VitalUpdateMessage payload, applying per-vital fault states,
        stale caching, out-of-bounds artifact injection, or null missingness without imputation.
        """
        vitals_dict = msg.vitals.model_dump()
        stale_list = stale_vitals or []
        jumps = jump_vitals or {}

        overall_quality = msg.quality_status

        for v in self.VITAL_NAMES:
            status = self._fault_overrides[v] or self.vital_quality[v]

            if status in (QualityStatus.DISCONNECTED, QualityStatus.SENSOR_UNAVAILABLE, QualityStatus.MISSING):
                # Explicit missing representation - NO IMPUTATION
                vitals_dict[v] = None
                self.vital_quality[v] = status
                overall_quality = status

            elif status == QualityStatus.INVALID:
                # Out-of-bounds unphysiological artifact
                if v == "heart_rate":
                    vitals_dict[v] = 295.0
                elif v == "spo2":
                    vitals_dict[v] = 12.0
                elif v == "temperature":
                    vitals_dict[v] = 18.5
                self.vital_quality[v] = QualityStatus.INVALID
                overall_quality = QualityStatus.INVALID

            elif status == QualityStatus.STALE or v in stale_list:
                # Retain cached value from previous tick
                if self._stale_cache[v] is not None:
                    vitals_dict[v] = self._stale_cache[v]
                self.vital_quality[v] = QualityStatus.STALE
                if overall_quality == QualityStatus.VALID:
                    overall_quality = QualityStatus.STALE

            elif status == QualityStatus.DELAYED:
                self.vital_quality[v] = QualityStatus.DELAYED
                if overall_quality == QualityStatus.VALID:
                    overall_quality = QualityStatus.DELAYED

            else:
                # Valid reading - apply any sudden artifact jumps
                if v in jumps and vitals_dict[v] is not None:
                    vitals_dict[v] = round(vitals_dict[v] + jumps[v], 1)
                self.vital_quality[v] = QualityStatus.VALID
                # Cache valid value for future staleness calls
                if vitals_dict[v] is not None:
                    self._stale_cache[v] = vitals_dict[v]

        updated_vitals = VitalSignSet(**vitals_dict)
        return msg.model_copy(
            update={
                "vitals": updated_vitals,
                "quality_status": overall_quality,
            }
        )
