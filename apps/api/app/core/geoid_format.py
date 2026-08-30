"""Census GEOID format checks. Fail closed. No Census HTTP. Not identity."""

from __future__ import annotations

import re

PLACE_GEOID_PATTERN = re.compile(r"^[0-9]{7}$")
TRACT_GEOID_PATTERN = re.compile(r"^[0-9]{11}$")
CENSUS_VINTAGE_PATTERN = re.compile(r"^[0-9]{4}$")

REASON_INVALID_PLACE_GEOID = "INVALID_PLACE_GEOID"
REASON_INVALID_TRACT_GEOID = "INVALID_TRACT_GEOID"
REASON_GEOID_STATE_MISMATCH = "GEOID_STATE_MISMATCH"
REASON_INVALID_CENSUS_VINTAGE = "INVALID_CENSUS_VINTAGE"


class GeoidFormatError(ValueError):
    """Malformed place/tract GEOID or STATEFP mismatch."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


def _ascii_digit_token(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if value != value.strip() or any(ch.isspace() for ch in value):
        return None
    if not value.isascii() or not value.isdigit():
        return None
    return value


def is_place_geoid(value: object) -> bool:
    token = _ascii_digit_token(value)
    return token is not None and PLACE_GEOID_PATTERN.fullmatch(token) is not None


def is_tract_geoid(value: object) -> bool:
    token = _ascii_digit_token(value)
    return token is not None and TRACT_GEOID_PATTERN.fullmatch(token) is not None


def is_census_vintage(value: object) -> bool:
    token = _ascii_digit_token(value)
    return token is not None and CENSUS_VINTAGE_PATTERN.fullmatch(token) is not None


def require_place_geoid(value: object) -> str:
    if not is_place_geoid(value):
        raise GeoidFormatError(
            REASON_INVALID_PLACE_GEOID,
            "place GEOID must be exactly 7 ASCII digits",
        )
    return str(value)


def require_tract_geoid(value: object) -> str:
    if not is_tract_geoid(value):
        raise GeoidFormatError(
            REASON_INVALID_TRACT_GEOID,
            "tract GEOID must be exactly 11 ASCII digits",
        )
    return str(value)


def require_census_vintage(value: object) -> str:
    if not is_census_vintage(value):
        raise GeoidFormatError(
            REASON_INVALID_CENSUS_VINTAGE,
            "census vintage must be exactly 4 ASCII digits",
        )
    return str(value)


def tract_state_matches_place(tract: object, place: object) -> bool:
    try:
        return require_tract_geoid(tract)[:2] == require_place_geoid(place)[:2]
    except GeoidFormatError:
        return False


def require_tract_for_place(tract: object, place: object) -> str:
    """11-digit tract whose STATEFP prefix matches the 7-digit place."""
    token = require_tract_geoid(tract)
    place_token = require_place_geoid(place)
    if token[:2] != place_token[:2]:
        raise GeoidFormatError(
            REASON_GEOID_STATE_MISMATCH,
            "tract STATEFP must match place STATEFP",
        )
    return token
