"""Assemble four observed instants from TRACKED fixtures only.

Reads data/phoenix snapshots, four_instant_differences, and held 03:00
rows in observations.jsonl. Never reads workforce/. Never calls FortyGuard.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.phoenix_v1_area_config import hackathon_root
from app.domain.observed_thermal_instants.types import (
    DirectInstantDifference,
    InstantCoverage,
    ObservedThermalInstant,
    ObservedThermalSequence,
)

ACTIVITY_1500 = "92086c4c-1550-4263-8ac8-9a6c9e030bc4"
ACTIVITY_2100 = "9865bd33-43a0-42b0-bc9b-74b27510002d"
DATE_D = "2024-07-08"
DATE_D_PLUS_1 = "2024-07-09"
AREA_ID = "phoenix-demo"
INSTANT_ORDER = ("03:00_D", "15:00", "21:00", "03:00_D+1")
QUANTITY = "TEMPERATURE DIFFERENCE BETWEEN OBSERVED INSTANTS"
METHOD_NOTE = (
    "TEMPERATURE DIFFERENCE BETWEEN OBSERVED INSTANTS. Four named "
    "observations only. No interpolation."
)
NOT_CLAIMS = (
    "cooling rate",
    "interpolation",
    "24-hour profile",
    "hourly profile",
    "AfterHeat",
    "recovery",
    "HeatDose",
    "q_A",
    "JJA",
    "climate trend",
)
SNAP_1500 = Path("data") / "phoenix" / "snapshots" / "2024-07-08T15-00.snapshot.json"
SNAP_2100 = Path("data") / "phoenix" / "snapshots" / "2024-07-08T21-00.snapshot.json"
DIFFS = Path("data") / "phoenix" / "reference" / "four_instant_differences_2024-07-08.json"
OBS = Path("data") / "phoenix" / "reference" / "observations.jsonl"


def _geoid(value: str) -> str:
    return str(value).zfill(11)


def _tracked(rel: Path) -> Path:
    path = hackathon_root() / rel
    posix = path.as_posix()
    if "/workforce/" in posix:
        raise ValueError(f"refused workforce path {posix}")
    return path


@lru_cache(maxsize=1)
def load_tracked_snapshots() -> dict[str, dict]:
    docs = {
        "15:00": json.loads(_tracked(SNAP_1500).read_text(encoding="utf-8")),
        "21:00": json.loads(_tracked(SNAP_2100).read_text(encoding="utf-8")),
    }
    if docs["15:00"]["activity_id"] != ACTIVITY_1500:
        raise ValueError("15:00 activity_id mismatch")
    if docs["21:00"]["activity_id"] != ACTIVITY_2100:
        raise ValueError("21:00 activity_id mismatch")
    return docs


@lru_cache(maxsize=1)
def load_four_instant_differences() -> dict:
    return json.loads(_tracked(DIFFS).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_held_0300_means() -> dict[tuple[str, str], float]:
    """Held 03:00 D and D+1 only. Replay panel. Not reacquired."""
    means: dict[tuple[str, str], float] = {}
    for line in _tracked(OBS).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("local_time") != "03:00":
            continue
        if row.get("date") not in {DATE_D, DATE_D_PLUS_1}:
            continue
        if row.get("mean_tcm_c") is None:
            continue
        means[(_geoid(str(row["geoid"])), str(row["date"]))] = float(row["mean_tcm_c"])
    return means


def _zone_temp(doc: dict, geoid: str) -> float | None:
    key = _geoid(geoid)
    for row in doc["zones"]:
        if str(row["zone_id"]).zfill(11) == key:
            return float(row["mean_temperature_c"])
    return None


def _coverage(doc: dict) -> InstantCoverage:
    return InstantCoverage(
        valid_zone_count=int(doc["valid_zone_count"]),
        expected_zone_count=int(doc["expected_zone_count"]),
    )


def assemble_observed_thermal_sequence(
    geoid: str,
    *,
    area_id: str = AREA_ID,
) -> ObservedThermalSequence:
    if area_id != AREA_ID:
        raise ValueError("observed instants are phoenix-demo only")
    key = _geoid(geoid)
    snaps = load_tracked_snapshots()
    diffs = load_four_instant_differences()
    held = load_held_0300_means()
    held_d = [g for (g, d) in held if d == DATE_D]
    held_d1 = [g for (g, d) in held if d == DATE_D_PLUS_1]
    cov_d = InstantCoverage(valid_zone_count=len(set(held_d)), expected_zone_count=25)
    cov_d1 = InstantCoverage(valid_zone_count=len(set(held_d1)), expected_zone_count=25)
    zone_diff = next((row for row in diffs["zones"] if str(row["geoid"]).zfill(11) == key), None)
    if zone_diff is None:
        raise KeyError(f"no four-instant differences for {key}")

    observations = (
        ObservedThermalInstant(
            instant_id="03:00_D",
            date=DATE_D,
            local_time="03:00",
            local_timestamp=f"{DATE_D}T03:00",
            temperature_c=held.get((key, DATE_D)),
            source="fortyguard_cached",
            source_mode="replay",
            coverage=cov_d,
            activity_id=None,
            observation_status="held_not_reacquired",
            label="03:00 D",
        ),
        ObservedThermalInstant(
            instant_id="15:00",
            date=DATE_D,
            local_time="15:00",
            local_timestamp=f"{DATE_D}T15:00",
            temperature_c=_zone_temp(snaps["15:00"], key),
            source="fortyguard_cached",
            source_mode="cache",
            coverage=_coverage(snaps["15:00"]),
            activity_id=ACTIVITY_1500,
            observation_status="cached",
            label="15:00",
        ),
        ObservedThermalInstant(
            instant_id="21:00",
            date=DATE_D,
            local_time="21:00",
            local_timestamp=f"{DATE_D}T21:00",
            temperature_c=_zone_temp(snaps["21:00"], key),
            source="fortyguard_cached",
            source_mode="cache",
            coverage=_coverage(snaps["21:00"]),
            activity_id=ACTIVITY_2100,
            observation_status="cached",
            label="21:00",
        ),
        ObservedThermalInstant(
            instant_id="03:00_D+1",
            date=DATE_D_PLUS_1,
            local_time="03:00",
            local_timestamp=f"{DATE_D_PLUS_1}T03:00",
            temperature_c=held.get((key, DATE_D_PLUS_1)),
            source="fortyguard_cached",
            source_mode="replay",
            coverage=cov_d1,
            activity_id=None,
            observation_status="held_not_reacquired",
            label="03:00 D+1",
        ),
    )
    differences = (
        DirectInstantDifference(
            from_instant_id="03:00_D",
            to_instant_id="15:00",
            delta_c=float(zone_diff["T15_minus_T03_D"]),
            quantity=QUANTITY,
            label=QUANTITY,
        ),
        DirectInstantDifference(
            from_instant_id="15:00",
            to_instant_id="21:00",
            delta_c=float(zone_diff["T21_minus_T15"]),
            quantity=QUANTITY,
            label=QUANTITY,
        ),
        DirectInstantDifference(
            from_instant_id="21:00",
            to_instant_id="03:00_D+1",
            delta_c=float(zone_diff["T03_Dplus1_minus_T21"]),
            quantity=QUANTITY,
            label=QUANTITY,
        ),
    )
    return ObservedThermalSequence(
        date_context=f"{DATE_D} / {DATE_D_PLUS_1} America/Phoenix",
        area_id=area_id,
        geoid=key,
        observations=observations,
        direct_differences=differences,
        source="FortyGuard",
        method_note=METHOD_NOTE,
        not_claims=NOT_CLAIMS,
        unpublished=True,
        not_signal_a=True,
        geometry_sha256=str(snaps["15:00"]["geometry_sha256"]),
        snapshot_fingerprints={
            "15:00": str(snaps["15:00"]["snapshot_request_fingerprint"]),
            "21:00": str(snaps["21:00"]["snapshot_request_fingerprint"]),
        },
    )
