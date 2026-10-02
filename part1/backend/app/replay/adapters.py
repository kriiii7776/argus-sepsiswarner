"""
Replay Adapters and Data Normalizer for ARGUS Part 1.

Converts CSV, JSON, and MIMIC-IV raw dataset records into the frozen ARGUS v1.0 standard data contract.
"""

from abc import ABC, abstractmethod
import csv
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import pandas as pd

from app.schemas.contract import (
    DataSource,
    QualityStatus,
    ScenarioState,
    VitalSignSet,
    VitalUnits,
    VitalUpdateMessage,
)


class DataNormalizer:
    """
    Normalizes raw source column names and unit representations to the standard ARGUS vitals contract.
    """

    COLUMN_MAPPINGS = {
        "heart_rate": ["heart_rate", "hr", "heartrate", "bpm"],
        "systolic_bp": ["systolic_bp", "sys_bp", "sbp", "nibp_sys", "abp_sys"],
        "diastolic_bp": ["diastolic_bp", "dia_bp", "dbp", "nibp_dia", "abp_dia"],
        "spo2": ["spo2", "spo2_pct", "o2_sat", "oximetry"],
        "temperature": ["temperature", "temp", "temp_c", "body_temp"],
        "respiratory_rate": ["respiratory_rate", "resp_rate", "rr", "resprate"],
    }

    @classmethod
    def normalize_record(
        self,
        raw: Dict[str, Any],
        patient_id: str,
        session_id: str,
        source: DataSource = DataSource.CSV_REPLAY,
        wall_timestamp: Optional[datetime] = None,
    ) -> VitalUpdateMessage:
        if wall_timestamp is None:
            wall_timestamp = datetime.now(timezone.utc)

        # 1. Parse Simulation Timestamp
        sim_time_raw = raw.get("simulation_time") or raw.get("timestamp") or raw.get("charttime")
        if isinstance(sim_time_raw, datetime):
            sim_time = sim_time_raw
        elif sim_time_raw:
            sim_time = pd.to_datetime(sim_time_raw).to_pydatetime()
        else:
            sim_time = wall_timestamp

        if sim_time.tzinfo is None:
            sim_time = sim_time.replace(tzinfo=timezone.utc)
        else:
            sim_time = sim_time.astimezone(timezone.utc)

        # 2. Extract and Normalize Vitals
        vitals = {}
        for vital_key, aliases in self.COLUMN_MAPPINGS.items():
            val = None
            for alias in aliases:
                if alias in raw and raw[alias] is not None and str(raw[alias]).strip() != "":
                    try:
                        val = float(raw[alias])
                        break
                    except (ValueError, TypeError):
                        pass
            vitals[vital_key] = val

        # Temperature Unit Normalization (°F -> °C if > 50)
        if vitals.get("temperature") is not None and vitals["temperature"] > 50.0:
            vitals["temperature"] = round((vitals["temperature"] - 32.0) * (5.0 / 9.0), 2)

        # 3. Quality Status & Scenario Metadata Extraction
        quality_str = str(raw.get("quality_status", "valid")).lower()
        try:
            quality_status = QualityStatus(quality_str)
        except ValueError:
            quality_status = QualityStatus.VALID

        scenario_str = str(raw.get("scenario_state", "stable")).lower()
        try:
            scenario_state = ScenarioState(scenario_str)
        except ValueError:
            scenario_state = ScenarioState.STABLE

        vital_set = VitalSignSet(**vitals)

        return VitalUpdateMessage(
            schema_version="1.0",
            message_type="vital_update",
            patient_id=raw.get("patient_id") or patient_id,
            session_id=raw.get("session_id") or session_id,
            source=source,
            timestamp=wall_timestamp,
            simulation_time=sim_time,
            vitals=vital_set,
            vital_units=VitalUnits(),
            quality_status=quality_status,
            scenario_state=scenario_state,
        )


class ReplayAdapter(ABC):
    """
    Abstract Replay Adapter Interface.
    """

    @abstractmethod
    def load_records(self, file_path_or_data: Any) -> List[Dict[str, Any]]:
        pass


class CSVReplayAdapter(ReplayAdapter):
    """
    Concrete adapter for loading and parsing CSV dataset files.
    """

    def load_records(self, file_path_or_data: Any) -> List[Dict[str, Any]]:
        records = []
        if isinstance(file_path_or_data, str):
            with open(file_path_or_data, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
        elif hasattr(file_path_or_data, "read"):
            reader = csv.DictReader(file_path_or_data)
            for row in reader:
                records.append(row)
        return records


class JSONReplayAdapter(ReplayAdapter):
    """
    Concrete adapter for loading JSON and JSONL datasets.
    """

    def load_records(self, file_path_or_data: Any) -> List[Dict[str, Any]]:
        records = []
        if isinstance(file_path_or_data, list):
            return file_path_or_data
        elif isinstance(file_path_or_data, str):
            s = file_path_or_data.strip()
            if s.startswith("[") or s.startswith("{"):
                if s.startswith("["):
                    records = json.loads(s)
                else:
                    for line in s.splitlines():
                        if line.strip():
                            records.append(json.loads(line))
                return records
            else:
                with open(file_path_or_data, mode="r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content.startswith("["):
                        records = json.loads(content)
                    else:
                        for line in content.splitlines():
                            if line.strip():
                                records.append(json.loads(line))
        elif hasattr(file_path_or_data, "read"):
            content = file_path_or_data.read().strip()
            if content.startswith("["):
                records = json.loads(content)
            else:
                for line in content.splitlines():
                    if line.strip():
                        records.append(json.loads(line))
        return records


class MIMICIVReplayAdapter(ReplayAdapter):
    """
    Concrete adapter for MIMIC-IV Clinical Demo / derived concept tables (chartevents/derived vitals).
    Maps MIMIC-IV itemids/concepts (e.g. 220045 -> HR, 220179 -> SBP, 220180 -> DBP, 220277 -> SpO2)
    into standard normalized dictionary structures.
    """

    MIMIC_ITEMID_MAP = {
        220045: "heart_rate",
        220179: "systolic_bp",
        220180: "diastolic_bp",
        220277: "spo2",
        223761: "temperature",  # °F
        223762: "temperature",  # °C
        220210: "respiratory_rate",
    }

    def load_records(self, file_path_or_df: Any) -> List[Dict[str, Any]]:
        if isinstance(file_path_or_df, str):
            df = pd.read_csv(file_path_or_df)
        elif isinstance(file_path_or_df, pd.DataFrame):
            df = file_path_or_df
        else:
            df = pd.DataFrame(file_path_or_df)

        # Check if already pivoted with standard column names or MIMIC chartevents layout
        if "itemid" in df.columns and "valuenum" in df.columns:
            pivoted = df.pivot_table(
                index=["stay_id", "charttime"],
                columns="itemid",
                values="valuenum",
                aggfunc="first",
            ).reset_index()

            records = []
            for _, row in pivoted.iterrows():
                rec = {
                    "patient_id": f"P-MIMIC-{int(row['stay_id'])}",
                    "simulation_time": str(row["charttime"]),
                }
                for itemid, target_col in self.MIMIC_ITEMID_MAP.items():
                    if itemid in row and pd.notna(row[itemid]):
                        rec[target_col] = float(row[itemid])
                records.append(rec)
            return records
        else:
            return df.to_dict(orient="records")
