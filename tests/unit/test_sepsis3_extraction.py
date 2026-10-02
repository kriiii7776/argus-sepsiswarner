import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "data" / "02_sepsis3_extraction.py"
SPEC = importlib.util.spec_from_file_location("argus_sepsis3_extraction", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class _Catalog:
    def __init__(self, present=True):
        self.present = present

    def tableExists(self, name):
        return self.present


class _Frame:
    columns = sorted(MODULE.REQUIRED_COLUMNS)

    def __init__(self):
        self.selected = None

    def select(self, *columns):
        self.selected = columns
        return self


class _Spark:
    def __init__(self, present=True, frame=None):
        self.catalog = _Catalog(present)
        self.frame = frame or _Frame()

    def table(self, name):
        return self.frame


def test_requires_upstream_official_derived_relation():
    with pytest.raises(RuntimeError, match="Raw-table fallback is disabled"):
        MODULE.extract_sepsis3_cohort(_Spark(present=False))


def test_rejects_untrusted_relation_names():
    with pytest.raises(ValueError, match="Invalid derived relation"):
        MODULE.extract_sepsis3_cohort(_Spark(), "sepsis3; DROP TABLE patients")


def test_selects_required_official_event_fields():
    frame = _Frame()
    result = MODULE.extract_sepsis3_cohort(_Spark(frame=frame))
    assert result is frame
    assert set(frame.selected) == MODULE.REQUIRED_COLUMNS
