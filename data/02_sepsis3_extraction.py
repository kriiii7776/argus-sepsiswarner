"""Read the official MIMIC-IV derived Sepsis-3 event relation.

The former prototype computed a one-component MAP score (only 0 or 1) and
compared it with a threshold of 2, while also using an incomplete antibiotic
join. That cannot implement Sepsis-3. This module now fails closed unless the
MIT-LCP MIMIC-Code `mimiciv_derived.sepsis3` concept has been built for the
source database. It deliberately does not substitute a simplified label.

The upstream concept uses suspected infection and the full six-component
SOFA score, evaluates SOFA in the 48-hours-before to 24-hours-after infection
window, and records the first qualifying event per ICU stay. See:
https://github.com/MIT-LCP/mimic-code/tree/main/mimic-iv/concepts
"""
from __future__ import annotations

import re
from typing import Any


DEFAULT_TABLE = "mimiciv_derived.sepsis3"
REQUIRED_COLUMNS = {
    "subject_id",
    "stay_id",
    "suspected_infection_time",
    "sofa_time",
    "sofa_score",
    "sepsis3",
}
_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def extract_sepsis3_cohort(spark: Any, table_name: str = DEFAULT_TABLE):
    """Return validated official MIMIC-Code Sepsis-3 event rows.

    `spark` must already contain the output of the upstream MIMIC-Code
    suspicion-of-infection, SOFA, and Sepsis-3 concepts. A raw-table shortcut
    is intentionally not provided: the repository's simplified score was
    mathematically incapable of meeting its own label threshold.
    """
    if not _TABLE_NAME.fullmatch(table_name):
        raise ValueError(f"Invalid derived relation name: {table_name!r}")

    try:
        exists = spark.catalog.tableExists(table_name)
    except Exception as exc:
        raise RuntimeError(
            "Spark catalog is unavailable; load the MIMIC-Code derived "
            "Sepsis-3 relation before extracting labels."
        ) from exc
    if not exists:
        raise RuntimeError(
            f"Required relation {table_name!r} is absent. Build the official "
            "MIT-LCP MIMIC-Code suspicion_of_infection, sofa, and sepsis3 "
            "concepts for this MIMIC-IV release first. Raw-table fallback is "
            "disabled because it would create unvalidated labels."
        )

    events = spark.table(table_name)
    missing = REQUIRED_COLUMNS - set(events.columns)
    if missing:
        raise ValueError(
            f"{table_name!r} is not a compatible official Sepsis-3 relation; "
            f"missing columns: {sorted(missing)}"
        )
    return events.select(*sorted(REQUIRED_COLUMNS))


if __name__ == "__main__":
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("Argus-Official-Sepsis3-Import").getOrCreate()
    try:
        labels = extract_sepsis3_cohort(spark)
        labels.show(5, truncate=False)
        print(f"Loaded {labels.count()} official Sepsis-3 event rows.")
    except Exception as exc:
        raise SystemExit(f"Sepsis-3 extraction stopped safely: {exc}") from exc
