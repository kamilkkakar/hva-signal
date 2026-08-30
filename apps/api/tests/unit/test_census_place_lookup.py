"""Deterministic 2025 Gazetteer place lookup. Fixture is official Census rows."""

from pathlib import Path

import pytest

from app.domain.census_place import (
    PLACE_IDENTITY_VINTAGE,
    PlaceIdentityFailure,
    PlaceLookupQuery,
    PlaceScope,
    PlaceType,
)
from app.services.census_place_lookup import (
    CensusPlaceIndex,
    compact_index_bytes,
    parse_gazetteer_places,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "census_place_gazetteer_2025_excerpt.txt"
)
LIVE_GAZETTEER = Path(
    r"f:\cursor\hackathon\workforce\national_resolver\_cache\place"
    r"\2025_Gaz_place_national.txt"
)


@pytest.fixture(scope="module")
def index() -> CensusPlaceIndex:
    return CensusPlaceIndex.from_path(FIXTURE)


def test_chicago_il_resolves_to_official_geoid(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Chicago, IL"))
    assert result.ok
    assert result.identity is not None
    assert result.identity.place_geoid == "1714000"
    assert result.identity.official_name == "Chicago city"
    assert result.identity.place_name == "Chicago"
    assert result.identity.state_fips == "17"
    assert result.identity.state_abbreviation == "IL"
    assert result.identity.display_name == "Chicago, IL"
    assert result.identity.place_type is PlaceType.INCORPORATED
    assert result.identity.source_vintage == PLACE_IDENTITY_VINTAGE
    assert result.identity.geoidfq == "1600000US1714000"


def test_chicago_without_state_is_unique_in_fixture(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Chicago"))
    assert result.ok
    assert result.identity is not None
    assert result.identity.place_geoid == "1714000"


def test_chicago_does_not_match_chicago_heights(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Chicago Heights, IL"))
    assert result.ok
    assert result.identity is not None
    assert result.identity.place_geoid == "1714026"


def test_springfield_without_state_is_ambiguous(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Springfield"))
    assert not result.ok
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    geoids = {candidate.place_geoid for candidate in result.candidates}
    assert geoids == {"1772000", "2567000", "2970000", "3974118"}


def test_springfield_il_versus_springfield_mo(index: CensusPlaceIndex) -> None:
    illinois = index.resolve(PlaceLookupQuery(raw_text="Springfield, IL"))
    missouri = index.resolve(PlaceLookupQuery(raw_text="Springfield, MO"))
    assert illinois.ok and illinois.identity is not None
    assert missouri.ok and missouri.identity is not None
    assert illinois.identity.place_geoid == "1772000"
    assert missouri.identity.place_geoid == "2970000"
    assert illinois.identity.display_name == "Springfield, IL"
    assert missouri.identity.display_name == "Springfield, MO"


def test_phoenix_az_matches_frozen_phoenix_place_geoid(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Phoenix, AZ"))
    assert result.ok
    assert result.identity is not None
    assert result.identity.place_geoid == "0455000"
    assert result.identity.official_name == "Phoenix city"


def test_phoenix_without_state_is_ambiguous(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Phoenix"))
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    geoids = {candidate.place_geoid for candidate in result.candidates}
    assert "0455000" in geoids
    assert "4157500" in geoids


def test_cdp_is_a_first_class_place(index: CensusPlaceIndex) -> None:
    paradise = index.resolve(PlaceLookupQuery(raw_text="Paradise, NV"))
    metairie = index.resolve(PlaceLookupQuery(raw_text="Metairie, LA"))
    assert paradise.identity is not None
    assert metairie.identity is not None
    assert paradise.identity.place_geoid == "3254600"
    assert paradise.identity.place_type is PlaceType.CDP
    assert metairie.identity.place_geoid == "2250115"
    assert metairie.identity.place_type is PlaceType.CDP


def test_within_state_city_versus_cdp_is_ambiguous(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Cottonwood, AZ"))
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    types = {candidate.place_type for candidate in result.candidates}
    assert types == {PlaceType.INCORPORATED, PlaceType.CDP}


def test_geoid_lookup_and_invalid_shapes(index: CensusPlaceIndex) -> None:
    ok = index.resolve(PlaceLookupQuery(place_geoid="1714000"))
    assert ok.identity is not None and ok.identity.place_geoid == "1714000"
    assert index.resolve(PlaceLookupQuery(place_geoid="16980")).failure is (
        PlaceIdentityFailure.INVALID_PLACE_GEOID
    )
    assert index.resolve(PlaceLookupQuery(place_geoid="2502109175")).failure is (
        PlaceIdentityFailure.INVALID_PLACE_GEOID
    )
    assert index.resolve(PlaceLookupQuery(place_geoid="1799999")).failure is (
        PlaceIdentityFailure.UNKNOWN_PLACE
    )


def test_unknown_place_name(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Not A Real City, IL"))
    assert result.failure is PlaceIdentityFailure.UNKNOWN_PLACE


def test_alaska_hawaii_puerto_rico_are_unsupported_on_default_scope(
    index: CensusPlaceIndex,
) -> None:
    assert index.resolve(PlaceLookupQuery(raw_text="Anchorage, AK")).failure is (
        PlaceIdentityFailure.UNSUPPORTED_SCOPE
    )
    assert index.resolve(PlaceLookupQuery(raw_text="Urban Honolulu, HI")).failure is (
        PlaceIdentityFailure.UNSUPPORTED_SCOPE
    )
    assert index.resolve(PlaceLookupQuery(raw_text="San Juan, PR")).failure is (
        PlaceIdentityFailure.UNSUPPORTED_SCOPE
    )


def test_explicit_hawaii_scope_resolves_urban_honolulu(index: CensusPlaceIndex) -> None:
    result = index.resolve(
        PlaceLookupQuery(
            raw_text="Urban Honolulu, HI",
            allowed_scope=PlaceScope.HAWAII,
        )
    )
    assert result.ok
    assert result.identity is not None
    assert result.identity.place_geoid == "1571550"
    assert result.identity.place_type is PlaceType.CDP


def test_washington_dc_is_in_conus_plus_dc_scope(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Washington, DC"))
    assert result.ok
    assert result.identity is not None
    assert result.identity.place_geoid == "1150000"


def test_vintage_mismatch_is_explicit(index: CensusPlaceIndex) -> None:
    result = index.resolve(
        PlaceLookupQuery(raw_text="Chicago, IL", source_vintage="US_CENSUS_GAZETTEER.PLACE.2024")
    )
    assert result.failure is PlaceIdentityFailure.VINTAGE_MISMATCH


def test_compact_index_is_small(index: CensusPlaceIndex) -> None:
    blob = compact_index_bytes(list(index.by_geoid.values()))
    assert blob.startswith(b"GEOID|USPS|STATEFP|")
    assert b"1714000|IL|17|25|A|Chicago city|" in blob
    assert len(blob) < 10_000


def test_consolidated_city_balance_is_a_valid_geoid(index: CensusPlaceIndex) -> None:
    by_name = index.resolve(PlaceLookupQuery(raw_text="Indianapolis, IN"))
    by_geoid = index.resolve(PlaceLookupQuery(place_geoid="1836003"))
    assert by_name.ok and by_name.identity is not None
    assert by_geoid.ok and by_geoid.identity is not None
    assert by_name.identity.place_geoid == "1836003"
    assert by_name.identity.place_name == "Indianapolis"
    assert by_name.identity.place_type is PlaceType.CONSOLIDATED_CITY_BALANCE
    assert by_geoid.identity.place_type is PlaceType.CONSOLIDATED_CITY_BALANCE


def test_lsad_00_proper_name_keeps_title_case_city(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Carson City, NV"))
    assert result.ok and result.identity is not None
    assert result.identity.place_geoid == "3209700"
    assert result.identity.place_name == "Carson City"
    assert result.identity.place_type is PlaceType.CONSOLIDATED_CITY_BALANCE


def test_island_area_geoid_and_state_are_unsupported_scope(
    index: CensusPlaceIndex,
) -> None:
    geoid = index.resolve(PlaceLookupQuery(place_geoid="6600001"))
    name = index.resolve(PlaceLookupQuery(raw_text="Pago Pago, AS"))
    assert geoid.failure is PlaceIdentityFailure.UNSUPPORTED_SCOPE
    assert name.failure is PlaceIdentityFailure.UNSUPPORTED_SCOPE


def test_alaska_geoid_is_unsupported_on_default_scope(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(place_geoid="0203000"))
    assert result.failure is PlaceIdentityFailure.UNSUPPORTED_SCOPE
    enabled = index.resolve(
        PlaceLookupQuery(place_geoid="0203000", allowed_scope=PlaceScope.ALASKA)
    )
    assert enabled.ok and enabled.identity is not None
    assert enabled.identity.place_geoid == "0203000"


def test_geoid_wins_over_conflicting_name(index: CensusPlaceIndex) -> None:
    result = index.resolve(
        PlaceLookupQuery(place_geoid="1714000", raw_text="Springfield, MO")
    )
    assert result.ok and result.identity is not None
    assert result.identity.place_geoid == "1714000"


def test_whitespace_geoid_normalizes(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(place_geoid=" 1714000 "))
    assert result.ok and result.identity is not None
    assert result.identity.place_geoid == "1714000"


def test_ambiguous_candidates_are_geoid_sorted(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Springfield"))
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    geoids = [candidate.place_geoid for candidate in result.candidates]
    assert geoids == sorted(geoids)
    assert result.identity is None


def test_no_largest_city_tie_break_on_bare_springfield(index: CensusPlaceIndex) -> None:
    result = index.resolve(PlaceLookupQuery(raw_text="Springfield"))
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    geoids = {candidate.place_geoid for candidate in result.candidates}
    assert "1772000" in geoids
    assert "2970000" in geoids
    assert result.identity is None


def test_tab_delimited_official_gazetteer_parses() -> None:
    text = (
        "USPS\tGEOID\tGEOIDFQ\tNAME\tLSAD\tFUNCSTAT\n"
        "IL\t1714000\t1600000US1714000\tChicago city\t25\tA\n"
    )
    places = parse_gazetteer_places(text)
    assert len(places) == 1
    assert places[0].place_geoid == "1714000"
    assert places[0].place_name == "Chicago"


def test_non_2025_gazetteer_vintage_cannot_be_loaded() -> None:
    with pytest.raises(ValueError, match="US_CENSUS_GAZETTEER.PLACE.2025"):
        parse_gazetteer_places(
            "USPS|GEOID|NAME|LSAD|FUNCSTAT\nIL|1714000|Chicago city|25|A\n",
            source_vintage="US_CENSUS_GAZETTEER.PLACE.2024",
        )


def test_lookup_module_has_no_vendor_or_city_special_cases() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "census_place_lookup.py"
    ).read_text(encoding="utf-8").casefold()
    assert "fortyguard" not in source
    assert "phoenix-demo" not in source
    assert "if phoenix" not in source
    assert "largest" not in source


@pytest.mark.skipif(not LIVE_GAZETTEER.is_file(), reason="full 2025 Gazetteer not downloaded")
def test_live_2025_gazetteer_chicago_and_springfield_counts() -> None:
    live = CensusPlaceIndex.from_path(LIVE_GAZETTEER)
    assert len(live.by_geoid) == 32350
    chicago = live.resolve(PlaceLookupQuery(raw_text="Chicago, IL"))
    assert chicago.identity is not None
    assert chicago.identity.place_geoid == "1714000"
    bare = live.resolve(PlaceLookupQuery(raw_text="Springfield"))
    assert bare.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    assert len(bare.candidates) == 22
    illinois = live.resolve(PlaceLookupQuery(raw_text="Springfield, IL"))
    missouri = live.resolve(PlaceLookupQuery(raw_text="Springfield, MO"))
    assert illinois.identity is not None
    assert missouri.identity is not None
    assert illinois.identity.place_geoid == "1772000"
    assert missouri.identity.place_geoid == "2970000"
    indy = live.resolve(PlaceLookupQuery(raw_text="Indianapolis, IN"))
    assert indy.identity is not None
    assert indy.identity.place_geoid == "1836003"
    assert indy.identity.place_type is PlaceType.CONSOLIDATED_CITY_BALANCE
    assert indy.identity.place_name == "Indianapolis"
    bare_phoenix = live.resolve(PlaceLookupQuery(raw_text="Phoenix"))
    assert bare_phoenix.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE
    assert bare_phoenix.identity is None
