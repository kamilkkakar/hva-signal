"""Deterministic Census place lookup over a frozen 2025 Gazetteer table.

Loads official pipe-delimited Gazetteer place rows (or a compact subset) and
resolves name/GEOID queries. No network, no public route, no vendor calls.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.domain.census_place import (
    FIPS_TO_USPS,
    GEOIDFQ_PREFIX,
    PLACE_IDENTITY_VINTAGE,
    USPS_TO_FIPS,
    CensusPlaceIdentity,
    PlaceCandidate,
    PlaceIdentityFailure,
    PlaceLookupQuery,
    PlaceLookupResult,
    PlaceScope,
    classify_place_type,
    display_name_for,
    normalize_place_name,
    parse_user_place_text,
    scope_for_state_fips,
    scope_is_allowed,
    strip_lsad_suffix,
    validate_place_geoid_format,
)

GAZETTEER_REQUIRED_COLUMNS = (
    "USPS",
    "GEOID",
    "NAME",
    "LSAD",
    "FUNCSTAT",
)


def _gazetteer_delimiter(header_line: str) -> str:
    pipes = header_line.count("|")
    tabs = header_line.count("\t")
    if pipes >= 4 and pipes >= tabs:
        return "|"
    if tabs >= 4:
        return "\t"
    raise ValueError("gazetteer header is neither pipe- nor tab-delimited")


def parse_gazetteer_places(text: str, *, source_vintage: str = PLACE_IDENTITY_VINTAGE) -> list[CensusPlaceIdentity]:
    if source_vintage != PLACE_IDENTITY_VINTAGE:
        raise ValueError(f"only {PLACE_IDENTITY_VINTAGE} may be loaded")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("gazetteer text is empty")
    delimiter = _gazetteer_delimiter(lines[0])
    header = [col.strip() for col in lines[0].split(delimiter)]
    missing = [col for col in GAZETTEER_REQUIRED_COLUMNS if col not in header]
    if missing:
        raise ValueError(f"gazetteer missing columns: {missing}")
    index = {name: i for i, name in enumerate(header)}
    places: list[CensusPlaceIdentity] = []
    seen: set[str] = set()
    for line in lines[1:]:
        cols = [part.strip() for part in line.split(delimiter)]
        if len(cols) < len(header):
            raise ValueError(f"gazetteer row has {len(cols)} columns, expected {len(header)}")
        geoid = cols[index["GEOID"]]
        if geoid in seen:
            raise ValueError(f"duplicate place GEOID {geoid}")
        failure = validate_place_geoid_format(geoid)
        if failure is not None:
            raise ValueError(f"invalid gazetteer GEOID {geoid!r}")
        official_name = cols[index["NAME"]]
        lsad = cols[index["LSAD"]]
        usps = cols[index["USPS"]].upper()
        state_fips = geoid[:2]
        expected_usps = FIPS_TO_USPS.get(state_fips)
        if expected_usps is None or expected_usps != usps:
            raise ValueError(f"USPS {usps!r} does not match GEOID {geoid}")
        place_name = strip_lsad_suffix(official_name, lsad)
        geoidfq = cols[index["GEOIDFQ"]] if "GEOIDFQ" in index and index["GEOIDFQ"] < len(cols) else None
        if geoidfq and geoidfq != f"{GEOIDFQ_PREFIX}{geoid}":
            raise ValueError(f"GEOIDFQ {geoidfq!r} does not match GEOID {geoid}")
        places.append(
            CensusPlaceIdentity(
                place_geoid=geoid,
                place_name=place_name,
                official_name=official_name,
                state_fips=state_fips,
                state_abbreviation=usps,
                display_name=display_name_for(place_name, usps),
                place_type=classify_place_type(
                    lsad=lsad,
                    official_name=official_name,
                    funcstat=cols[index["FUNCSTAT"]],
                ),
                lsad=lsad,
                funcstat=cols[index["FUNCSTAT"]],
                source_vintage=source_vintage,
                geoidfq=geoidfq or f"{GEOIDFQ_PREFIX}{geoid}",
                scope=scope_for_state_fips(state_fips),
            )
        )
        seen.add(geoid)
    return places


def load_gazetteer_places(path: Path, *, source_vintage: str = PLACE_IDENTITY_VINTAGE) -> list[CensusPlaceIdentity]:
    return parse_gazetteer_places(
        path.read_text(encoding="utf-8-sig"),
        source_vintage=source_vintage,
    )


def compact_index_bytes(places: list[CensusPlaceIdentity]) -> bytes:
    """Pipe table with identity fields only. Suitable for a small national index."""
    rows = [
        "GEOID|USPS|STATEFP|LSAD|FUNCSTAT|NAME|PLACE_TYPE|SCOPE",
    ]
    for place in places:
        rows.append(
            "|".join(
                [
                    place.place_geoid,
                    place.state_abbreviation,
                    place.state_fips,
                    place.lsad,
                    place.funcstat,
                    place.official_name,
                    place.place_type.value,
                    place.scope.value,
                ]
            )
        )
    return ("\n".join(rows) + "\n").encode("utf-8")


class CensusPlaceIndex:
    def __init__(self, places: list[CensusPlaceIdentity]) -> None:
        vintages = {place.source_vintage for place in places}
        if len(vintages) != 1:
            raise ValueError(f"index must be a single vintage, got {sorted(vintages)}")
        self.source_vintage = next(iter(vintages))
        self.by_geoid = {place.place_geoid: place for place in places}
        self._by_name: dict[str, list[CensusPlaceIdentity]] = defaultdict(list)
        self._by_name_state: dict[tuple[str, str], list[CensusPlaceIdentity]] = defaultdict(list)
        for place in places:
            key = normalize_place_name(place.official_name, place.lsad)
            self._by_name[key].append(place)
            self._by_name_state[(key, place.state_abbreviation)].append(place)

    @classmethod
    def from_gazetteer_text(
        cls,
        text: str,
        *,
        source_vintage: str = PLACE_IDENTITY_VINTAGE,
    ) -> CensusPlaceIndex:
        return cls(parse_gazetteer_places(text, source_vintage=source_vintage))

    @classmethod
    def from_path(cls, path: Path, *, source_vintage: str = PLACE_IDENTITY_VINTAGE) -> CensusPlaceIndex:
        return cls(load_gazetteer_places(path, source_vintage=source_vintage))

    def get(self, place_geoid: str) -> CensusPlaceIdentity | None:
        return self.by_geoid.get(place_geoid)

    def resolve(self, query: PlaceLookupQuery) -> PlaceLookupResult:
        if query.source_vintage != self.source_vintage:
            return PlaceLookupResult(
                ok=False,
                failure=PlaceIdentityFailure.VINTAGE_MISMATCH,
                message=(
                    f"query vintage {query.source_vintage} does not match "
                    f"index vintage {self.source_vintage}"
                ),
            )

        geoid = query.place_geoid
        name = query.place_name
        state = query.state_abbreviation.upper() if query.state_abbreviation else None
        if query.state_fips:
            derived = FIPS_TO_USPS.get(query.state_fips)
            if derived is None:
                return PlaceLookupResult(
                    ok=False,
                    failure=PlaceIdentityFailure.INVALID_PLACE_GEOID,
                    message=f"unknown state FIPS {query.state_fips}",
                )
            if state and state != derived:
                return PlaceLookupResult(
                    ok=False,
                    failure=PlaceIdentityFailure.AMBIGUOUS_PLACE,
                    message="state_abbreviation and state_fips disagree",
                )
            state = derived
        if query.raw_text:
            parsed_name, parsed_state, parsed_geoid = parse_user_place_text(query.raw_text)
            geoid = geoid or parsed_geoid
            name = name or parsed_name
            state = state or parsed_state

        if geoid is not None:
            return self._resolve_geoid(geoid, allowed=query.allowed_scope)
        if name:
            return self._resolve_name(name, state, allowed=query.allowed_scope)
        return PlaceLookupResult(
            ok=False,
            failure=PlaceIdentityFailure.UNKNOWN_PLACE,
            message="query has neither place_geoid nor a place name",
        )

    def _finish(
        self,
        matches: list[CensusPlaceIdentity],
        *,
        allowed: PlaceScope,
        empty_message: str,
    ) -> PlaceLookupResult:
        if not matches:
            return PlaceLookupResult(
                ok=False,
                failure=PlaceIdentityFailure.UNKNOWN_PLACE,
                message=empty_message,
            )
        in_scope = [place for place in matches if scope_is_allowed(place.scope, allowed)]
        if not in_scope:
            return PlaceLookupResult(
                ok=False,
                failure=PlaceIdentityFailure.UNSUPPORTED_SCOPE,
                message=(
                    f"{len(matches)} official place(s) are outside allowed scope "
                    f"{allowed.value}"
                ),
                candidates=_candidates(matches),
            )
        if len(in_scope) > 1:
            return PlaceLookupResult(
                ok=False,
                failure=PlaceIdentityFailure.AMBIGUOUS_PLACE,
                message=f"{len(in_scope)} official places match; require state or GEOID",
                candidates=_candidates(in_scope),
            )
        return PlaceLookupResult(ok=True, identity=in_scope[0])

    def _resolve_geoid(self, geoid: str, *, allowed: PlaceScope) -> PlaceLookupResult:
        geoid = geoid.strip()
        failure = validate_place_geoid_format(geoid)
        if failure is not None:
            return PlaceLookupResult(
                ok=False,
                failure=failure,
                message="place_geoid must be the 7-digit Census place identifier",
            )
        place_scope = scope_for_state_fips(geoid[:2])
        place = self.by_geoid.get(geoid)
        if place is None:
            if place_scope == PlaceScope.ISLAND_AREA and not scope_is_allowed(
                place_scope, allowed
            ):
                return PlaceLookupResult(
                    ok=False,
                    failure=PlaceIdentityFailure.UNSUPPORTED_SCOPE,
                    message=(
                        f"Island Area GEOID {geoid} is outside allowed scope "
                        f"{allowed.value}"
                    ),
                )
            return PlaceLookupResult(
                ok=False,
                failure=PlaceIdentityFailure.UNKNOWN_PLACE,
                message=f"GEOID {geoid} is not in vintage {self.source_vintage}",
            )
        return self._finish([place], allowed=allowed, empty_message="not found")

    def _resolve_name(
        self,
        name: str,
        state: str | None,
        *,
        allowed: PlaceScope,
    ) -> PlaceLookupResult:
        key = normalize_place_name(name)
        if not key:
            return PlaceLookupResult(
                ok=False,
                failure=PlaceIdentityFailure.UNKNOWN_PLACE,
                message="empty place name",
            )
        if state:
            usps = state.upper()
            state_fips = USPS_TO_FIPS.get(usps)
            if state_fips is None:
                return PlaceLookupResult(
                    ok=False,
                    failure=PlaceIdentityFailure.UNKNOWN_PLACE,
                    message=f"unknown state abbreviation {state}",
                )
            state_scope = scope_for_state_fips(state_fips)
            matches = list(self._by_name_state.get((key, usps), ()))
            if (
                not matches
                and state_scope == PlaceScope.ISLAND_AREA
                and not scope_is_allowed(state_scope, allowed)
            ):
                return PlaceLookupResult(
                    ok=False,
                    failure=PlaceIdentityFailure.UNSUPPORTED_SCOPE,
                    message=(
                        f"Island Areas are outside allowed scope {allowed.value}; "
                        "2025 Gazetteer identity does not cover AS/GU/MP/VI"
                    ),
                )
            return self._finish(
                matches,
                allowed=allowed,
                empty_message=f"no 2025 Census place named {name!r} in {state}",
            )
        matches = list(self._by_name.get(key, ()))
        return self._finish(
            matches,
            allowed=allowed,
            empty_message=f"no 2025 Census place named {name!r}",
        )


def _candidates(places: list[CensusPlaceIdentity]) -> list[PlaceCandidate]:
    return [_candidate(place) for place in sorted(places, key=lambda item: item.place_geoid)]


def _candidate(place: CensusPlaceIdentity) -> PlaceCandidate:
    return PlaceCandidate(
        place_geoid=place.place_geoid,
        official_name=place.official_name,
        state_abbreviation=place.state_abbreviation,
        place_type=place.place_type,
        display_name=place.display_name,
    )
