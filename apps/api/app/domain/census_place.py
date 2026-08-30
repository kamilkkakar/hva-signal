"""Zero-vendor Census place identity contract.

Canonical backend entity is a Census *place* (incorporated place or CDP)
identified by the 7-digit place GEOID (state FIPS + place FIPS). Vintage is
frozen to 2025 so identity matches Phoenix TIGER/Line 2025 tracts.

This module is identity only. It does not fetch thermal data, open a public
route, or special-case any demo area.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PLACE_IDENTITY_VINTAGE = "US_CENSUS_GAZETTEER.PLACE.2025"
PLACE_GEOMETRY_VINTAGE = "US_CENSUS_TIGERLINE.PLACE.2025"
TRACT_GEOMETRY_VINTAGE = "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025"
SOURCE_VINTAGE_YEAR = 2025
GAZETTEER_PLACE_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2025_Gazetteer/2025_Gaz_place_national.zip"
)
TIGER_PLACE_DIR_URL = "https://www2.census.gov/geo/tiger/TIGER2025/PLACE/"
GEOIDFQ_PREFIX = "1600000US"

# Gazetteer 2025 covers 50 states + DC + PR. Island Areas are TIGER-only.
GAZETTEER_STATE_FIPS = frozenset(
    {
        "01",
        "02",
        "04",
        "05",
        "06",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "53",
        "54",
        "55",
        "56",
        "72",
    }
)
# C 04 / policy pin: CONUS + DC only. Not derived from “all Gazetteer minus a few”.
CONUS_PLUS_DC_FIPS = frozenset(
    {
        "01",
        "04",
        "05",
        "06",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
        "36",
        "37",
        "38",
        "39",
        "40",
        "41",
        "42",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "50",
        "51",
        "53",
        "54",
        "55",
        "56",
    }
)
ALASKA_FIPS = "02"
HAWAII_FIPS = "15"
PUERTO_RICO_FIPS = "72"
ISLAND_AREA_FIPS = frozenset({"60", "66", "69", "78"})
UNSUPPORTED_DEFAULT_SCOPE_FIPS = frozenset(
    {ALASKA_FIPS, HAWAII_FIPS, PUERTO_RICO_FIPS, *ISLAND_AREA_FIPS}
)

# Official LSAD codes observed on 2025 Gazetteer places, plus documented CDP codes.
CDP_LSAD_CODES = frozenset({"57", "55", "62"})
LSAD_SUFFIX_BY_CODE: dict[str, tuple[str, ...]] = {
    "00": ("(balance)",),
    "21": ("borough",),
    "25": ("city",),
    "37": ("municipality",),
    "43": ("town",),
    "47": ("village",),
    "53": ("city and borough",),
    "55": ("comunidad",),
    "57": ("cdp",),
    "62": ("zona urbana",),
}
# Gazetteer legal-status suffixes are lowercase except CDP. "Carson City" keeps City.
_LEGAL_NAME_SUFFIXES: tuple[str, ...] = (
    "city and borough",
    "zona urbana",
    "municipality",
    "comunidad",
    "borough",
    "village",
    "town",
    "city",
    "CDP",
    "cdp",
)

USPS_TO_FIPS: dict[str, str] = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "DC": "11",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
    "AS": "60",
    "GU": "66",
    "MP": "69",
    "PR": "72",
    "VI": "78",
}
FIPS_TO_USPS = {fips: usps for usps, fips in USPS_TO_FIPS.items()}


class PlaceType(str, Enum):
    INCORPORATED = "incorporated"
    CDP = "cdp"
    CONSOLIDATED_CITY_BALANCE = "consolidated_city_balance"


class PlaceScope(str, Enum):
    CONUS_PLUS_DC = "conus_plus_dc"
    ALASKA = "alaska"
    HAWAII = "hawaii"
    PUERTO_RICO = "puerto_rico"
    ISLAND_AREA = "island_area"


class PlaceIdentityFailure(str, Enum):
    UNKNOWN_PLACE = "UNKNOWN_PLACE"
    AMBIGUOUS_PLACE = "AMBIGUOUS_PLACE"
    INVALID_PLACE_GEOID = "INVALID_PLACE_GEOID"
    UNSUPPORTED_SCOPE = "UNSUPPORTED_SCOPE"
    VINTAGE_MISMATCH = "VINTAGE_MISMATCH"


class CensusPlaceIdentity(BaseModel):
    """Canonical zero-vendor identity for a user-selected city."""

    model_config = ConfigDict(extra="forbid")

    place_geoid: str = Field(min_length=7, max_length=7)
    place_name: str
    official_name: str
    state_fips: str = Field(min_length=2, max_length=2)
    state_abbreviation: str = Field(min_length=2, max_length=2)
    display_name: str
    place_type: PlaceType
    lsad: str
    funcstat: str
    source_vintage: str = PLACE_IDENTITY_VINTAGE
    geoidfq: str | None = None
    scope: PlaceScope

    @field_validator("place_geoid")
    @classmethod
    def _geoid_digits(cls, value: str) -> str:
        geoid = value.strip()
        if not geoid.isdigit() or len(geoid) != 7:
            raise ValueError("place_geoid must be a 7-digit Census place GEOID")
        return geoid

    @field_validator("state_fips")
    @classmethod
    def _fips_digits(cls, value: str) -> str:
        fips = value.strip()
        if not fips.isdigit() or len(fips) != 2:
            raise ValueError("state_fips must be a 2-digit state FIPS code")
        return fips

    @field_validator("state_abbreviation")
    @classmethod
    def _usps_upper(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("source_vintage")
    @classmethod
    def _frozen_2025_vintage(cls, value: str) -> str:
        if value != PLACE_IDENTITY_VINTAGE:
            raise ValueError("place identity vintage is frozen to US_CENSUS_GAZETTEER.PLACE.2025")
        return value

    @model_validator(mode="after")
    def _state_matches_geoid(self) -> CensusPlaceIdentity:
        if self.place_geoid[:2] != self.state_fips:
            raise ValueError("state_fips must equal place_geoid STATEFP")
        expected_usps = FIPS_TO_USPS.get(self.state_fips)
        if expected_usps is not None and expected_usps != self.state_abbreviation:
            raise ValueError("state_abbreviation must match state_fips")
        return self


class PlaceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    place_geoid: str
    official_name: str
    state_abbreviation: str
    place_type: PlaceType
    display_name: str


class PlaceLookupQuery(BaseModel):
    """Name and/or GEOID query. Not a public request body."""

    model_config = ConfigDict(extra="forbid")

    raw_text: str | None = None
    place_geoid: str | None = None
    place_name: str | None = None
    state_abbreviation: str | None = None
    state_fips: str | None = None
    source_vintage: str = PLACE_IDENTITY_VINTAGE
    allowed_scope: PlaceScope = PlaceScope.CONUS_PLUS_DC


class PlaceLookupResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    identity: CensusPlaceIdentity | None = None
    failure: PlaceIdentityFailure | None = None
    message: str | None = None
    candidates: list[PlaceCandidate] = Field(default_factory=list)


def classify_place_type(*, lsad: str, official_name: str, funcstat: str) -> PlaceType:
    if "(balance)" in official_name.casefold() or lsad == "00":
        return PlaceType.CONSOLIDATED_CITY_BALANCE
    if lsad in CDP_LSAD_CODES or funcstat == "S":
        return PlaceType.CDP
    return PlaceType.INCORPORATED


def scope_for_state_fips(state_fips: str) -> PlaceScope:
    if state_fips in ISLAND_AREA_FIPS:
        return PlaceScope.ISLAND_AREA
    if state_fips == ALASKA_FIPS:
        return PlaceScope.ALASKA
    if state_fips == HAWAII_FIPS:
        return PlaceScope.HAWAII
    if state_fips == PUERTO_RICO_FIPS:
        return PlaceScope.PUERTO_RICO
    if state_fips in CONUS_PLUS_DC_FIPS:
        return PlaceScope.CONUS_PLUS_DC
    raise ValueError(f"unrecognized state FIPS {state_fips!r}")


def scope_is_allowed(place_scope: PlaceScope, allowed: PlaceScope) -> bool:
    if allowed == PlaceScope.CONUS_PLUS_DC:
        return place_scope == PlaceScope.CONUS_PLUS_DC
    return place_scope == allowed


def _legal_suffix_tokens(lsad: str) -> tuple[str, ...]:
    specific = [item for item in LSAD_SUFFIX_BY_CODE.get(lsad, ()) if item != "(balance)"]
    seen: set[str] = set()
    ordered: list[str] = []
    for suffix in [*specific, *_LEGAL_NAME_SUFFIXES]:
        if suffix not in seen:
            seen.add(suffix)
            ordered.append(suffix)
    ordered.sort(key=len, reverse=True)
    return tuple(ordered)


def strip_lsad_suffix(official_name: str, lsad: str) -> str:
    """Return the Census short name (TIGER NAME equivalent).

    Gazetteer legal-status suffixes are lowercase (` city`) except ` CDP`.
    Title-case tokens that are part of the proper name (Carson City) stay.
    Consolidated remainder rows lose trailing ` (balance)` and then ` city`.
    """
    text = official_name.strip()
    if text.casefold().endswith(" (balance)"):
        text = text[: -len(" (balance)")].rstrip()
    for suffix in _legal_suffix_tokens(lsad):
        token = f" {suffix}"
        if text.endswith(token):
            text = text[: -len(token)].rstrip()
            break
    return text or official_name.strip()


def normalize_place_name(value: str, lsad: str | None = None) -> str:
    text = " ".join(value.replace(",", " ").split()).casefold()
    tokens = text.split()
    if len(tokens) >= 2 and tokens[-1].upper() in USPS_TO_FIPS:
        text = " ".join(tokens[:-1])
    return strip_lsad_suffix(text, lsad or "").casefold()


def parse_user_place_text(raw: str) -> tuple[str | None, str | None, str | None]:
    """Split 'Chicago, IL' / '1714000' into (name, usps, geoid)."""
    text = " ".join(raw.replace(";", ",").split()).strip()
    if not text:
        return None, None, None
    compact = text.replace(" ", "")
    if compact.isdigit() and len(compact) == 7:
        return None, None, compact
    if "," in text:
        left, right = text.rsplit(",", 1)
        maybe_state = right.strip().upper()
        if maybe_state in USPS_TO_FIPS:
            return left.strip() or None, maybe_state, None
    tokens = text.split()
    if len(tokens) >= 2 and tokens[-1].upper() in USPS_TO_FIPS:
        return " ".join(tokens[:-1]) or None, tokens[-1].upper(), None
    return text, None, None


def validate_place_geoid_format(value: str) -> PlaceIdentityFailure | None:
    geoid = value.strip()
    if not geoid.isdigit() or len(geoid) != 7:
        return PlaceIdentityFailure.INVALID_PLACE_GEOID
    if geoid[:2] not in FIPS_TO_USPS:
        return PlaceIdentityFailure.INVALID_PLACE_GEOID
    return None


def display_name_for(place_name: str, state_abbreviation: str) -> str:
    return f"{place_name}, {state_abbreviation.upper()}"
