import pytest

from app.domain.temporal import TemperatureQuantity, TemporalSourceFamily, TemporalSourceMode
from app.services.temporal_source import (
    SourceMixError,
    acquire_mix,
    refuse_blend,
    stamp_from_thermal_data_source,
    stamp_public,
)


def test_thermal_data_source_maps_to_tb_modes() -> None:
    assert stamp_from_thermal_data_source("replay").source_mode is TemporalSourceMode.REPLAY
    assert stamp_from_thermal_data_source("fortyguard_cached").source_mode is TemporalSourceMode.CACHE
    assert stamp_from_thermal_data_source("fortyguard_live").source_mode is TemporalSourceMode.LIVE


def test_public_cannot_claim_tcm() -> None:
    public = stamp_public(acquire_mode="replay")
    assert public.source_family is TemporalSourceFamily.PUBLIC
    assert public.temperature_quantity is TemperatureQuantity.PUBLIC_2M_AIR_ZONE_MEAN
    assert public.thermal_data_source is None


def test_illegal_data_status_pairs() -> None:
    with pytest.raises(SourceMixError):
        stamp_from_thermal_data_source("replay", data_status="live")
    with pytest.raises(SourceMixError):
        stamp_from_thermal_data_source("fortyguard_cached", data_status="live")


def test_mixed_family_is_two_objects() -> None:
    with pytest.raises(SourceMixError):
        refuse_blend(TemporalSourceFamily.FORTYGUARD, TemporalSourceFamily.PUBLIC)
    mixed = acquire_mix(
        [
            stamp_from_thermal_data_source("replay"),
            stamp_from_thermal_data_source("fortyguard_cached"),
        ]
    )
    assert mixed == "MIXED"
    assert mixed != "LIVE"
