"""SHA-locked loader for the Phoenix hourly thermal-event candidate."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.core.phoenix_v1_area_config import hackathon_root
from app.domain.hourly_thermal_event import HourlyThermalEventContract
from app.domain.phoenix_v1 import (
    AREA_ID,
    REFERENCE_YEARS,
    THERMAL_AGGREGATION_VERSION,
    ZONE_GEOMETRY_VERSION,
)

PHOENIX_HOURLY_EVENT_CONTRACT_RELATIVE_PATH = (
    Path("data") / "gate0" / "phoenix-v1" / "hourly_thermal_event_candidate.json"
)
PHOENIX_HOURLY_EVENT_CONTRACT_SHA256 = (
    "9bc43aca20d88b8654def288ed59e85f2af3241a18eb54c43736167ad53b5e46"
)
PHOENIX_HOURLY_EVENT_CONTRACT_VERSION = (
    "PHX_PERSISTENT_RELATIVE_THERMAL_EXCEEDANCE_V1_CANDIDATE"
)


class HourlyThermalEventRegistryError(ValueError):
    """The tracked candidate is missing, changed, malformed, or inconsistent."""


@dataclass(frozen=True)
class ResolvedHourlyThermalEventContract:
    contract: HourlyThermalEventContract
    path: Path
    sha256: str


def load_phoenix_hourly_thermal_event_contract(
    *,
    root: Path | None = None,
    expected_sha256: str | None = None,
) -> ResolvedHourlyThermalEventContract:
    repo = Path(root) if root is not None else hackathon_root()
    path = repo / PHOENIX_HOURLY_EVENT_CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise HourlyThermalEventRegistryError(
            "canonical Phoenix hourly thermal-event candidate is missing"
        )
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = expected_sha256 or PHOENIX_HOURLY_EVENT_CONTRACT_SHA256
    if digest != expected:
        raise HourlyThermalEventRegistryError(
            "Phoenix hourly thermal-event candidate SHA-256 mismatch"
        )
    try:
        contract = HourlyThermalEventContract.model_validate(
            json.loads(raw.decode("utf-8"))
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise HourlyThermalEventRegistryError(
            f"invalid Phoenix hourly thermal-event candidate: {exc}"
        ) from exc

    if contract.contract_version != PHOENIX_HOURLY_EVENT_CONTRACT_VERSION:
        raise HourlyThermalEventRegistryError("hourly event contract version mismatch")
    if contract.area_id != AREA_ID:
        raise HourlyThermalEventRegistryError("hourly event area_id mismatch")
    if contract.zone_geometry_version != ZONE_GEOMETRY_VERSION:
        raise HourlyThermalEventRegistryError("hourly event geometry version mismatch")
    if contract.aggregation_spec_version != THERMAL_AGGREGATION_VERSION:
        raise HourlyThermalEventRegistryError("hourly event aggregation version mismatch")
    if contract.threshold.reference_years != REFERENCE_YEARS:
        raise HourlyThermalEventRegistryError("hourly event reference years mismatch")
    if contract.threshold.event_quantile_cutoff != 0.97:
        raise HourlyThermalEventRegistryError("canonical candidate quantile must be 0.97")
    if contract.persistence.minimum_consecutive_hours != 3:
        raise HourlyThermalEventRegistryError(
            "canonical candidate persistence must be three consecutive hours"
        )
    return ResolvedHourlyThermalEventContract(
        contract=contract,
        path=path,
        sha256=digest,
    )
