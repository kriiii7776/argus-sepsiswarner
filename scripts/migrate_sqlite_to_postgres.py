"""One-time, guarded migration for the ARGUS Part 2 SQLAlchemy tables.

Default behavior is a read-only preflight. Use --apply only after the source
service is stopped, a verified SQLite backup exists, and target tables are
empty. Existing PostgreSQL rows are never replaced or deleted.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    inspect,
    select,
    text,
)


metadata = MetaData()
patients = Table(
    "patients", metadata,
    Column("id", Integer, primary_key=True),
    Column("patient_id", String(64), nullable=False, index=True),
    Column("source_system", String(32), nullable=False),
    Column("sex_at_birth", String(16)),
    Column("birth_year", Integer),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
vital_events = Table(
    "vital_events", metadata,
    Column("id", Integer, primary_key=True),
    Column("patient_id", String(64), nullable=False, index=True),
    Column("session_id", String(128)),
    Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("source", String(24), nullable=False),
)
predictions = Table(
    "predictions", metadata,
    Column("id", Integer, primary_key=True),
    Column("patient_id", String(64), nullable=False, index=True),
    Column("session_id", String(128)),
    Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
    Column("risk", Float, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("model_version", String(64), nullable=False),
)
alerts = Table(
    "alerts", metadata,
    Column("id", Integer, primary_key=True),
    Column("patient_id", String(64), nullable=False, index=True),
    Column("session_id", String(128)),
    Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
    Column("severity", String(32), nullable=False),
    Column("payload", JSON, nullable=False),
)
TABLES = (patients, vital_events, predictions, alerts)


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    # SQLite's SQLAlchemy DateTime serialization drops tzinfo; ARGUS writes UTC.
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def _rows(source: sqlite3.Connection, table: Table) -> list[dict[str, Any]]:
    rows = [dict(row) for row in source.execute(f'SELECT * FROM "{table.name}" ORDER BY id')]
    for row in rows:
        if table.name == "patients":
            row["created_at"] = _datetime(row["created_at"])
        else:
            row["timestamp"] = _datetime(row["timestamp"])
            row["payload"] = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
            row["session_id"] = row.get("session_id") or row["payload"].get("session_id")
    return rows


def _utc_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return value


def _verify_target(connection, source_rows: dict[str, list[dict[str, Any]]], counts: dict[str, int]) -> None:
    actual_counts = {
        table.name: connection.execute(text(f'SELECT count(*) FROM "{table.name}"')).scalar_one()
        for table in TABLES
    }
    if actual_counts != counts:
        raise RuntimeError(f"PostgreSQL row counts differ; source={counts}, target={actual_counts}")
    for table in TABLES:
        actual_rows = [dict(row._mapping) for row in connection.execute(select(table).order_by(table.c.id))]
        expected_rows = source_rows[table.name]
        if len(actual_rows) != len(expected_rows):
            raise RuntimeError(f"{table.name} row count changed during content verification")
        for index, (expected, actual_row) in enumerate(zip(expected_rows, actual_rows)):
            for column in table.columns:
                field = column.name
                if _utc_value(expected.get(field)) != _utc_value(actual_row.get(field)):
                    raise RuntimeError(f"{table.name} content mismatch at row {index}, field {field}")


def migrate(source_path: Path, target_url: str, apply: bool, verify_only: bool = False) -> dict[str, int]:
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite backup does not exist: {source_path}")
    source = sqlite3.connect(f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    source_names = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected_names = {table.name for table in TABLES}
    if not expected_names.issubset(source_names):
        raise RuntimeError(f"SQLite backup is missing tables: {sorted(expected_names - source_names)}")
    source_rows = {table.name: _rows(source, table) for table in TABLES}
    counts = {name: len(rows) for name, rows in source_rows.items()}

    target = create_engine(target_url, pool_pre_ping=True)
    try:
        with target.connect() as connection:
            # No table is created or changed during a dry run.
            present = set(inspect(connection).get_table_names())
            if verify_only:
                missing = {table.name for table in TABLES} - present
                if missing:
                    raise RuntimeError(f"PostgreSQL target missing migrated tables: {sorted(missing)}")
                _verify_target(connection, source_rows, counts)
                return counts
            occupied = {}
            for table in TABLES:
                if table.name in present:
                    occupied[table.name] = connection.execute(
                        select(table.c.id).limit(1)
                    ).first() is not None
            if any(occupied.values()):
                raise RuntimeError(
                    "Refusing migration because target contains rows: "
                    + ", ".join(name for name, has_rows in occupied.items() if has_rows)
                )
            if not apply:
                return counts

        metadata.create_all(target)
        with target.begin() as connection:
            for table in TABLES:
                # Add session traceability to older, empty target schemas.
                current_columns = {c["name"] for c in inspect(connection).get_columns(table.name)}
                if "session_id" in table.c and "session_id" not in current_columns:
                    connection.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN session_id VARCHAR(128)'))
                rows = source_rows[table.name]
                for offset in range(0, len(rows), 1000):
                    connection.execute(insert(table), rows[offset:offset + 1000])
            for table in TABLES:
                if "session_id" in table.c:
                    connection.execute(text(
                        f'CREATE INDEX IF NOT EXISTS ix_{table.name}_session_id ON "{table.name}" (session_id)'
                    ))
                seq = connection.execute(
                    text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
                    {"table_name": table.name},
                ).scalar_one_or_none()
                max_id = connection.execute(select(table.c.id).order_by(table.c.id.desc()).limit(1)).scalar_one_or_none()
                if seq and max_id is not None:
                    connection.execute(text("SELECT setval(:sequence_name, :max_id, true)"),
                                       {"sequence_name": seq, "max_id": max_id})
        with target.connect() as connection:
            _verify_target(connection, source_rows, counts)
        return counts
    finally:
        source.close()
        target.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sqlite_backup", type=Path)
    parser.add_argument("--target-url", default=os.getenv("ARGUS_MIGRATION_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Apply after a verified backup and target preflight")
    parser.add_argument("--verify-only", action="store_true", help="Compare all rows against an already migrated target")
    args = parser.parse_args()
    if not args.target_url:
        parser.error("set ARGUS_MIGRATION_DATABASE_URL or pass --target-url")
    result = migrate(args.sqlite_backup, args.target_url, args.apply, args.verify_only)
    mode = "Verified source-to-PostgreSQL rows" if args.verify_only else ("Migrated" if args.apply else "Preflight source row counts")
    print(mode + ": " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
