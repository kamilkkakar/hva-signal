"""Census place identity models. No network. No public route."""

from pathlib import Path

from pydantic import ValidationError
import pytest

from app.domain.census_place import (
    CONUS_PLUS_DC_FIPS,
    ISLAND_AREA_FIPS,
    PLACE_IDENTITY_VINTAGE,
    UNSUPPORTED_DEFAULT_SCOPE_FIPS,
    CensusPlaceIdentity,
    PlaceIdentityFailure,
    PlaceScope,
    PlaceType,
    classify_place_type,
    display_name_for,
    normalize_place_name,
    parse_user_place_text,
    scope_for_state_fips,
    strip_lsad_suffix,
    validate_place_geoid_format,
)

DOMAIN_SOURCE = (
    Path(__file__).resolve().parents[2] / "app" / "domain" / "census_place.py"
)


def test_chicago_identity_fields() -> None:
    identity = CensusPlaceIdentity(
        place_geoid="1714000",
        place_name="Chicago",
        official_name="Chicago city",
        state_fips="17",
        state_abbreviation="il",
        display_name="Chicago, IL",
        place_type=PlaceType.INCORPORATED,
        lsad="25",
        funcstat="A",
        scope=PlaceScope.CONUS_PLUS_DC,
    )
    assert identity.state_abbreviation == "IL"
    assert identity.source_vintage == PLACE_IDENTITY_VINTAGE
    assert identity.place_geoid == "1714000"


def test_geoid_must_be_seven_digits() -> None:
    with pytest.raises(ValidationError):
        CensusPlaceIdentity(
            place_geoid="171400",
            place_name="Chicago",
            official_name="Chicago city",
            state_fips="17",
            state_abbreviation="IL",
            display_name="Chicago, IL",
            place_type=PlaceType.INCORPORATED,
            lsad="25",
            funcstat="A",
            scope=PlaceScope.CONUS_PLUS_DC,
        )


def test_place_type_from_official_codes() -> None:
    assert classify_place_type(lsad="25", official_name="Chicago city", funcstat="A") is (
        PlaceType.INCORPORATED
    )
    assert classify_place_type(lsad="57", official_name="Paradise CDP", funcstat="S") is (
        PlaceType.CDP
    )
    assert classify_place_type(
        lsad="00", official_name="Indianapolis city (balance)", funcstat="F"
    ) is PlaceType.CONSOLIDATED_CITY_BALANCE


def test_name_normalization_does_not_substring_match() -> None:
    assert normalize_place_name("Chicago city", "25") == "chicago"
    assert normalize_place_name("Chicago Heights city", "25") == "chicago heights"
    assert normalize_place_name("North Chicago") == "north chicago"
    assert normalize_place_name("Springfield, IL") == "springfield"


def test_parse_city_comma_state_and_bare_geoid() -> None:
    assert parse_user_place_text("Chicago, IL") == ("Chicago", "IL", None)
    assert parse_user_place_text("1714000") == (None, None, "1714000")
    assert parse_user_place_text("Springfield IL") == ("Springfield", "IL", None)


def test_invalid_geoid_shapes() -> None:
    assert validate_place_geoid_format("171400") is PlaceIdentityFailure.INVALID_PLACE_GEOID
    assert validate_place_geoid_format("16980") is PlaceIdentityFailure.INVALID_PLACE_GEOID
    assert validate_place_geoid_format("2502109175") is PlaceIdentityFailure.INVALID_PLACE_GEOID
    assert validate_place_geoid_format("1714000") is None


def test_scope_and_display_helpers() -> None:
    assert scope_for_state_fips("17") is PlaceScope.CONUS_PLUS_DC
    assert scope_for_state_fips("11") is PlaceScope.CONUS_PLUS_DC
    assert scope_for_state_fips("02") is PlaceScope.ALASKA
    assert scope_for_state_fips("15") is PlaceScope.HAWAII
    assert scope_for_state_fips("72") is PlaceScope.PUERTO_RICO
    assert scope_for_state_fips("66") is PlaceScope.ISLAND_AREA
    assert display_name_for("Chicago", "il") == "Chicago, IL"
    assert strip_lsad_suffix("San Juan zona urbana", "62") == "San Juan"


def test_conus_plus_dc_fips_matches_projection_contract() -> None:
    assert "11" in CONUS_PLUS_DC_FIPS
    assert CONUS_PLUS_DC_FIPS.isdisjoint(UNSUPPORTED_DEFAULT_SCOPE_FIPS)
    assert ISLAND_AREA_FIPS == frozenset({"60", "66", "69", "78"})
    assert UNSUPPORTED_DEFAULT_SCOPE_FIPS == frozenset(
        {"02", "15", "60", "66", "69", "72", "78"}
    )


def test_balance_and_proper_name_suffix_stripping() -> None:
    assert strip_lsad_suffix("Indianapolis city (balance)", "00") == "Indianapolis"
    assert strip_lsad_suffix("Butte-Silver Bow (balance)", "00") == "Butte-Silver Bow"
    assert strip_lsad_suffix("Carson City", "00") == "Carson City"
    assert strip_lsad_suffix("Paradise CDP", "57") == "Paradise"
    assert normalize_place_name("Indianapolis city (balance)", "00") == "indianapolis"
    assert normalize_place_name("Indianapolis, IN") == "indianapolis"


def test_invalid_state_fips_is_not_a_place_geoid() -> None:
    assert validate_place_geoid_format("0314000") is PlaceIdentityFailure.INVALID_PLACE_GEOID


def test_identity_rejects_non_2025_vintage_and_state_mismatch() -> None:
    with pytest.raises(ValidationError):
        CensusPlaceIdentity(
            place_geoid="1714000",
            place_name="Chicago",
            official_name="Chicago city",
            state_fips="17",
            state_abbreviation="IL",
            display_name="Chicago, IL",
            place_type=PlaceType.INCORPORATED,
            lsad="25",
            funcstat="A",
            source_vintage="US_CENSUS_GAZETTEER.PLACE.2024",
            scope=PlaceScope.CONUS_PLUS_DC,
        )
    with pytest.raises(ValidationError):
        CensusPlaceIdentity(
            place_geoid="1714000",
            place_name="Chicago",
            official_name="Chicago city",
            state_fips="29",
            state_abbreviation="MO",
            display_name="Chicago, MO",
            place_type=PlaceType.INCORPORATED,
            lsad="25",
            funcstat="A",
            scope=PlaceScope.CONUS_PLUS_DC,
        )


def test_domain_module_has_no_vendor_or_city_special_cases() -> None:
    source = DOMAIN_SOURCE.read_text(encoding="utf-8").casefold()
    assert "fortyguard" not in source
    assert "phoenix-demo" not in source
    assert "if phoenix" not in source
    assert "largest" not in source
