"""Replay recorded MIMIC-IV Demo observations without fabricating measurements.

The public demo is charted EHR data, not a second-by-second bedside waveform.
This provider emits a monitor tick every second for integration testing, retains
the latest *recorded* observation, and marks it stale after five simulated minutes.
It never interpolates a clinical value or fills a missing measurement.
"""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from app.schemas.contract import (
    ClinicalContext, ClinicalContextUnits, ClinicalUpdateMessage, DataSource,
    QualityStatus, ScenarioState, VitalSignSet, VitalUnits, VitalUpdateMessage,
)
from app.schemas.patient import Patient, PatientBaseline, PatientProfileType


VITAL_ITEM_IDS = {220045: "heart_rate", 220179: "systolic_bp", 220180: "diastolic_bp", 220277: "spo2", 220210: "respiratory_rate", 223761: "temperature", 223762: "temperature"}
LAB_ITEM_IDS = {51265: "platelets", 50885: "bilirubin", 50912: "creatinine", 50813: "lactate"}
PAO2_ITEM_ID = 50821
FIO2_ITEM_ID = 223835
# MIMIC chart events store GCS components separately. Do not expose any one
# component as a total GCS score; use the official derived concept in a future
# import step. Until then the field remains unavailable rather than incorrect.
GCS_COMPONENT_ITEM_IDS = {220739, 223900, 223901}
NOREPINEPHRINE_ITEM_ID = 221906
URINE_ITEM_IDS = {226559, 226566, 226627, 226631}


@dataclass
class HistoricalPatient:
    patient: Patient
    start: datetime
    vitals: Dict[str, List[Tuple[datetime, float]]]
    clinical: Dict[str, List[Tuple[datetime, float]]]


class MIMICHistoricalReplay:
    """Loads a small cohort of real, de-identified MIMIC-IV Demo ICU stays."""

    # Cohort membership is presentation metadata only. It is deliberately not
    # included in telemetry messages, so a downstream model cannot leak the
    # expected outcome into its prediction.
    COHORT = {
        38197705: {"group": "sepsis_warning_candidate", "evidence": "culture/antimicrobial evidence plus 3 recorded organ-dysfunction markers"},
        34617352: {"group": "sepsis_warning_candidate", "evidence": "culture/antimicrobial evidence plus 4 recorded organ-dysfunction markers"},
        32359580: {"group": "sepsis_warning_candidate", "evidence": "culture/antimicrobial evidence plus 4 recorded organ-dysfunction markers"},
        31269608: {"group": "no_sepsis_warning_candidate", "evidence": "no preliminary infection-plus-two-organ-marker evidence; complete monitor replay"},
        37509585: {"group": "no_sepsis_warning_candidate", "evidence": "no preliminary infection-plus-two-organ-marker evidence; complete monitor replay"},
        32554129: {"group": "no_sepsis_warning_candidate", "evidence": "no preliminary infection-plus-two-organ-marker evidence; complete monitor replay"},
        31338022: {"group": "no_sepsis_warning_candidate", "evidence": "no preliminary infection-plus-two-organ-marker evidence; complete monitor replay"},
        30876334: {"group": "no_sepsis_warning_candidate", "evidence": "no preliminary infection-plus-two-organ-marker evidence; complete monitor replay"},
        35446858: {"group": "no_sepsis_warning_candidate", "evidence": "no preliminary infection-plus-two-organ-marker evidence; complete monitor replay"},
        36091287: {"group": "no_sepsis_warning_candidate", "evidence": "no preliminary infection-plus-two-organ-marker evidence; complete monitor replay"},
    }
    STAY_IDS = tuple(COHORT)
    STALE_AFTER_SECONDS = 300
    SIMULATION_SECONDS_PER_WALL_SECOND = 60

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or Path(__file__).resolve().parents[3] / "data" / "mimic-iv-demo"
        self._patients: Dict[str, HistoricalPatient] = {}

    def load(self) -> List[Patient]:
        if self._patients:
            return [entry.patient for entry in self._patients.values()]
        required = ["chartevents.csv.gz", "icustays.csv.gz", "labevents.csv.gz", "inputevents.csv.gz", "outputevents.csv.gz"]
        missing = [name for name in required if not (self.data_dir / name).exists()]
        if missing:
            raise FileNotFoundError(f"MIMIC-IV Demo files are missing: {', '.join(missing)}")

        stays = pd.read_csv(self.data_dir / "icustays.csv.gz").set_index("stay_id")
        # Preserve cohort order: the most complete warning replay is the
        # dashboard default, while all ten patients still stream to consumers.
        stays = stays.loc[list(self.STAY_IDS)].reset_index()
        chart = pd.read_csv(self.data_dir / "chartevents.csv.gz", usecols=["subject_id", "hadm_id", "stay_id", "charttime", "itemid", "valuenum"])
        labs = pd.read_csv(self.data_dir / "labevents.csv.gz", usecols=["hadm_id", "charttime", "itemid", "valuenum"])
        inputs = pd.read_csv(self.data_dir / "inputevents.csv.gz", usecols=["stay_id", "starttime", "itemid", "rate"])
        outputs = pd.read_csv(self.data_dir / "outputevents.csv.gz", usecols=["stay_id", "charttime", "itemid", "value"])

        for _, stay in stays.iterrows():
            stay_id, hadm_id = int(stay.stay_id), int(stay.hadm_id)
            vital_rows = chart[(chart.stay_id == stay_id) & chart.itemid.isin(VITAL_ITEM_IDS)].copy()
            vital_rows["charttime"] = pd.to_datetime(vital_rows["charttime"], utc=True)
            vital_rows = vital_rows.dropna(subset=["valuenum"]).sort_values("charttime")
            vitals: Dict[str, List[Tuple[datetime, float]]] = {field: [] for field in set(VITAL_ITEM_IDS.values())}
            for row in vital_rows.itertuples():
                field = VITAL_ITEM_IDS[int(row.itemid)]
                value = float(row.valuenum)
                if field == "temperature" and value > 50:
                    value = (value - 32) * 5 / 9
                vitals[field].append((row.charttime.to_pydatetime(), value))
            clinical = self._clinical_samples(labs, inputs, outputs, chart, stay_id, hadm_id)
            # Begin only once the recorded monitor fields and core laboratory
            # fields have each appeared at least once. This avoids showing a
            # misleading blank dashboard at the start of a historical replay.
            required = [*vitals.values(), clinical["platelets"], clinical["bilirubin"], clinical["creatinine"], clinical["lactate"]]
            start = max(samples[0][0] for samples in required if samples)
            # The UI's legacy baseline schema has conservative bounds. This
            # display-only baseline is clamped; emitted replay observations are
            # never changed or clamped.
            def display_baseline(field, default, low, high):
                value = self._value_at(vitals[field], start)[0] or default
                return min(high, max(low, value))
            baseline = PatientBaseline(
                heart_rate=display_baseline("heart_rate", 80, 40, 140),
                systolic_bp=display_baseline("systolic_bp", 120, 70, 200),
                diastolic_bp=display_baseline("diastolic_bp", 80, 40, 120),
                spo2=display_baseline("spo2", 95, 85, 100),
                temperature=display_baseline("temperature", 37, 35, 40),
                respiratory_rate=display_baseline("respiratory_rate", 16, 8, 35),
            )
            patient = Patient(patient_id=f"MIMIC-{stay_id}", session_id=f"MIMIC-{stay_id}", age=60,
                profile_type=PatientProfileType.ICU_BASELINE, baseline=baseline)
            self._patients[patient.patient_id] = HistoricalPatient(patient, start, vitals, clinical)
        return [entry.patient for entry in self._patients.values()]

    def cohort_manifest(self) -> List[Dict[str, str]]:
        """Presentation metadata; do not pass this to the inference pipeline."""
        return [
            {
                "patient_id": f"MIMIC-{stay_id}",
                "stay_id": str(stay_id),
                "expected_group": details["group"],
                "selection_evidence": details["evidence"],
                "label_scope": "retrospective demo cohort selection, not a clinical diagnosis",
            }
            for stay_id, details in self.COHORT.items()
        ]

    def vital_update(self, patient_id: str, elapsed_wall_ticks: int) -> VitalUpdateMessage:
        entry = self._patients[patient_id]
        sim_time = entry.start + timedelta(seconds=elapsed_wall_ticks * self.SIMULATION_SECONDS_PER_WALL_SECOND)
        values, ages = {}, []
        for field, samples in entry.vitals.items():
            value, observed = self._value_at(samples, sim_time)
            values[field] = round(value, 2) if value is not None else None
            if observed:
                ages.append((sim_time - observed).total_seconds())
        quality = QualityStatus.VALID if ages and max(ages) <= self.STALE_AFTER_SECONDS else QualityStatus.STALE
        return VitalUpdateMessage(patient_id=entry.patient.patient_id, session_id=entry.patient.session_id,
            source=DataSource.MIMIC_IV, timestamp=datetime.now(timezone.utc), simulation_time=sim_time,
            vitals=VitalSignSet(**values), vital_units=VitalUnits(), quality_status=quality, scenario_state=ScenarioState.STABLE)

    def clinical_update(self, patient_id: str, elapsed_wall_ticks: int) -> ClinicalUpdateMessage:
        entry = self._patients[patient_id]
        sim_time = entry.start + timedelta(seconds=elapsed_wall_ticks * self.SIMULATION_SECONDS_PER_WALL_SECOND)
        as_of_values = {field: self._value_at(samples, sim_time) for field, samples in entry.clinical.items()}
        values = {field: value for field, (value, _) in as_of_values.items()}
        observed_times = {field: observed for field, (_, observed) in as_of_values.items()}
        return ClinicalUpdateMessage(patient_id=entry.patient.patient_id, session_id=entry.patient.session_id,
            source=DataSource.MIMIC_IV, timestamp=datetime.now(timezone.utc), simulation_time=sim_time, recorded_at=sim_time,
            clinical_context=ClinicalContext(**values), clinical_units=ClinicalContextUnits(),
            clinical_observation_times=observed_times, data_origin="mimic_iv_demo_recorded_replay")

    @staticmethod
    def _value_at(samples: List[Tuple[datetime, float]], at: datetime) -> Tuple[Optional[float], Optional[datetime]]:
        if not samples:
            return None, None
        times = [time for time, _ in samples]
        index = bisect_right(times, at) - 1
        return (samples[index][1], times[index]) if index >= 0 else (None, None)

    def _clinical_samples(self, labs, inputs, outputs, chart, stay_id, hadm_id):
        clinical = {field: [] for field in [*LAB_ITEM_IDS.values(), "glasgow_coma_scale", "urine_output_6h", "norepinephrine_dose", "pao2_fio2_ratio"]}
        rows = labs[(labs.hadm_id == hadm_id) & labs.itemid.isin(LAB_ITEM_IDS)].dropna(subset=["valuenum"]).copy()
        rows["charttime"] = pd.to_datetime(rows.charttime, utc=True)
        for row in rows.itertuples(): clinical[LAB_ITEM_IDS[int(row.itemid)]].append((row.charttime.to_pydatetime(), float(row.valuenum)))
        # Derive total GCS only when all three correctly identified recorded
        # components (eye, verbal, motor) share a chart timestamp.
        gcs = chart[(chart.stay_id == stay_id) & chart.itemid.isin(GCS_COMPONENT_ITEM_IDS)].dropna(subset=["valuenum"]).copy()
        gcs["charttime"] = pd.to_datetime(gcs.charttime, utc=True)
        gcs_pivot = gcs.pivot_table(index="charttime", columns="itemid", values="valuenum", aggfunc="first")
        if GCS_COMPONENT_ITEM_IDS.issubset(gcs_pivot.columns):
            totals = gcs_pivot.dropna(subset=list(GCS_COMPONENT_ITEM_IDS)).sum(axis=1)
            clinical["glasgow_coma_scale"] = [(time.to_pydatetime(), float(value)) for time, value in totals.items()]

        # Derive PaO2/FiO2 from recorded arterial PaO2 and the most recent
        # recorded inspired oxygen fraction no more than four hours earlier.
        pao2 = labs[(labs.hadm_id == hadm_id) & (labs.itemid == PAO2_ITEM_ID)].dropna(subset=["valuenum"]).copy()
        pao2["charttime"] = pd.to_datetime(pao2.charttime, utc=True)
        fio2 = chart[(chart.stay_id == stay_id) & (chart.itemid == FIO2_ITEM_ID)].dropna(subset=["valuenum"]).copy()
        fio2["charttime"] = pd.to_datetime(fio2.charttime, utc=True)
        fio2_samples = sorted((row.charttime.to_pydatetime(), float(row.valuenum) / 100 if float(row.valuenum) > 1 else float(row.valuenum)) for row in fio2.itertuples())
        for row in pao2.itertuples():
            observed_at = row.charttime.to_pydatetime()
            fraction, fio2_time = self._value_at(fio2_samples, observed_at)
            if fraction and observed_at - fio2_time <= timedelta(hours=4):
                clinical["pao2_fio2_ratio"].append((observed_at, float(row.valuenum) / fraction))
        norepi = inputs[(inputs.stay_id == stay_id) & (inputs.itemid == NOREPINEPHRINE_ITEM_ID)].dropna(subset=["rate"]).copy()
        norepi["starttime"] = pd.to_datetime(norepi.starttime, utc=True)
        clinical["norepinephrine_dose"] = [(row.starttime.to_pydatetime(), float(row.rate)) for row in norepi.itertuples()]
        urine = outputs[(outputs.stay_id == stay_id) & outputs.itemid.isin(URINE_ITEM_IDS)].dropna(subset=["value"]).copy()
        urine["charttime"] = pd.to_datetime(urine.charttime, utc=True)
        urine_samples = sorted((row.charttime.to_pydatetime(), float(row.value)) for row in urine.itertuples())
        clinical["urine_output_6h"] = [
            (time, sum(value for earlier_time, value in urine_samples if time - timedelta(hours=6) <= earlier_time <= time))
            for time, _ in urine_samples
        ]
        return {field: sorted(samples) for field, samples in clinical.items()}
