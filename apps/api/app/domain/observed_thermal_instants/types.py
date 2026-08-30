"""Typed observed-instant contract. Four named observations only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InstantCoverage:
    valid_zone_count: int
    expected_zone_count: int

    @property
    def label(self) -> str:
        return f"{self.valid_zone_count}/{self.expected_zone_count}"


@dataclass(frozen=True)
class ObservedThermalInstant:
    instant_id: str
    date: str
    local_time: str
    local_timestamp: str
    temperature_c: float | None
    source: str
    source_mode: str
    coverage: InstantCoverage
    activity_id: str | None
    observation_status: str
    label: str


@dataclass(frozen=True)
class DirectInstantDifference:
    from_instant_id: str
    to_instant_id: str
    delta_c: float | None
    quantity: str
    label: str


@dataclass(frozen=True)
class ObservedThermalSequence:
    date_context: str
    area_id: str
    geoid: str
    observations: tuple[ObservedThermalInstant, ...]
    direct_differences: tuple[DirectInstantDifference, ...]
    source: str
    method_note: str
    not_claims: tuple[str, ...]
    unpublished: bool
    not_signal_a: bool
    geometry_sha256: str
    snapshot_fingerprints: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "date_context": self.date_context,
            "area": {"area_id": self.area_id, "geoid": self.geoid},
            "observations": [
                {
                    "instant_id": item.instant_id,
                    "date": item.date,
                    "local_time": item.local_time,
                    "local_timestamp": item.local_timestamp,
                    "temperature_c": item.temperature_c,
                    "source": item.source,
                    "source_mode": item.source_mode,
                    "coverage": {
                        "valid_zone_count": item.coverage.valid_zone_count,
                        "expected_zone_count": item.coverage.expected_zone_count,
                        "label": item.coverage.label,
                    },
                    "activity_id": item.activity_id,
                    "observation_status": item.observation_status,
                    "label": item.label,
                }
                for item in self.observations
            ],
            "direct_differences": [
                {
                    "from_instant_id": item.from_instant_id,
                    "to_instant_id": item.to_instant_id,
                    "delta_c": item.delta_c,
                    "quantity": item.quantity,
                    "label": item.label,
                }
                for item in self.direct_differences
            ],
            "source": self.source,
            "method_note": self.method_note,
            "not_claims": list(self.not_claims),
            "unpublished": self.unpublished,
            "not_signal_a": self.not_signal_a,
            "geometry_sha256": self.geometry_sha256,
            "snapshot_fingerprints": dict(self.snapshot_fingerprints),
        }
