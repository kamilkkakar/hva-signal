"""Pure timezone / DST validators. No FortyGuard. No online geocoding."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.aoi_timezone import (
    EXPECTED_ZONE_COUNT,
    PHOENIX_IANA,
    POLICY_VERSION,
    RESOLUTION_RULE,
    TIMEZONE_UNRESOLVED,
    UNSUPPORTED_MULTI_TIMEZONE_AOI,
    AoiLocalTimeError,
    AoiTimezoneResolutionError,
    LonLat,
    TimezoneFailureCode,
    TimezoneMethod,
    assert_client_timezone_matches,
    classify_aoi_local_datetime,
    compare_timezone_methods,
    require_iana_timezone,
    require_unique_aoi_local_hour,
    resolve_aoi_timezone,
    try_timezonefinder_lookup,
    LocalTimeStatus,
)

PHOENIX = LonLat(-112.0740, 33.4484)
WINDOW_ROCK = LonLat(-109.0514, 35.6806)
NYC = LonLat(-74.0060, 40.7128)


def _const(name: str | None):
    return lambda lon, lat: name


def _by_lon(threshold: float, west: str, east: str):
    return lambda lon, lat: west if lon < threshold else east


def _grid(origin: LonLat, count: int = EXPECTED_ZONE_COUNT) -> list[LonLat]:
    return [LonLat(origin.lon + (i * 0.001), origin.lat) for i in range(count)]


def test_unanimous_representative_points_resolve_phoenix() -> None:
    points = _grid(PHOENIX)
    resolved = resolve_aoi_timezone(points, _const(PHOENIX_IANA))
    assert resolved.timezone == PHOENIX_IANA
    assert resolved.policy_version == POLICY_VERSION
    assert resolved.rule == RESOLUTION_RULE
    assert resolved.point_timezones == (PHOENIX_IANA,) * EXPECTED_ZONE_COUNT


def test_one_foreign_representative_point_is_multi_timezone() -> None:
    points = _grid(PHOENIX)
    points[-1] = WINDOW_ROCK
    lookup = _by_lon(-110.5, PHOENIX_IANA, "America/Denver")
    with pytest.raises(AoiTimezoneResolutionError) as exc:
        resolve_aoi_timezone(points, lookup)
    assert exc.value.code == TimezoneFailureCode.MULTI_TIMEZONE_AOI
    assert exc.value.code == UNSUPPORTED_MULTI_TIMEZONE_AOI
    assert exc.value.distinct == ("America/Denver", PHOENIX_IANA)


def test_missing_lookup_is_timezone_not_found() -> None:
    points = _grid(PHOENIX)
    lookup = lambda lon, lat: None if lon > -112.06 else PHOENIX_IANA
    with pytest.raises(AoiTimezoneResolutionError) as exc:
        resolve_aoi_timezone(points, lookup)
    assert exc.value.code == TimezoneFailureCode.TIMEZONE_NOT_FOUND


def test_unknown_iana_from_lookup_is_timezone_not_found() -> None:
    with pytest.raises(AoiTimezoneResolutionError) as exc:
        resolve_aoi_timezone(_grid(PHOENIX), _const("Not/AZone"))
    assert exc.value.code == TimezoneFailureCode.TIMEZONE_NOT_FOUND


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_lookup_is_timezone_not_found(blank: str | None) -> None:
    with pytest.raises(AoiTimezoneResolutionError) as exc:
        resolve_aoi_timezone(_grid(PHOENIX), _const(blank))
    assert exc.value.code == TimezoneFailureCode.TIMEZONE_NOT_FOUND
    assert exc.value.code == TIMEZONE_UNRESOLVED


def test_lookup_miss_takes_priority_over_split() -> None:
    points = _grid(PHOENIX)
    points[-1] = WINDOW_ROCK

    def lookup(lon: float, lat: float) -> str | None:
        if lon > -110.5:
            return None
        return PHOENIX_IANA

    with pytest.raises(AoiTimezoneResolutionError) as exc:
        resolve_aoi_timezone(points, lookup)
    assert exc.value.code == TimezoneFailureCode.TIMEZONE_NOT_FOUND


def test_arizona_coordinates_do_not_force_phoenix() -> None:
    """National path has no AZ FIPS → America/Phoenix shortcut."""
    resolved = resolve_aoi_timezone(_grid(PHOENIX), _const("America/Denver"))
    assert resolved.timezone == "America/Denver"


def test_same_offset_different_iana_is_multi_timezone() -> None:
    points = _grid(PHOENIX)
    names = ("America/Denver",) * 24 + ("America/Boise",)
    lookup = lambda lon, lat: names[
        next(i for i, point in enumerate(points) if point.lon == lon and point.lat == lat)
    ]
    with pytest.raises(AoiTimezoneResolutionError) as exc:
        resolve_aoi_timezone(points, lookup)
    assert exc.value.code == TimezoneFailureCode.MULTI_TIMEZONE_AOI
    assert exc.value.distinct == ("America/Boise", "America/Denver")


def test_alias_is_not_canonicalized_to_phoenix() -> None:
    resolved = resolve_aoi_timezone(_grid(PHOENIX), _const("US/Arizona"))
    assert resolved.timezone == "US/Arizona"
    with pytest.raises(ValueError, match="does not match"):
        assert_client_timezone_matches("US/Arizona", PHOENIX_IANA)


def test_wrong_point_count_is_invariant_not_timezone_code() -> None:
    with pytest.raises(ValueError, match="representative points"):
        resolve_aoi_timezone([PHOENIX], _const(PHOENIX_IANA))


def test_invalid_coordinates_are_rejected() -> None:
    with pytest.raises(ValueError, match="longitude"):
        LonLat(-200.0, 33.0)
    with pytest.raises(ValueError, match="latitude"):
        LonLat(-112.0, 100.0)


def test_place_centroid_and_seed_miss_a_split_aoi() -> None:
    representative = _grid(PHOENIX)
    representative[-1] = WINDOW_ROCK
    centroids = list(representative)
    lookup = _by_lon(-110.5, PHOENIX_IANA, "America/Denver")
    comparison = compare_timezone_methods(
        lookup=lookup,
        tract_representative_points=representative,
        tract_centroids=centroids,
        place_centroid=PHOENIX,
        seed=PHOENIX,
    )
    assert comparison.place_centroid is not None
    assert comparison.seed is not None
    assert comparison.place_centroid.timezone == PHOENIX_IANA
    assert comparison.seed.timezone == PHOENIX_IANA
    assert comparison.production.code == TimezoneFailureCode.MULTI_TIMEZONE_AOI
    assert comparison.tract_centroids.code == TimezoneFailureCode.MULTI_TIMEZONE_AOI
    assert comparison.methods_agree is False


def test_centroid_outside_polygon_can_false_split() -> None:
    """A centroid that left the tract can invent a second timezone."""
    representative = _grid(PHOENIX)
    centroids = _grid(PHOENIX)
    centroids[0] = WINDOW_ROCK
    lookup = _by_lon(-110.5, PHOENIX_IANA, "America/Denver")
    comparison = compare_timezone_methods(
        lookup=lookup,
        tract_representative_points=representative,
        tract_centroids=centroids,
        place_centroid=PHOENIX,
    )
    assert comparison.production.timezone == PHOENIX_IANA
    assert comparison.tract_centroids.code == TimezoneFailureCode.MULTI_TIMEZONE_AOI
    assert comparison.methods_agree is False


def test_compare_requires_twenty_five_points() -> None:
    with pytest.raises(ValueError, match="tract_representative_points"):
        compare_timezone_methods(
            lookup=_const(PHOENIX_IANA),
            tract_representative_points=[PHOENIX],
            tract_centroids=[PHOENIX],
        )


@pytest.mark.parametrize(
    ("when", "iana", "expected"),
    [
        (datetime(2026, 3, 8, 2, 0), "America/New_York", LocalTimeStatus.NONEXISTENT),
        (datetime(2026, 3, 8, 1, 0), "America/New_York", LocalTimeStatus.UNIQUE),
        (datetime(2026, 3, 8, 3, 0), "America/New_York", LocalTimeStatus.UNIQUE),
        (datetime(2026, 11, 1, 1, 0), "America/New_York", LocalTimeStatus.AMBIGUOUS),
        (datetime(2026, 11, 1, 0, 0), "America/New_York", LocalTimeStatus.UNIQUE),
        (datetime(2026, 11, 1, 2, 0), "America/New_York", LocalTimeStatus.UNIQUE),
        (datetime(2024, 3, 10, 2, 0), "America/New_York", LocalTimeStatus.NONEXISTENT),
        (datetime(2024, 11, 3, 1, 0), "America/New_York", LocalTimeStatus.AMBIGUOUS),
        (datetime(2025, 3, 9, 2, 0), "America/Chicago", LocalTimeStatus.NONEXISTENT),
        (datetime(2025, 11, 2, 1, 0), "America/Denver", LocalTimeStatus.AMBIGUOUS),
        (datetime(2026, 3, 8, 2, 0), "America/Los_Angeles", LocalTimeStatus.NONEXISTENT),
        (datetime(2026, 3, 8, 2, 0), PHOENIX_IANA, LocalTimeStatus.UNIQUE),
        (datetime(2026, 11, 1, 1, 0), PHOENIX_IANA, LocalTimeStatus.UNIQUE),
        (datetime(2024, 3, 10, 2, 0), PHOENIX_IANA, LocalTimeStatus.UNIQUE),
        (datetime(2024, 11, 3, 1, 0), PHOENIX_IANA, LocalTimeStatus.UNIQUE),
        (datetime(2026, 3, 8, 2, 0), "Pacific/Honolulu", LocalTimeStatus.UNIQUE),
        (datetime(2026, 11, 1, 1, 0), "Pacific/Honolulu", LocalTimeStatus.UNIQUE),
        (datetime(2024, 7, 15, 15, 0), PHOENIX_IANA, LocalTimeStatus.UNIQUE),
        (datetime(2024, 7, 15, 3, 0), "America/New_York", LocalTimeStatus.UNIQUE),
    ],
)
def test_classify_dst_and_phoenix(
    when: datetime, iana: str, expected: LocalTimeStatus
) -> None:
    assert classify_aoi_local_datetime(when, iana) is expected


def test_signal_a_frozen_hour_is_unique_on_us_dst_sundays() -> None:
    for day in (
        datetime(2024, 3, 10, 3, 0),
        datetime(2025, 3, 9, 3, 0),
        datetime(2026, 3, 8, 3, 0),
        datetime(2024, 11, 3, 3, 0),
        datetime(2026, 11, 1, 3, 0),
    ):
        assert classify_aoi_local_datetime(day, "America/New_York") is LocalTimeStatus.UNIQUE
        assert require_unique_aoi_local_hour(day, "America/New_York") == day


def test_require_unique_rejects_nonexistent_and_ambiguous() -> None:
    gap = datetime(2026, 3, 8, 2, 0)
    overlap = datetime(2026, 11, 1, 1, 0)
    with pytest.raises(AoiLocalTimeError) as missing:
        require_unique_aoi_local_hour(gap, "America/New_York")
    assert missing.value.code == TimezoneFailureCode.NONEXISTENT_LOCAL_TIME
    with pytest.raises(AoiLocalTimeError) as repeated:
        require_unique_aoi_local_hour(overlap, "America/New_York")
    assert repeated.value.code == TimezoneFailureCode.AMBIGUOUS_LOCAL_TIME


def test_require_unique_accepts_phoenix_transition_hours() -> None:
    spring = datetime(2026, 3, 8, 2, 0)
    fall = datetime(2026, 11, 1, 1, 0)
    summer = datetime(2024, 7, 15, 15, 0)
    assert require_unique_aoi_local_hour(spring, PHOENIX_IANA) == spring
    assert require_unique_aoi_local_hour(fall, PHOENIX_IANA) == fall
    accepted = require_unique_aoi_local_hour(summer, PHOENIX_IANA)
    assert accepted == summer
    assert accepted.tzinfo is None


def test_require_unique_rejects_aware_and_minutes() -> None:
    aware = datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="naive"):
        require_unique_aoi_local_hour(aware, PHOENIX_IANA)
    with pytest.raises(ValueError, match="minutes"):
        require_unique_aoi_local_hour(datetime(2024, 7, 15, 15, 30), PHOENIX_IANA)


def test_classify_rejects_aware_datetime() -> None:
    with pytest.raises(ValueError, match="naive"):
        classify_aoi_local_datetime(
            datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc), PHOENIX_IANA
        )


def test_unknown_iana_is_not_found() -> None:
    with pytest.raises(AoiTimezoneResolutionError) as exc:
        require_iana_timezone("Mars/Olympus")
    assert exc.value.code == TimezoneFailureCode.TIMEZONE_NOT_FOUND


def test_client_timezone_must_match_geography() -> None:
    assert assert_client_timezone_matches(None, PHOENIX_IANA) == PHOENIX_IANA
    assert assert_client_timezone_matches(PHOENIX_IANA, PHOENIX_IANA) == PHOENIX_IANA
    with pytest.raises(ValueError, match="does not match"):
        assert_client_timezone_matches("America/Denver", PHOENIX_IANA)


def test_timezonefinder_is_not_a_hard_dependency() -> None:
    assert try_timezonefinder_lookup() is None


def test_production_method_name_is_representative_points() -> None:
    points = _grid(NYC)
    comparison = compare_timezone_methods(
        lookup=_const("America/New_York"),
        tract_representative_points=points,
        tract_centroids=points,
        place_centroid=NYC,
        seed=NYC,
    )
    assert comparison.production.method is TimezoneMethod.TRACT_REPRESENTATIVE_POINTS
    assert comparison.production.timezone == "America/New_York"
    assert comparison.methods_agree is True
