"""Load the frozen Decision 1B 93×25 reference panel.

Does not compute q_A, ECDF, leakage, or Decision 8 spread.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.area_config import AreaConfig
from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    hackathon_root,
)
from app.domain.enums import ReferenceEvidenceQuality
from app.domain.phoenix_v1 import REFERENCE_HOUR_LOCAL, REFERENCE_VERSION, ZONE_GEOMETRY_VERSION
from app.services.phoenix_v1_thermal import observations_from_jsonl_rows
from app.services.temporal_anomaly import ReferenceObservation, evaluate_reference_quality


@dataclass(frozen=True)
class PhoenixV1ReferencePanel:
    observations: list[ReferenceObservation]
    source_path: Path
    source_sha256: str | None
    row_count: int
    timestamp_count: int
    tract_count: int
    quality: str
    reference_version: str
    zone_geometry_version: str
    reason: str | None = None


def canonical_reference_source_path() -> Path:
    return hackathon_root() / CANONICAL_REFERENCE_RELATIVE_PATH


def _empty_panel(
    source_path: Path,
    *,
    reason: str,
    source_sha256: str | None = None,
) -> PhoenixV1ReferencePanel:
    return PhoenixV1ReferencePanel(
        observations=[],
        source_path=source_path,
        source_sha256=source_sha256,
        row_count=0,
        timestamp_count=0,
        tract_count=0,
        quality=ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
        reference_version=REFERENCE_VERSION,
        zone_geometry_version=ZONE_GEOMETRY_VERSION,
        reason=reason,
    )


def load_phoenix_v1_reference_panel(
    config: AreaConfig,
    *,
    source_path: Path | None = None,
) -> PhoenixV1ReferencePanel:
    """Load and structurally validate the canonical Decision 1B panel."""
    path = Path(source_path) if source_path is not None else canonical_reference_source_path()
    if config.historical_reference_window.version != REFERENCE_VERSION:
        return _empty_panel(path, reason="AreaConfig reference version mismatch")
    if config.zone_geometry_version != ZONE_GEOMETRY_VERSION:
        return _empty_panel(path, reason="AreaConfig geometry version mismatch")
    if not path.is_file():
        return _empty_panel(path, reason="canonical Decision 1B reference source is absent")

    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        rows = [
            json.loads(line)
            for line in raw.decode("utf-8").splitlines()
            if line.strip()
        ]
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _empty_panel(
            path,
            reason="canonical Decision 1B reference source is malformed",
            source_sha256=digest,
        )

    hours = {str(row.get("local_time") or "") for row in rows}
    if hours and hours != {REFERENCE_HOUR_LOCAL}:
        return _empty_panel(
            path,
            reason="reference panel contains an unsupported hour",
            source_sha256=digest,
        )

    keys = [(str(row.get("date")), str(row.get("geoid")).zfill(11)) for row in rows]
    if len(keys) != len(set(keys)):
        return _empty_panel(
            path,
            reason="reference panel contains duplicate tract×timestamp keys",
            source_sha256=digest,
        )

    try:
        observations = observations_from_jsonl_rows(rows)
    except (KeyError, TypeError, ValueError):
        return _empty_panel(
            path,
            reason="canonical Decision 1B reference source is malformed",
            source_sha256=digest,
        )

    quality = evaluate_reference_quality(observations)
    return PhoenixV1ReferencePanel(
        observations=observations,
        source_path=path,
        source_sha256=digest,
        row_count=quality.n_rows,
        timestamp_count=quality.n_timestamps,
        tract_count=quality.n_tracts,
        quality=quality.quality,
        reference_version=REFERENCE_VERSION,
        zone_geometry_version=ZONE_GEOMETRY_VERSION,
        reason=quality.reason,
    )
