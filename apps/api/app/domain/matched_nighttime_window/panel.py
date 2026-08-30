"""Load the frozen FortyGuard 03:00 replay panel as zone-mean TCM.

Does not compute q_A. Does not call FortyGuard. Per-row provenance is
absent from the JSONL; panel-level provenance is the frozen path.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    hackathon_root,
)
from app.domain.matched_nighttime_window.claims import (
    HOUR_LOCAL,
    N_EXPECTED_NIGHTS,
    REFERENCE_YEARS,
    SOURCE_FAMILY,
    SOURCE_MODE,
    TEMPERATURE_QUANTITY,
    TIMEZONE,
    WINDOW_DATES,
    WINDOW_LABEL,
)
from app.domain.phoenix_v1 import (
    EXPECTED_ZONE_COUNT,
    SEASONAL_END_MONTH_DAY,
    SEASONAL_START_MONTH_DAY,
    THERMAL_AGGREGATION_VERSION,
    ZONE_GEOMETRY_VERSION,
)

PANEL_FIELDS = (
    "date",
    "year",
    "local_time",
    "geoid",
    "contributing_tiles",
    "mean_tcm_c",
    "usable",
)


@dataclass(frozen=True)
class NighttimeTcmObservation:
    date: str
    year: int
    local_time: str
    geoid: str
    mean_tcm_c: float
    contributing_tiles: int | None
    usable: bool
    month_day: str

    @property
    def local_timestamp(self) -> str:
        """Derived AOI-local stamp. The JSONL has date + local_time, not ISO UTC."""
        return f"{self.date}T{self.local_time}"


@dataclass(frozen=True)
class NighttimePanel:
    observations: tuple[NighttimeTcmObservation, ...]
    source_path: str
    source_sha256: str
    n_rows: int
    n_timestamps: int
    n_zones: int
    years: tuple[int, ...]
    hour_local: str
    timezone: str
    window_label: str
    window_dates: str
    temperature_quantity: str
    source_family: str
    source_mode: str
    zone_geometry_version: str
    aggregation_spec_version: str
    has_iso_timestamp_field: bool
    has_row_provenance_field: bool
    has_q_a_field: bool
    raw_fields: tuple[str, ...]

    def for_zone_year(
        self, geoid: str, year: int, *, usable_only: bool = True
    ) -> tuple[NighttimeTcmObservation, ...]:
        key = _geoid(geoid)
        rows = [
            row
            for row in self.observations
            if row.geoid == key
            and row.year == year
            and row.local_time == HOUR_LOCAL
            and _in_matched_window(row.date)
        ]
        if usable_only:
            rows = [row for row in rows if row.usable]
        return tuple(rows)

    def zone_ids(self) -> tuple[str, ...]:
        return tuple(sorted({row.geoid for row in self.observations}))


def _geoid(value: str) -> str:
    return str(value).zfill(11)


def _in_matched_window(iso_date: str) -> bool:
    local_date = date.fromisoformat(iso_date)
    start = date(local_date.year, *SEASONAL_START_MONTH_DAY)
    end = date(local_date.year, *SEASONAL_END_MONTH_DAY)
    return start <= local_date <= end


def canonical_panel_path() -> Path:
    return hackathon_root() / CANONICAL_REFERENCE_RELATIVE_PATH


def load_fortyguard_nighttime_panel(path: Path | None = None) -> NighttimePanel:
    """Read observations.jsonl. Requires mean_tcm_c. Invents nothing."""
    source = Path(path) if path is not None else canonical_panel_path()
    raw_bytes = source.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw_rows = [
        json.loads(line)
        for line in raw_bytes.decode("utf-8").splitlines()
        if line.strip()
    ]
    if not raw_rows:
        raise ValueError("FortyGuard nighttime panel is empty")

    field_union = set()
    for row in raw_rows:
        field_union.update(row.keys())
    has_q_a = any(key in {"q_A", "q_a", "qa"} for key in field_union)
    has_timestamp = "timestamp" in field_union
    has_provenance = bool(
        field_union & {"provenance", "source", "source_family", "source_mode"}
    )

    observations: list[NighttimeTcmObservation] = []
    for row in raw_rows:
        if row.get("mean_tcm_c") is None:
            continue
        local_date = str(row["date"])
        if not _in_matched_window(local_date):
            continue
        observations.append(
            NighttimeTcmObservation(
                date=local_date,
                year=int(row["year"]),
                local_time=str(row.get("local_time") or ""),
                geoid=_geoid(str(row["geoid"])),
                mean_tcm_c=float(row["mean_tcm_c"]),
                contributing_tiles=(
                    int(row["contributing_tiles"])
                    if row.get("contributing_tiles") is not None
                    else None
                ),
                usable=bool(row.get("usable", True)),
                month_day=date.fromisoformat(local_date).strftime("%m-%d"),
            )
        )

    years = tuple(sorted({row.year for row in observations}))
    timestamps = {row.date for row in observations}
    zones = {row.geoid for row in observations}
    return NighttimePanel(
        observations=tuple(observations),
        source_path=str(source),
        source_sha256=digest,
        n_rows=len(observations),
        n_timestamps=len(timestamps),
        n_zones=len(zones),
        years=years,
        hour_local=HOUR_LOCAL,
        timezone=TIMEZONE,
        window_label=WINDOW_LABEL,
        window_dates=WINDOW_DATES,
        temperature_quantity=TEMPERATURE_QUANTITY,
        source_family=SOURCE_FAMILY,
        source_mode=SOURCE_MODE,
        zone_geometry_version=ZONE_GEOMETRY_VERSION,
        aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
        has_iso_timestamp_field=has_timestamp,
        has_row_provenance_field=has_provenance,
        has_q_a_field=has_q_a,
        raw_fields=tuple(sorted(field_union)),
    )


def expected_month_days(year: int) -> tuple[str, ...]:
    start = date(year, *SEASONAL_START_MONTH_DAY)
    end = date(year, *SEASONAL_END_MONTH_DAY)
    days: list[str] = []
    cursor = start
    while cursor <= end:
        days.append(cursor.strftime("%m-%d"))
        cursor = date.fromordinal(cursor.toordinal() + 1)
    if len(days) != N_EXPECTED_NIGHTS:
        raise ValueError("matched window length disagrees with N_EXPECTED_NIGHTS")
    return tuple(days)


def panel_structure_ok(panel: NighttimePanel) -> bool:
    if panel.n_zones != EXPECTED_ZONE_COUNT:
        return False
    if panel.years != REFERENCE_YEARS:
        return False
    if panel.has_q_a_field:
        return False
    hours = {row.local_time for row in panel.observations}
    return hours == {HOUR_LOCAL}
