"""Capability negotiation for the server-owned city catalog."""

from __future__ import annotations

from app.domain.multicity.catalog import get_city
from app.domain.multicity.city_config import CapabilityKey, CapabilityStatus, CityId


def negotiate_capabilities(
    city_id: CityId | str,
) -> dict[CapabilityKey, CapabilityStatus]:
    return dict(get_city(city_id).capabilities)

