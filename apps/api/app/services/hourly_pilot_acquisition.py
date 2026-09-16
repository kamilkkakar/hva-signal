"""Durable acquisition boundary for the exact frozen hourly-pilot canary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from app.core.hourly_thermal_pilot_registry import (
    CANARY_SLOT_ID,
    ResolvedHourlyThermalPilotManifest,
    request_for_hourly_pilot_slot,
)
from app.core.postgres_acquisition import PostgresAcquisitionStore
from app.integrations.fortyguard.temporal_modes import build_heatmap_payload

HOURLY_PILOT_VENDOR_PATH: Final = "/v1/heatmap"


class HourlyPilotAcquisitionError(ValueError):
    """The requested slot is outside the currently authorized pilot boundary."""


@dataclass(frozen=True)
class PreparedHourlyPilotAcquisition:
    manifest_sha256: str
    slot_id: str
    request_fingerprint: str
    path: str
    payload: dict[str, Any]


def prepare_hourly_pilot_canary(
    resolved: ResolvedHourlyThermalPilotManifest,
    slot_id: str,
) -> PreparedHourlyPilotAcquisition:
    """Rebuild the sole authorized canary request from server-owned inputs."""

    if slot_id != CANARY_SLOT_ID:
        raise HourlyPilotAcquisitionError(
            "The hourly pilot canary must complete before any batch slot."
        )
    slot = next(
        (candidate for candidate in resolved.manifest.slots if candidate.slot_id == slot_id),
        None,
    )
    if slot is None or slot.phase != "canary":
        raise HourlyPilotAcquisitionError("The frozen canary slot is unavailable.")
    request = request_for_hourly_pilot_slot(resolved, slot)
    return PreparedHourlyPilotAcquisition(
        manifest_sha256=resolved.sha256,
        slot_id=slot.slot_id,
        request_fingerprint=slot.request_fingerprint,
        path=HOURLY_PILOT_VENDOR_PATH,
        payload=build_heatmap_payload(request),
    )


def run_hourly_pilot_canary(
    resolved: ResolvedHourlyThermalPilotManifest,
    *,
    slot_id: str,
    store: PostgresAcquisitionStore,
    submit: Callable[[], str],
    poll: Callable[[str], dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    """Run or recover the canary under its preregistered request fingerprint."""

    prepared = prepare_hourly_pilot_canary(resolved, slot_id)
    return store.run(
        prepared.path,
        prepared.payload,
        request_fingerprint=prepared.request_fingerprint,
        submit=submit,
        poll=poll,
    )
