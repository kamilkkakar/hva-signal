"""Seed InMemorySelectedTimeReuse with the phoenix-demo cached SelectedTimeSnapshot.

Uses the processed 25-zone means only. Does not load the vendor tile dump.
Does not bind Signal A analysis_result.json.
The seed key is snapshot_request_fingerprint (hva-signal-b-snapshot-identity-v1),
not the adapter L2 key.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.signals import (
    SelectedTimeSnapshot,
    SelectedTimeSnapshotZone,
    SignalAvailability,
    SignalProvenance,
    ThermalSignalKind,
)

CACHED_ACTIVITY_ID = "e0244934-0840-4072-bcb6-96cca26a9a20"
CACHED_SNAPSHOT_FINGERPRINT = (
    "319d2425f955a51527d3ddad1cbb0b2588d5336fff12f9ceabc035a9d38282f8"
)
CACHED_FIXTURE_NAME = "signal_b_cached_phoenix_demo_2025_07_15_0300.json"
ADAPTER_L2_KEY = "d83bde1d8e3e7807d67571a8a164c5767ac744c5b125fdfed8fbb1e890813c1d"

_FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / CACHED_FIXTURE_NAME


def load_cached_seed_document() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def load_phoenix_cached_snapshot() -> SelectedTimeSnapshot:
    doc = load_cached_seed_document()
    if doc.get("snapshot_request_fingerprint") != CACHED_SNAPSHOT_FINGERPRINT:
        raise ValueError("cached Signal B seed fingerprint mismatch")
    target = datetime.fromisoformat(str(doc["target_timestamp_local"]))
    zones = [
        SelectedTimeSnapshotZone(
            zone_id=str(row["zone_id"]),
            mean_temperature_c=row["mean_temperature_c"],
            tile_count=int(row["tile_count"]),
            coverage_status=str(row.get("coverage_status") or "ok"),
        )
        for row in doc["zones"]
    ]
    return SelectedTimeSnapshot(
        area_id=str(doc["area_id"]),
        target_timestamp=target,
        timezone=str(doc["timezone"]),
        units="celsius",
        aggregation_method="centroid_within_mean",
        aggregation_spec_version=str(doc["aggregation_spec_version"]),
        spatial_resolution="zone",
        user_facing_tile_map=False,
        availability=SignalAvailability.READY,
        provenance=SignalProvenance(
            signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
            area_id=str(doc["area_id"]),
            target_timestamp=target,
            timezone=str(doc["timezone"]),
            source=ThermalDataSource.FORTYGUARD_CACHED,
            data_status=DataStatus.CACHED,
            geometry_version=str(doc["geometry_version"]),
            aggregation_spec_version=str(doc["aggregation_spec_version"]),
            vendor_request_fingerprint=CACHED_SNAPSHOT_FINGERPRINT,
            notes=[
                f"activity_id={CACHED_ACTIVITY_ID}",
                "source_mode=cache",
                "reuse_only selected-time snapshot",
            ],
        ),
        zones=zones,
        expected_zone_count=int(doc["expected_zone_count"]),
        valid_zone_count=int(doc["valid_zone_count"]),
        missing_zone_ids=list(doc.get("missing_zone_ids") or []),
        geometry_sha256=str(doc["geometry_sha256"]),
        quality_flags=list(doc.get("quality_flags") or []),
    )
