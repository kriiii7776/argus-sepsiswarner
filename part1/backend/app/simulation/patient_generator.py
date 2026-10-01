"""
Patient Baseline Generator and Factory.

Generates physiologically plausible patient baselines deterministically based on seed and profile type.
"""

from typing import Optional
import numpy as np

from app.schemas.patient import (
    Patient,
    PatientBaseline,
    PatientProfileType,
    PatientSex,
    PatientStatus,
)


PROFILE_DISTRIBUTIONS = {
    PatientProfileType.STANDARD: {
        "hr": (72.0, 5.0, 60.0, 85.0),
        "sys": (120.0, 5.0, 110.0, 130.0),
        "dia": (80.0, 4.0, 70.0, 85.0),
        "spo2": (98.0, 0.8, 96.0, 100.0),
        "temp": (36.8, 0.2, 36.5, 37.3),
        "rr": (15.0, 1.5, 12.0, 18.0),
    },
    PatientProfileType.ATHLETIC: {
        "hr": (52.0, 4.0, 42.0, 60.0),
        "sys": (112.0, 5.0, 100.0, 122.0),
        "dia": (72.0, 4.0, 65.0, 80.0),
        "spo2": (99.0, 0.5, 97.0, 100.0),
        "temp": (36.6, 0.2, 36.2, 37.0),
        "rr": (13.0, 1.5, 10.0, 16.0),
    },
    PatientProfileType.GERIATRIC: {
        "hr": (76.0, 6.0, 65.0, 88.0),
        "sys": (134.0, 7.0, 120.0, 148.0),
        "dia": (82.0, 5.0, 75.0, 90.0),
        "spo2": (95.5, 1.0, 94.0, 98.0),
        "temp": (36.5, 0.2, 36.0, 37.0),
        "rr": (18.0, 2.0, 14.0, 22.0),
    },
    PatientProfileType.HYPERTENSIVE: {
        "hr": (80.0, 5.0, 70.0, 92.0),
        "sys": (152.0, 8.0, 140.0, 170.0),
        "dia": (96.0, 4.0, 90.0, 105.0),
        "spo2": (97.0, 1.0, 95.0, 99.0),
        "temp": (36.9, 0.2, 36.5, 37.3),
        "rr": (17.0, 2.0, 14.0, 20.0),
    },
    PatientProfileType.ICU_BASELINE: {
        "hr": (88.0, 7.0, 75.0, 105.0),
        "sys": (112.0, 8.0, 95.0, 128.0),
        "dia": (68.0, 5.0, 60.0, 80.0),
        "spo2": (94.5, 1.5, 91.0, 97.0),
        "temp": (37.2, 0.3, 36.6, 38.0),
        "rr": (20.0, 2.5, 16.0, 26.0),
    },
}


class PatientFactory:
    """
    Factory for producing synthetic ICU patients with individual baselines.
    """

    @staticmethod
    def create_baseline(
        profile_type: PatientProfileType = PatientProfileType.STANDARD,
        seed: Optional[int] = None,
    ) -> PatientBaseline:
        rng = np.random.default_rng(seed)
        dist = PROFILE_DISTRIBUTIONS[profile_type]

        def draw(mean: float, std: float, min_val: float, max_val: float) -> float:
            val = rng.normal(mean, std)
            return float(np.clip(val, min_val, max_val))

        hr = round(draw(*dist["hr"]), 1)
        sys_bp = round(draw(*dist["sys"]), 1)
        dia_bp = round(draw(*dist["dia"]), 1)
        spo2 = round(draw(*dist["spo2"]), 1)
        temp = round(draw(*dist["temp"]), 2)
        rr = round(draw(*dist["rr"]), 1)

        # Enforce physical rule: diastolic < systolic
        if dia_bp >= sys_bp:
            dia_bp = round(sys_bp - 15.0, 1)

        return PatientBaseline(
            heart_rate=hr,
            systolic_bp=sys_bp,
            diastolic_bp=dia_bp,
            spo2=spo2,
            temperature=temp,
            respiratory_rate=rr,
        )

    @classmethod
    def create_patient(
        cls,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        age: Optional[int] = None,
        sex: Optional[PatientSex] = None,
        profile_type: PatientProfileType = PatientProfileType.STANDARD,
        status: PatientStatus = PatientStatus.ACTIVE,
        seed: Optional[int] = None,
    ) -> Patient:
        rng = np.random.default_rng(seed)

        if age is None:
            if profile_type == PatientProfileType.GERIATRIC:
                age = int(rng.integers(65, 88))
            elif profile_type == PatientProfileType.ATHLETIC:
                age = int(rng.integers(20, 40))
            else:
                age = int(rng.integers(25, 75))

        if sex is None:
            sex = PatientSex.MALE if rng.random() > 0.5 else PatientSex.FEMALE

        baseline = cls.create_baseline(profile_type=profile_type, seed=seed)

        kwargs = {
            "age": age,
            "sex": sex,
            "profile_type": profile_type,
            "status": status,
            "baseline": baseline,
        }
        if patient_id is not None:
            kwargs["patient_id"] = patient_id
        if session_id is not None:
            kwargs["session_id"] = session_id

        return Patient(**kwargs)
