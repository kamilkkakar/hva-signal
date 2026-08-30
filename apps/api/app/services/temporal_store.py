"""CANDIDATE SQLite zone-hour store. New file only.

Does not reuse analysis_jobs. Does not touch sqlite_job_store.py.
Default backend is in-memory. SQLite is opt-in via an explicit path.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

STORE_FEATURE_FLAG = "HVA_TEMPORAL_STORE_BACKEND"
STORE_SCHEMA_VERSION = "hva-signal-temporal-store-v1-candidate"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS temporal_store_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zone_hour (
    area_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    valid_time_utc TEXT NOT NULL,
    valid_time_local TEXT NOT NULL,
    timezone TEXT NOT NULL,
    temperature_c REAL,
    source_mode TEXT NOT NULL,
    source_family TEXT NOT NULL,
    temperature_quantity TEXT NOT NULL,
    sampling_design TEXT NOT NULL,
    zone_geometry_version TEXT NOT NULL,
    aggregation_spec_version TEXT NOT NULL,
    observation_kind TEXT NOT NULL,
    coverage_status TEXT NOT NULL,
    activity_id TEXT,
    PRIMARY KEY (
        area_id, zone_id, valid_time_utc, source_mode,
        temperature_quantity, zone_geometry_version, aggregation_spec_version
    )
);

CREATE INDEX IF NOT EXISTS idx_zone_hour_zone_time
    ON zone_hour (area_id, zone_id, valid_time_utc);
CREATE INDEX IF NOT EXISTS idx_zone_hour_aoi_time
    ON zone_hour (area_id, valid_time_utc);

CREATE TABLE IF NOT EXISTS daily_profile_summary (
    area_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    local_date TEXT NOT NULL,
    sampling_design TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    n_present INTEGER NOT NULL,
    n_expected INTEGER NOT NULL,
    coverage_class TEXT NOT NULL,
    min_c REAL,
    max_c REAL,
    PRIMARY KEY (area_id, zone_id, local_date, sampling_design, source_mode)
);

CREATE TABLE IF NOT EXISTS season_summary (
    area_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    window_id TEXT NOT NULL,
    sampling_design TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    availability TEXT NOT NULL,
    mean_c REAL,
    n_present INTEGER NOT NULL,
    n_expected INTEGER NOT NULL,
    coverage_class TEXT NOT NULL,
    PRIMARY KEY (area_id, zone_id, window_id, sampling_design, source_mode)
);

CREATE TABLE IF NOT EXISTS year_comparison_summary (
    area_id TEXT NOT NULL,
    zone_id TEXT,
    window_id TEXT NOT NULL,
    year_a INTEGER NOT NULL,
    year_b INTEGER NOT NULL,
    sampling_design TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    comparability TEXT NOT NULL,
    mean_difference_c REAL,
    pair_coverage_class TEXT NOT NULL,
    PRIMARY KEY (area_id, zone_id, window_id, year_a, year_b, sampling_design, source_mode)
);
"""


@dataclass(frozen=True)
class ZoneHourRow:
    area_id: str
    zone_id: str
    valid_time_utc: str
    valid_time_local: str
    timezone: str
    temperature_c: float | None
    source_mode: str
    source_family: str
    temperature_quantity: str
    sampling_design: str
    zone_geometry_version: str
    aggregation_spec_version: str
    observation_kind: str
    coverage_status: str
    activity_id: str | None = None


class TemporalStore:
    def put_zone_hour(self, row: ZoneHourRow) -> None:
        raise NotImplementedError

    def get_zone_hours(
        self,
        *,
        area_id: str,
        zone_id: str | None = None,
        start_utc: str | None = None,
        end_utc: str | None = None,
    ) -> list[ZoneHourRow]:
        raise NotImplementedError

    def put_season_summary(self, record: dict) -> None:
        raise NotImplementedError

    def get_season_summary(self, **key: object) -> dict | None:
        raise NotImplementedError


class InMemoryTemporalStore(TemporalStore):
    def __init__(self) -> None:
        self.zone_hours: dict[tuple, ZoneHourRow] = {}
        self.seasons: dict[tuple, dict] = {}
        self.daily: dict[tuple, dict] = {}
        self.yoy: dict[tuple, dict] = {}

    def put_zone_hour(self, row: ZoneHourRow) -> None:
        key = (
            row.area_id,
            row.zone_id,
            row.valid_time_utc,
            row.source_mode,
            row.temperature_quantity,
            row.zone_geometry_version,
            row.aggregation_spec_version,
        )
        self.zone_hours[key] = row

    def get_zone_hours(
        self,
        *,
        area_id: str,
        zone_id: str | None = None,
        start_utc: str | None = None,
        end_utc: str | None = None,
    ) -> list[ZoneHourRow]:
        rows = [row for row in self.zone_hours.values() if row.area_id == area_id]
        if zone_id is not None:
            rows = [row for row in rows if row.zone_id == zone_id]
        if start_utc is not None:
            rows = [row for row in rows if row.valid_time_utc >= start_utc]
        if end_utc is not None:
            rows = [row for row in rows if row.valid_time_utc <= end_utc]
        return sorted(rows, key=lambda row: (row.zone_id, row.valid_time_utc))

    def put_season_summary(self, record: dict) -> None:
        key = (
            record["area_id"],
            record["zone_id"],
            record["window_id"],
            record["sampling_design"],
            record["source_mode"],
        )
        self.seasons[key] = dict(record)

    def get_season_summary(self, **key: object) -> dict | None:
        lookup = (
            key["area_id"],
            key["zone_id"],
            key["window_id"],
            key["sampling_design"],
            key["source_mode"],
        )
        return self.seasons.get(lookup)


class SqliteTemporalStore(TemporalStore):
    """Typed zone-hour SQLite. Separate file from analysis_jobs."""

    def __init__(self, path: str) -> None:
        if path in {":memory:", ""}:
            self._conn = sqlite3.connect(":memory:")
        else:
            if "analysis_jobs" in path or path.endswith("jobs.sqlite"):
                raise ValueError("temporal store must not reuse the job-store file")
            self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        self._conn.execute(
            "INSERT OR REPLACE INTO temporal_store_meta(key, value) VALUES (?, ?)",
            ("schema_version", STORE_SCHEMA_VERSION),
        )
        self._conn.commit()

    def put_zone_hour(self, row: ZoneHourRow) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO zone_hour (
                area_id, zone_id, valid_time_utc, valid_time_local, timezone,
                temperature_c, source_mode, source_family, temperature_quantity,
                sampling_design, zone_geometry_version, aggregation_spec_version,
                observation_kind, coverage_status, activity_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.area_id,
                row.zone_id,
                row.valid_time_utc,
                row.valid_time_local,
                row.timezone,
                row.temperature_c,
                row.source_mode,
                row.source_family,
                row.temperature_quantity,
                row.sampling_design,
                row.zone_geometry_version,
                row.aggregation_spec_version,
                row.observation_kind,
                row.coverage_status,
                row.activity_id,
            ),
        )
        self._conn.commit()

    def get_zone_hours(
        self,
        *,
        area_id: str,
        zone_id: str | None = None,
        start_utc: str | None = None,
        end_utc: str | None = None,
    ) -> list[ZoneHourRow]:
        sql = "SELECT * FROM zone_hour WHERE area_id = ?"
        params: list[object] = [area_id]
        if zone_id is not None:
            sql += " AND zone_id = ?"
            params.append(zone_id)
        if start_utc is not None:
            sql += " AND valid_time_utc >= ?"
            params.append(start_utc)
        if end_utc is not None:
            sql += " AND valid_time_utc <= ?"
            params.append(end_utc)
        sql += " ORDER BY zone_id, valid_time_utc"
        rows = []
        for item in self._conn.execute(sql, params):
            rows.append(
                ZoneHourRow(
                    area_id=item["area_id"],
                    zone_id=item["zone_id"],
                    valid_time_utc=item["valid_time_utc"],
                    valid_time_local=item["valid_time_local"],
                    timezone=item["timezone"],
                    temperature_c=item["temperature_c"],
                    source_mode=item["source_mode"],
                    source_family=item["source_family"],
                    temperature_quantity=item["temperature_quantity"],
                    sampling_design=item["sampling_design"],
                    zone_geometry_version=item["zone_geometry_version"],
                    aggregation_spec_version=item["aggregation_spec_version"],
                    observation_kind=item["observation_kind"],
                    coverage_status=item["coverage_status"],
                    activity_id=item["activity_id"],
                )
            )
        return rows

    def put_season_summary(self, record: dict) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO season_summary (
                area_id, zone_id, window_id, sampling_design, source_mode,
                availability, mean_c, n_present, n_expected, coverage_class
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["area_id"],
                record["zone_id"],
                record["window_id"],
                record["sampling_design"],
                record["source_mode"],
                record["availability"],
                record.get("mean_c"),
                record["n_present"],
                record["n_expected"],
                record["coverage_class"],
            ),
        )
        self._conn.commit()

    def get_season_summary(self, **key: object) -> dict | None:
        row = self._conn.execute(
            """
            SELECT * FROM season_summary
            WHERE area_id=? AND zone_id=? AND window_id=? AND sampling_design=? AND source_mode=?
            """,
            (
                key["area_id"],
                key["zone_id"],
                key["window_id"],
                key["sampling_design"],
                key["source_mode"],
            ),
        ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        self._conn.close()


def open_temporal_store(path: str | None = None) -> TemporalStore:
    backend = os.environ.get(STORE_FEATURE_FLAG, "memory")
    if backend == "sqlite" or path:
        return SqliteTemporalStore(path or ":memory:")
    return InMemoryTemporalStore()
