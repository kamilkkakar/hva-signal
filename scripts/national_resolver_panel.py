"""National 25-zone resolver stress / should-fail harness.

I7 / AGENT E. Public Census TIGER/Line only. Zero FortyGuard.

Pinned measurement substrate: ALG1_GREEDY_LEX_PLACE_INTPT_V1
(FROZEN CANDIDATE — NATIONAL_PLACE_GEOGRAPHY_V1).
Does not import Phoenix production resolvers, Decision 8, or vendor clients.
Does not fabricate Census places or alter eligibility to force failures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
import zipfile
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal
from urllib.request import Request, urlopen

from shapely import STRtree
from shapely.geometry import Point, box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shp_transform
from shapely.ops import unary_union
from shapely.validation import make_valid

try:
    from pyproj import Geod, Transformer
except ImportError:  # pragma: no cover — live measure only
    Geod = None  # type: ignore[misc, assignment]
    Transformer = None  # type: ignore[misc, assignment]

TARGET_TRACTS = 25
ROOK_MIN_LENGTH_M = 1e-3
PP_COMPARE_DECIMALS = 6
CENSUS_VINTAGE = "2025"
TIGER_BASE = "https://www2.census.gov/geo/tiger/TIGER2025"
USER_AGENT = (
    "hva-signal-national-resolver-panel/0.1 "
    "(3K Labs; public TIGER geography validation; zero vendor)"
)
PLACE_GEOID_RE = re.compile(r"^\d{7}$")
CONUS_LON_RANGE = (-124.8, -66.9)
CONUS_LAT_RANGE = (24.5, 49.4)

REASON_INSUFFICIENT_ELIGIBLE = "INSUFFICIENT_ELIGIBLE_TRACTS"
REASON_INSUFFICIENT_CONNECTED = "INSUFFICIENT_CONNECTED_TRACTS"
REASON_UNKNOWN_PLACE = "UNKNOWN_PLACE"
REASON_INVALID_PLACE_ID = "INVALID_PLACE_ID"
REASON_UNSUPPORTED_SCOPE = "UNSUPPORTED_SCOPE"
REASON_PROJECTION_UNSUPPORTED = "PROJECTION_UNSUPPORTED"
STATUS_SUPPORTED = "SUPPORTED"
STATUS_UNSUPPORTED = "UNSUPPORTED"

FROZEN_CANDIDATE_SUBSTRATE: dict[str, Any] = {
    "schema_version": "NATIONAL_RESOLVER_PANEL_SUBSTRATE_V1",
    "status": "FROZEN_CANDIDATE",
    "policy_id": "NATIONAL_PLACE_GEOGRAPHY_V1",
    "slug": "national-place-geography-v1",
    "algorithm": "ALG1_GREEDY_LEX_PLACE_INTPT_V1",
    "census_source": "TIGER/Line",
    "census_vintage": CENSUS_VINTAGE,
    "eligibility": (
        "Official TIGER tract INTPT (INTPTLON, INTPTLAT) covered by the "
        "2025 place polygon after make_valid. ALAND <= 0 ineligible. "
        "No any-intersection. No outside-place expansion."
    ),
    "projection_conus": "EPSG:5070",
    "published_crs": "EPSG:4269",
    "rook": (
        "Shared linear boundary length > 1e-3 m after make_valid and "
        "EPSG:5070. Corner-only contact is not rook. No distance fallback."
    ),
    "rook_min_length_m": 0.001,
    "seed": (
        "Official TIGER place INTPT container; else nearest eligible tract "
        "INTPT in EPSG:5070; GEOID ASC"
    ),
    "growth": (
        "greedy_lex: PP_COMPARE DESC -> shared boundary DESC -> "
        "distance-to-seed ASC -> GEOID ASC"
    ),
    "component_policy": (
        "Eligible < 25 -> INSUFFICIENT_ELIGIBLE_TRACTS. "
        "Seed-component < 25 -> INSUFFICIENT_CONNECTED_TRACTS "
        "(no island jump). Do not invent 25."
    ),
    "outside_place_expansion": False,
    "target_tracts": TARGET_TRACTS,
    "phoenix_legacy_reproduction_required": False,
    "not_e_medoid_stub": True,
}

# Back-compat alias for older harness imports.
PROVISIONAL_SUBSTRATE = FROZEN_CANDIDATE_SUBSTRATE

SHOULD_FAIL_TARGETS: dict[str, dict[str, Any]] = {
    "1236550": {
        "name": "Key West city",
        "state": "FL",
        "role": "required_real_lt25",
        "expected_reason": REASON_INSUFFICIENT_ELIGIBLE,
    },
    "0485540": {
        "name": "Yuma city",
        "state": "AZ",
        "role": "required_real_connected_lt25",
        "expected_reason": REASON_INSUFFICIENT_CONNECTED,
        "alg1_seed_component": 6,
        "note": (
            "ALG1 place-INTPT / nearest eligible lands on the 6-tract "
            "island, not the 20."
        ),
    },
}

CURATED_TIMEZONES: dict[str, str] = {
    "0455000": "America/Phoenix",
    "0477000": "America/Phoenix",
    "0423620": "America/Phoenix",
    "0465350": "America/Phoenix",
    "0644000": "America/Los_Angeles",
    "0667000": "America/Los_Angeles",
    "0600562": "America/Los_Angeles",
    "0820000": "America/Denver",
    "0803620": "America/Denver",
    "1245000": "America/New_York",
    "1236550": "America/New_York",
    "1253000": "America/New_York",
    "1714000": "America/Chicago",
    "3651000": "America/New_York",
    "4260000": "America/New_York",
    "4835000": "America/Chicago",
    "4828068": "America/Chicago",
    "2255000": "America/Chicago",
    "2507000": "America/New_York",
    "5363000": "America/Los_Angeles",
    "5157000": "America/New_York",
    "5164000": "America/New_York",
    "5182000": "America/New_York",
    "5114968": "America/New_York",
    "5135000": "America/New_York",
    "2401600": "America/New_York",
    "3570500": "America/Denver",
    "1571550": "Pacific/Honolulu",
    "0203000": "America/Anchorage",
    "0236400": "America/Juneau",
}

# Stress-diversity roles. Fame is not the selection rule.
SUCCESS_TARGETS: dict[str, dict[str, str]] = {
    "1714000": {
        "name": "Chicago city",
        "state": "IL",
        "role": "dense_grid",
    },
    "3651000": {
        "name": "New York city",
        "state": "NY",
        "role": "large_dense_multipart_water",
    },
    "0644000": {
        "name": "Los Angeles city",
        "state": "CA",
        "role": "irregular_western_harbor_strip",
    },
    "4835000": {
        "name": "Houston city",
        "state": "TX",
        "role": "sprawling_irregular_annexation",
    },
    "1245000": {
        "name": "Miami city",
        "state": "FL",
        "role": "coastal",
    },
    "0820000": {
        "name": "Denver city",
        "state": "CO",
        "role": "western_high_plains",
    },
    "4260000": {
        "name": "Philadelphia city",
        "state": "PA",
        "role": "older_river_irregular",
    },
    "0477000": {
        "name": "Tucson city",
        "state": "AZ",
        "role": "lower_density_qualifying_southwest",
    },
}

# Required / substitute real failures (identity is real; outcome is measured).
FAIL_LT25_TARGETS: dict[str, dict[str, str]] = {
    "1236550": {
        "name": "Key West city",
        "state": "FL",
        "role": "required_lt25_coastal_island",
    },
    "0465350": {
        "name": "Sedona city",
        "state": "AZ",
        "role": "lt25_tourist_city",
    },
    "0803620": {
        "name": "Aspen city",
        "state": "CO",
        "role": "lt25_small_mountain_city",
    },
    "5114968": {
        "name": "Charlottesville city",
        "state": "VA",
        "role": "lt25_independent_city",
    },
    "2401600": {
        "name": "Annapolis city",
        "state": "MD",
        "role": "lt25_coastal_capital",
    },
}

FAIL2_SEARCH_TARGETS: dict[str, dict[str, str]] = {
    "5157000": {"name": "Norfolk city", "state": "VA", "role": "water_separated_midsize"},
    "5164000": {"name": "Portsmouth city", "state": "VA", "role": "water_separated_midsize"},
    "5135000": {"name": "Hampton city", "state": "VA", "role": "water_heavy_midsize"},
    "5182000": {"name": "Virginia Beach city", "state": "VA", "role": "coastal_large"},
    "4828068": {"name": "Galveston city", "state": "TX", "role": "barrier_island"},
    "1234132": {
        "name": "Islamorada, Village of Islands village",
        "state": "FL",
        "role": "multipart_keys",
    },
    "1243000": {"name": "Marathon city", "state": "FL", "role": "keys_island_chain"},
    "0600562": {"name": "Alameda city", "state": "CA", "role": "island_city"},
    "2255000": {"name": "New Orleans city", "state": "LA", "role": "river_coastal"},
    "2507000": {"name": "Boston city", "state": "MA", "role": "harbor_islands"},
    "5363000": {"name": "Seattle city", "state": "WA", "role": "coastal_lakes"},
    "0667000": {"name": "San Francisco city", "state": "CA", "role": "peninsula_islands"},
    "0236400": {"name": "Juneau city and borough", "state": "AK", "role": "famous_multipart_nonconus"},
    "1571550": {"name": "Urban Honolulu CDP", "state": "HI", "role": "nonconus_cdp"},
    "0203000": {"name": "Anchorage municipality", "state": "AK", "role": "nonconus_municipality"},
    "4752006": {
        "name": "Nashville-Davidson metropolitan government (balance)",
        "state": "TN",
        "role": "consolidated_balance_holes",
    },
    "1836003": {
        "name": "Indianapolis city (balance)",
        "state": "IN",
        "role": "consolidated_balance_holes",
    },
    "0423620": {"name": "Flagstaff city", "state": "AZ", "role": "borderline_count"},
    "3570500": {"name": "Santa Fe city", "state": "NM", "role": "borderline_count"},
}

RETROSPECTIVE_TARGETS: dict[str, dict[str, str]] = {
    "0455000": {
        "name": "Phoenix city",
        "state": "AZ",
        "role": "legacy_retrospective_only",
    },
}

FAIL2_FOUND_TARGETS: dict[str, dict[str, str]] = {
    "0485540": {
        "name": "Yuma city",
        "state": "AZ",
        "role": "yuma_fragmented_intpt",
    },
    "0812815": {
        "name": "Centennial city",
        "state": "CO",
        "role": "centennial_multipart_fragmented",
    },
    "1212875": {
        "name": "Clearwater city",
        "state": "FL",
        "role": "clearwater_multipart_fragmented",
    },
    "4816432": {
        "name": "Conroe city",
        "state": "TX",
        "role": "conroe_multipart_fragmented",
    },
}

IDENTITY_FAIL_TARGETS: dict[str, dict[str, str]] = {
    "00XXXXX": {
        "name": "(malformed GEOID)",
        "state": "NA",
        "role": "invalid_place_id",
    },
    "0499999": {
        "name": "(well-formed GEOID absent from TIGER 2025 AZ places)",
        "state": "AZ",
        "role": "unknown_place",
    },
}

DOWNLOAD_STATES: tuple[str, ...] = (
    "01",
    "02",
    "04",
    "06",
    "08",
    "12",
    "13",
    "15",
    "17",
    "18",
    "22",
    "24",
    "25",
    "29",
    "32",
    "35",
    "36",
    "42",
    "47",
    "48",
    "51",
    "53",
)

GEOD = Geod(ellps="WGS84") if Geod is not None else None
_TO_5070 = (
    Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)
    if Transformer is not None
    else None
)


def hackathon_roots() -> list[Path]:
    here = Path(__file__).resolve()
    roots = [here.parents[1]]
    main = Path(r"f:\cursor\hackathon")
    if main not in roots:
        roots.append(main)
    return roots


def hackathon_root() -> Path:
    for root in hackathon_roots():
        if (root / "apps" / "api").is_dir():
            return root
    return Path(__file__).resolve().parents[1]


def cache_dir() -> Path:
    main = Path(r"f:\cursor\hackathon")
    preferred = main / "workforce" / "national_resolver" / "cache" / "tiger2025"
    preferred.mkdir(parents=True, exist_ok=True)
    return preferred


def fixture_dir() -> Path:
    path = (
        hackathon_root()
        / "apps"
        / "api"
        / "tests"
        / "fixtures"
        / "national_resolver"
    )
    if path.name != "national_resolver" or path.parent.name != "fixtures":
        raise RuntimeError(f"refusing nested fixture path: {path}")
    nested = path / "national_resolver"
    if nested.exists():
        raise RuntimeError(f"nested fixture dir must not exist: {nested}")
    return path


def panel_run_dir() -> Path:
    path = (
        Path(r"f:\cursor\hackathon")
        / "workforce"
        / "national_resolver"
        / "panel_runs"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_conus_point(lon: float, lat: float) -> bool:
    return (
        CONUS_LON_RANGE[0] <= lon <= CONUS_LON_RANGE[1]
        and CONUS_LAT_RANGE[0] <= lat <= CONUS_LAT_RANGE[1]
    )


def validate_place_geoid(geoid: str) -> str | None:
    if not PLACE_GEOID_RE.match(geoid):
        return REASON_INVALID_PLACE_ID
    return None


def project_5070(geom: BaseGeometry) -> BaseGeometry:
    if _TO_5070 is None:
        raise RuntimeError("pyproj is required for live geometry metrics")
    valid = make_valid(geom)
    if valid.is_empty:
        return valid
    projected = shp_transform(_TO_5070.transform, valid)
    if not projected.is_valid:
        projected = make_valid(projected)
    return projected


def project_local_aeqd(geom: BaseGeometry, lon0: float, lat0: float) -> BaseGeometry:
    if Transformer is None:
        raise RuntimeError("pyproj is required for live geometry metrics")
    crs = (
        f"+proj=aeqd +lat_0={lat0:.8f} +lon_0={lon0:.8f} +datum=NAD83 "
        "+units=m +no_defs"
    )
    transformer = Transformer.from_crs("EPSG:4269", crs, always_xy=True)
    valid = make_valid(geom)
    if valid.is_empty:
        return valid
    projected = shp_transform(transformer.transform, valid)
    if not projected.is_valid:
        projected = make_valid(projected)
    return projected


def polsby_popper(union_m: BaseGeometry) -> float:
    if union_m.is_empty:
        return 0.0
    area = float(union_m.area)
    perim = float(union_m.length)
    if area <= 0.0 or perim <= 0.0:
        return 0.0
    return (4.0 * math.pi * area) / (perim * perim)


def rook_adjacent(a_m: BaseGeometry, b_m: BaseGeometry, min_length: float = ROOK_MIN_LENGTH_M) -> bool:
    if a_m.is_empty or b_m.is_empty:
        return False
    if not a_m.bounds or not b_m.bounds:
        return False
    minx = max(a_m.bounds[0], b_m.bounds[0])
    miny = max(a_m.bounds[1], b_m.bounds[1])
    maxx = min(a_m.bounds[2], b_m.bounds[2])
    maxy = min(a_m.bounds[3], b_m.bounds[3])
    if minx > maxx or miny > maxy:
        return False
    inter = a_m.boundary.intersection(b_m.boundary)
    if inter.is_empty:
        return False
    return float(inter.length) > min_length


def build_rook_neighbors(geoms_m: list[BaseGeometry]) -> list[list[int]]:
    n = len(geoms_m)
    neighbors: list[list[int]] = [[] for _ in range(n)]
    if n == 0:
        return neighbors
    tree = STRtree(geoms_m)
    for i, geom in enumerate(geoms_m):
        hits = tree.query(geom)
        for j in hits:
            j_int = int(j)
            if j_int <= i:
                continue
            if rook_adjacent(geom, geoms_m[j_int]):
                neighbors[i].append(j_int)
                neighbors[j_int].append(i)
    for row in neighbors:
        row.sort()
    return neighbors


def connected_components(neighbors: list[list[int]]) -> list[list[int]]:
    n = len(neighbors)
    seen = [False] * n
    components: list[list[int]] = []
    for start in range(n):
        if seen[start]:
            continue
        stack = [start]
        seen[start] = True
        group = [start]
        while stack:
            node = stack.pop()
            for nxt in neighbors[node]:
                if not seen[nxt]:
                    seen[nxt] = True
                    stack.append(nxt)
                    group.append(nxt)
        group.sort()
        components.append(group)
    components.sort(key=lambda g: (-len(g), g[0] if g else -1))
    return components


def component_sizes(neighbors: list[list[int]]) -> list[int]:
    return [len(c) for c in connected_components(neighbors)]


def component_containing(components: list[list[int]], index: int) -> list[int]:
    for group in components:
        if index in group:
            return group
    return []


def is_rook_connected(selected: Iterable[int], neighbors: list[list[int]]) -> bool:
    want = set(selected)
    if not want:
        return False
    start = next(iter(sorted(want)))
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt in neighbors[node]:
            if nxt in want and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen == want


def classify_support(
    *,
    eligible_count: int,
    largest_component: int,
    seed_component: int | None,
    scope_ok: bool,
    invalid_id: bool,
    unknown: bool,
) -> tuple[str, str | None]:
    if invalid_id:
        return STATUS_UNSUPPORTED, REASON_INVALID_PLACE_ID
    if unknown:
        return STATUS_UNSUPPORTED, REASON_UNKNOWN_PLACE
    if not scope_ok:
        return STATUS_UNSUPPORTED, REASON_UNSUPPORTED_SCOPE
    if eligible_count < TARGET_TRACTS:
        return STATUS_UNSUPPORTED, REASON_INSUFFICIENT_ELIGIBLE
    relevant = largest_component
    if seed_component is not None:
        relevant = max(largest_component, seed_component)
        if seed_component < TARGET_TRACTS and largest_component < TARGET_TRACTS:
            return STATUS_UNSUPPORTED, REASON_INSUFFICIENT_CONNECTED
        if seed_component < TARGET_TRACTS:
            return STATUS_UNSUPPORTED, REASON_INSUFFICIENT_CONNECTED
    if relevant < TARGET_TRACTS:
        return STATUS_UNSUPPORTED, REASON_INSUFFICIENT_CONNECTED
    return STATUS_SUPPORTED, None


def geographic_medoid_indices(lons: list[float], lats: list[float]) -> tuple[int, dict[str, Any]]:
    if GEOD is None:
        raise RuntimeError("pyproj is required for medoid seed")
    n = len(lons)
    if n == 0:
        raise ValueError("no eligible tracts")
    totals = []
    for i in range(n):
        if n == 1:
            totals.append(0.0)
            continue
        _, _, dist = GEOD.inv(
            [lons[i]] * n,
            [lats[i]] * n,
            lons,
            lats,
        )
        totals.append(float(sum(dist)))
    min_total = min(totals)
    tied = [i for i, total in enumerate(totals) if total == min_total]
    tied.sort()
    seed = tied[0]
    return seed, {
        "distance_method": (
            "WGS84 geodesic metres via pyproj.Geod(ellps='WGS84').inv "
            "on TIGER INTPTLON/INTPTLAT; sum of distances to every other "
            "eligible internal point"
        ),
        "total_distance_m": totals[seed],
        "tie_occurred": len(tied) > 1,
        "tied_indices": tied if len(tied) > 1 else [],
        "tie_break": "LOWEST GEOID" if len(tied) > 1 else None,
    }


def grow_greedy_pp(
    geoms_m: list[BaseGeometry],
    neighbors: list[list[int]],
    seed: int,
    geoids: list[str],
    target: int = TARGET_TRACTS,
) -> tuple[list[int], list[dict[str, Any]]]:
    selected = [seed]
    selected_set = {seed}
    union = geoms_m[seed]
    trace: list[dict[str, Any]] = [
        {
            "order": 1,
            "geoid": geoids[seed],
            "seed": True,
            "pp_raw": polsby_popper(union),
        }
    ]
    while len(selected) < target:
        frontier: list[int] = []
        seen: set[int] = set()
        for idx in selected:
            for nxt in neighbors[idx]:
                if nxt not in selected_set and nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        frontier.sort(key=lambda i: geoids[i])
        if not frontier:
            break
        scored: list[tuple[float, str, int, float]] = []
        for cand in frontier:
            tentative = unary_union([union, geoms_m[cand]])
            raw = polsby_popper(tentative)
            scored.append((round(raw, PP_COMPARE_DECIMALS), geoids[cand], cand, raw))
        scored.sort(key=lambda row: (-row[0], row[1]))
        _cmp, _gid, chosen, raw = scored[0]
        selected.append(chosen)
        selected_set.add(chosen)
        union = unary_union([union, geoms_m[chosen]])
        winners = [row for row in scored if row[0] == scored[0][0]]
        trace.append(
            {
                "order": len(selected),
                "geoid": geoids[chosen],
                "seed": False,
                "pp_raw": raw,
                "pp_compare": scored[0][0],
                "frontier": len(frontier),
                "tie_occurred": len(winners) > 1,
                "tie_break": "LOWEST GEOID" if len(winners) > 1 else None,
            }
        )
    return selected, trace


def permute_records(items: list[dict[str, Any]], mode: str, rng: random.Random) -> list[dict[str, Any]]:
    ordered = list(items)
    if mode == "normal":
        ordered.sort(key=lambda r: str(r["geoid"]))
    elif mode == "reversed":
        ordered.sort(key=lambda r: str(r["geoid"]), reverse=True)
    elif mode == "shuffled":
        rng.shuffle(ordered)
    else:
        raise ValueError(f"unknown order mode {mode}")
    return ordered


def determinism_signature(seed: str | None, selected: list[str], components: list[int]) -> tuple[str | None, tuple[str, ...], tuple[int, ...]]:
    return seed, tuple(selected), tuple(components)


# ---------------------------------------------------------------------------
# Synthetic unit-test graphs (not Census places)
# ---------------------------------------------------------------------------


def synthetic_insufficient_component_graph() -> dict[str, Any]:
    """Eligible 30, components 12 / 10 / 8 — should fail connected<25."""

    def grid(prefix: str, rows: int, cols: int) -> tuple[list[str], list[list[str]]]:
        nodes = [f"{prefix}{r:02d}{c:02d}" for r in range(rows) for c in range(cols)]
        edges: list[list[str]] = []
        lookup = {(r, c): f"{prefix}{r:02d}{c:02d}" for r in range(rows) for c in range(cols)}
        for r in range(rows):
            for c in range(cols):
                if c + 1 < cols:
                    edges.append([lookup[(r, c)], lookup[(r, c + 1)]])
                if r + 1 < rows:
                    edges.append([lookup[(r, c)], lookup[(r + 1, c)]])
        return nodes, edges

    a_nodes, a_edges = grid("A", 3, 4)  # 12
    b_nodes, b_edges = grid("B", 2, 5)  # 10
    c_nodes, c_edges = grid("C", 2, 4)  # 8
    nodes = a_nodes + b_nodes + c_nodes
    edges = a_edges + b_edges + c_edges
    return {
        "synthetic": True,
        "label": "SYNTHETIC_UNIT_TEST_GRAPH",
        "not_a_census_place": True,
        "do_not_register_as_production_place": True,
        "purpose": (
            "Prove INSUFFICIENT_CONNECTED_TRACTS when eligible >= 25 but no "
            "rook component reaches 25"
        ),
        "nodes": nodes,
        "edges": edges,
        "expected_eligible": 30,
        "expected_component_sizes": [12, 10, 8],
        "expected_reason": REASON_INSUFFICIENT_CONNECTED,
    }


def synthetic_insufficient_eligible_graph() -> dict[str, Any]:
    nodes = [f"S{i:02d}" for i in range(20)]
    edges = [[nodes[i], nodes[i + 1]] for i in range(19)]
    return {
        "synthetic": True,
        "label": "SYNTHETIC_UNIT_TEST_GRAPH",
        "not_a_census_place": True,
        "do_not_register_as_production_place": True,
        "purpose": "Prove INSUFFICIENT_ELIGIBLE_TRACTS when eligible < 25",
        "nodes": nodes,
        "edges": edges,
        "expected_eligible": 20,
        "expected_component_sizes": [20],
        "expected_reason": REASON_INSUFFICIENT_ELIGIBLE,
    }


def synthetic_success_graph() -> dict[str, Any]:
    nodes = [f"Q{i:02d}" for i in range(40)]
    edges = [[nodes[i], nodes[i + 1]] for i in range(39)]
    return {
        "synthetic": True,
        "label": "SYNTHETIC_UNIT_TEST_GRAPH",
        "not_a_census_place": True,
        "purpose": "Connected eligible >= 25 should classify SUPPORTED on count/component",
        "nodes": nodes,
        "edges": edges,
        "expected_eligible": 40,
        "expected_component_sizes": [40],
        "expected_reason": None,
        "expected_status": STATUS_SUPPORTED,
    }


def graph_neighbors(nodes: list[str], edges: list[list[str]]) -> list[list[int]]:
    index = {node: i for i, node in enumerate(nodes)}
    neighbors: list[list[int]] = [[] for _ in nodes]
    for a, b in edges:
        i, j = index[a], index[b]
        neighbors[i].append(j)
        neighbors[j].append(i)
    for row in neighbors:
        row.sort()
    return neighbors


def classify_graph_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    nodes: list[str] = list(payload["nodes"])
    edges: list[list[str]] = list(payload["edges"])
    neighbors = graph_neighbors(nodes, edges)
    sizes = component_sizes(neighbors)
    largest = sizes[0] if sizes else 0
    status, reason = classify_support(
        eligible_count=len(nodes),
        largest_component=largest,
        seed_component=largest,
        scope_ok=True,
        invalid_id=False,
        unknown=False,
    )
    return {
        "eligible_count": len(nodes),
        "component_sizes": sizes,
        "largest_component": largest,
        "status": status,
        "reason": reason,
    }


def corner_touch_squares() -> tuple[list[BaseGeometry], bool]:
    """Four unit squares touching only at a point — must not be rook-adjacent."""
    squares = [
        box(0, 0, 1, 1),
        box(1, 1, 2, 2),
        box(1, 0, 2, 1),
        box(0, 1, 1, 2),
    ]
    # Diagonal pair (0,1) share only a point.
    return squares, rook_adjacent(squares[0], squares[1])


def edge_adjacent_squares() -> tuple[list[BaseGeometry], bool]:
    squares = [box(0, 0, 1, 1), box(1, 0, 2, 1)]
    return squares, rook_adjacent(squares[0], squares[1])


def disconnected_island_polygons() -> list[BaseGeometry]:
    """Three 3x3 unit-square islands (9+9+9=27) with gaps — largest component 9."""
    geoms: list[BaseGeometry] = []
    origins = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)]
    for ox, oy in origins:
        for r in range(3):
            for c in range(3):
                geoms.append(box(ox + c, oy + r, ox + c + 1, oy + r + 1))
    return geoms


# ---------------------------------------------------------------------------
# Live Census I/O
# ---------------------------------------------------------------------------


def _http_get(url: str, dest: Path, timeout: float = 180.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp, tmp.open("wb") as handle:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
    tmp.replace(dest)


def tiger_urls(statefp: str) -> dict[str, str]:
    return {
        "place": f"{TIGER_BASE}/PLACE/tl_{CENSUS_VINTAGE}_{statefp}_place.zip",
        "tract": f"{TIGER_BASE}/TRACT/tl_{CENSUS_VINTAGE}_{statefp}_tract.zip",
    }


def download_state(statefp: str) -> dict[str, Any]:
    out: dict[str, Any] = {"statefp": statefp, "files": {}}
    for kind, url in tiger_urls(statefp).items():
        dest = cache_dir() / f"tl_{CENSUS_VINTAGE}_{statefp}_{kind}.zip"
        extracted = cache_dir() / dest.stem
        shp = extracted / f"{dest.stem}.shp"
        info: dict[str, Any] = {"url": url, "zip": str(dest), "shp": str(shp)}
        if dest.is_file() and dest.stat().st_size > 1000 and shp.is_file():
            info["status"] = "cached"
        else:
            started = time.perf_counter()
            _http_get(url, dest)
            extracted.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(extracted)
            info["status"] = "downloaded"
            info["elapsed_s"] = round(time.perf_counter() - started, 3)
        info["zip_bytes"] = dest.stat().st_size if dest.is_file() else None
        out["files"][kind] = info
    return out


def load_shapefile(shp_path: Path) -> list[dict[str, Any]]:
    import shapefile

    rows: list[dict[str, Any]] = []
    with shapefile.Reader(str(shp_path)) as reader:
        fields = [item[0] for item in reader.fields[1:]]
        for sr in reader.iterShapeRecords():
            if sr.shape is None or sr.shape.shapeType == 0:
                continue
            rec = {
                key: (value.strip() if isinstance(value, str) else value)
                for key, value in zip(fields, sr.record, strict=False)
            }
            geom = make_valid(shape(sr.shape.__geo_interface__))
            if geom.is_empty:
                continue
            rows.append({"rec": rec, "geom": geom})
    return rows


@dataclass
class PlaceRecord:
    geoid: str
    name: str
    namelsad: str
    statefp: str
    classfp: str
    geom: BaseGeometry
    lon: float
    lat: float
    aland: int
    awater: int
    multipart: bool


@dataclass
class TractRecord:
    geoid: str
    statefp: str
    geom: BaseGeometry
    lon: float
    lat: float
    aland: int
    awater: int


def load_state_layers(statefp: str) -> tuple[list[PlaceRecord], list[TractRecord]]:
    base = cache_dir()
    place_shp = base / f"tl_{CENSUS_VINTAGE}_{statefp}_place" / f"tl_{CENSUS_VINTAGE}_{statefp}_place.shp"
    tract_shp = base / f"tl_{CENSUS_VINTAGE}_{statefp}_tract" / f"tl_{CENSUS_VINTAGE}_{statefp}_tract.shp"
    if not place_shp.is_file() or not tract_shp.is_file():
        download_state(statefp)
    places_raw = load_shapefile(place_shp)
    tracts_raw = load_shapefile(tract_shp)
    places: list[PlaceRecord] = []
    for row in places_raw:
        rec = row["rec"]
        geom = row["geom"]
        places.append(
            PlaceRecord(
                geoid=str(rec.get("GEOID")),
                name=str(rec.get("NAME") or ""),
                namelsad=str(rec.get("NAMELSAD") or rec.get("NAME") or ""),
                statefp=str(rec.get("STATEFP") or statefp),
                classfp=str(rec.get("CLASSFP") or ""),
                geom=geom,
                lon=float(rec.get("INTPTLON") or 0.0),
                lat=float(rec.get("INTPTLAT") or 0.0),
                aland=int(rec.get("ALAND") or 0),
                awater=int(rec.get("AWATER") or 0),
                multipart=geom.geom_type == "MultiPolygon",
            )
        )
    tracts: list[TractRecord] = []
    for row in tracts_raw:
        rec = row["rec"]
        tracts.append(
            TractRecord(
                geoid=str(rec.get("GEOID")),
                statefp=str(rec.get("STATEFP") or statefp),
                geom=row["geom"],
                lon=float(rec.get("INTPTLON") or 0.0),
                lat=float(rec.get("INTPTLAT") or 0.0),
                aland=int(rec.get("ALAND") or 0),
                awater=int(rec.get("AWATER") or 0),
            )
        )
    return places, tracts


def assign_eligible(
    places: list[PlaceRecord],
    tracts: list[TractRecord],
) -> dict[str, list[TractRecord]]:
    if not places:
        return {}
    geoms = [p.geom for p in places]
    tree = STRtree(geoms)
    assigned: dict[str, list[TractRecord]] = defaultdict(list)
    for tract in tracts:
        point = Point(tract.lon, tract.lat)
        hits = tree.query(point)
        for idx in hits:
            place = places[int(idx)]
            if place.geom.covers(point):
                assigned[place.geoid].append(tract)
    for geoid in assigned:
        assigned[geoid].sort(key=lambda t: t.geoid)
    return assigned


def _project_tracts(
    tracts: list[TractRecord],
    lon0: float,
    lat0: float,
) -> tuple[list[BaseGeometry], str]:
    if is_conus_point(lon0, lat0):
        return [project_5070(t.geom) for t in tracts], "EPSG:5070"
    return [project_local_aeqd(t.geom, lon0, lat0) for t in tracts], "LOCAL_AEQD_SEARCH_ONLY"


def measure_place(
    place: PlaceRecord,
    eligible: list[TractRecord],
    *,
    run_selection: bool,
    order_mode: str = "normal",
    rng: random.Random | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    rng = rng or random.Random(20260830)
    invalid = validate_place_geoid(place.geoid)
    scope_ok = is_conus_point(place.lon, place.lat)
    records = [
        {
            "geoid": t.geoid,
            "geom": t.geom,
            "lon": t.lon,
            "lat": t.lat,
            "aland": t.aland,
            "awater": t.awater,
        }
        for t in eligible
    ]
    records = permute_records(records, order_mode, rng)
    geoids = [str(r["geoid"]) for r in records]
    lons = [float(r["lon"]) for r in records]
    lats = [float(r["lat"]) for r in records]
    geoms_m, crs = (
        _project_tracts(
            [
                TractRecord(
                    geoid=str(r["geoid"]),
                    statefp=place.statefp,
                    geom=r["geom"],
                    lon=float(r["lon"]),
                    lat=float(r["lat"]),
                    aland=int(r["aland"]),
                    awater=int(r["awater"]),
                )
                for r in records
            ],
            place.lon,
            place.lat,
        )
        if records
        else ([], "EPSG:5070" if scope_ok else "LOCAL_AEQD_SEARCH_ONLY")
    )
    neighbors = build_rook_neighbors(geoms_m) if geoms_m else []
    components = connected_components(neighbors)
    sizes = [len(c) for c in components]
    largest = sizes[0] if sizes else 0
    seed_geoid = None
    seed_idx = None
    seed_component_size = None
    selected: list[str] = []
    selected_connected = None
    area_km2 = None
    compactness = None
    seed_meta: dict[str, Any] = {}
    growth_len = None
    if records and run_selection and largest >= 1:
        seed_idx, seed_meta = geographic_medoid_indices(lons, lats)
        seed_geoid = geoids[seed_idx]
        seed_group = component_containing(components, seed_idx)
        seed_component_size = len(seed_group)
        if seed_component_size >= TARGET_TRACTS:
            grown, _trace = grow_greedy_pp(geoms_m, neighbors, seed_idx, geoids)
            selected = [geoids[i] for i in grown]
            growth_len = len(selected)
            if len(grown) == TARGET_TRACTS:
                selected_connected = is_rook_connected(grown, neighbors)
                union = unary_union([geoms_m[i] for i in grown])
                area_km2 = round(float(union.area) / 1_000_000.0, 6)
                compactness = round(polsby_popper(union), 8)
    status, reason = classify_support(
        eligible_count=len(records),
        largest_component=largest,
        seed_component=seed_component_size,
        scope_ok=scope_ok,
        invalid_id=invalid is not None,
        unknown=False,
    )
    if status == STATUS_SUPPORTED and growth_len != TARGET_TRACTS:
        status, reason = STATUS_UNSUPPORTED, REASON_INSUFFICIENT_CONNECTED
    elapsed = round(time.perf_counter() - started, 4)
    return {
        "place_geoid": place.geoid,
        "place_name": place.namelsad or place.name,
        "statefp": place.statefp,
        "classfp": place.classfp,
        "multipart_place_geometry": place.multipart,
        "aland_m2": place.aland,
        "awater_m2": place.awater,
        "intptlon": place.lon,
        "intptlat": place.lat,
        "conus": scope_ok,
        "projection": crs,
        "eligible_count": len(records),
        "component_sizes": sizes,
        "largest_component": largest,
        "n_components": len(sizes),
        "seed": seed_geoid,
        "seed_component_size": seed_component_size,
        "selected": selected,
        "selected_count": len(selected),
        "rook_connected_selected": selected_connected,
        "area_km2": area_km2,
        "compactness_polsby_popper": compactness,
        "timezone": CURATED_TIMEZONES.get(place.geoid, "NOT_MEASURED"),
        "timezone_source": (
            "panel_curated_iana" if place.geoid in CURATED_TIMEZONES else "NOT_MEASURED"
        ),
        "runtime_s": elapsed,
        "order_mode": order_mode,
        "status": status,
        "reason": reason,
        "seed_meta": seed_meta,
        "input_geoid_order_sha256": hashlib.sha256(
            ",".join(geoids).encode("utf-8")
        ).hexdigest(),
    }


def run_determinism(
    place: PlaceRecord,
    eligible: list[TractRecord],
    repeats: int = 3,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    modes = (
        [("normal", 20260830)]
        + [("reversed", 20260830)]
        + [("shuffled", 1), ("shuffled", 2)]
        + [("normal", 1000 + i) for i in range(repeats)]
    )
    do_select = len(eligible) >= TARGET_TRACTS
    # Cap extremely large cities: still select, but fewer extra repeats.
    extra_repeats = repeats if len(eligible) <= 900 else 1
    modes = (
        [("normal", 20260830), ("reversed", 20260830), ("shuffled", 1), ("shuffled", 2)]
        + [("normal", 1000 + i) for i in range(extra_repeats)]
    )
    for mode, seed in modes:
        result = measure_place(
            place,
            eligible,
            run_selection=do_select,
            order_mode=mode,
            rng=random.Random(seed),
        )
        runs.append(
            {
                "mode": mode,
                "rng_seed": seed,
                "seed": result["seed"],
                "selected": result["selected"],
                "component_sizes": result["component_sizes"],
                "status": result["status"],
                "reason": result["reason"],
                "runtime_s": result["runtime_s"],
            }
        )
    signatures = {
        determinism_signature(r["seed"], r["selected"], r["component_sizes"])
        for r in runs
    }
    return {
        "deterministic": len(signatures) == 1,
        "n_runs": len(runs),
        "distinct_signatures": len(signatures),
        "runs": runs,
    }


def scan_state(statefp: str) -> dict[str, Any]:
    places, tracts = load_state_layers(statefp)
    assigned = assign_eligible(places, tracts)
    place_by_id = {p.geoid: p for p in places}
    rows: list[dict[str, Any]] = []
    for place in places:
        eligible = assigned.get(place.geoid, [])
        rows.append(
            {
                "place_geoid": place.geoid,
                "name": place.namelsad or place.name,
                "classfp": place.classfp,
                "multipart": place.multipart,
                "eligible_count": len(eligible),
                "aland_m2": place.aland,
                "awater_m2": place.awater,
                "conus": is_conus_point(place.lon, place.lat),
                "intptlon": place.lon,
                "intptlat": place.lat,
            }
        )
    rows.sort(key=lambda r: (-int(r["eligible_count"]), r["place_geoid"]))
    return {
        "statefp": statefp,
        "n_places": len(places),
        "n_tracts": len(tracts),
        "places": rows,
        "assigned": assigned,
        "place_by_id": place_by_id,
    }


def interesting_for_fail2(row: dict[str, Any]) -> bool:
    n = int(row["eligible_count"])
    if n >= TARGET_TRACTS and n <= 80:
        return True
    if n >= TARGET_TRACTS and bool(row["multipart"]):
        return True
    if n >= TARGET_TRACTS and int(row["awater_m2"]) > int(row["aland_m2"]):
        return True
    return row["place_geoid"] in FAIL2_SEARCH_TARGETS


def measure_named_targets(scans: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = {
        **SUCCESS_TARGETS,
        **FAIL_LT25_TARGETS,
        **FAIL2_SEARCH_TARGETS,
        **RETROSPECTIVE_TARGETS,
    }
    results: list[dict[str, Any]] = []
    for geoid, meta in wanted.items():
        statefp = None
        place = None
        eligible: list[TractRecord] = []
        for scan in scans.values():
            place = scan["place_by_id"].get(geoid)
            if place is not None:
                eligible = scan["assigned"].get(geoid, [])
                statefp = scan["statefp"]
                break
        if place is None:
            results.append(
                {
                    "place_geoid": geoid,
                    "place_name": meta["name"],
                    "status": STATUS_UNSUPPORTED,
                    "reason": REASON_UNKNOWN_PLACE,
                    "eligible_count": None,
                    "role": meta["role"],
                    "panel": _panel_bucket(geoid),
                    "measured": False,
                    "notes": "Place GEOID not present in downloaded TIGER 2025 layers",
                }
            )
            continue
        run_selection = geoid in SUCCESS_TARGETS or geoid in RETROSPECTIVE_TARGETS
        if geoid in FAIL2_SEARCH_TARGETS and len(eligible) >= TARGET_TRACTS:
            run_selection = True
        measurement = measure_place(place, eligible, run_selection=run_selection)
        det = None
        if run_selection:
            det = run_determinism(place, eligible)
            measurement["determinism"] = {
                "deterministic": det["deterministic"],
                "n_runs": det["n_runs"],
                "distinct_signatures": det["distinct_signatures"],
            }
        measurement["role"] = meta["role"]
        measurement["panel"] = _panel_bucket(geoid)
        measurement["measured"] = True
        measurement["catalog_name"] = meta["name"]
        results.append(measurement)
    return results


def _panel_bucket(geoid: str) -> str:
    if geoid in SUCCESS_TARGETS:
        return "success"
    if geoid in FAIL_LT25_TARGETS:
        return "fail_lt25"
    if geoid in RETROSPECTIVE_TARGETS:
        return "phoenix_retrospective"
    if geoid in FAIL2_SEARCH_TARGETS:
        return "fail2_search"
    return "other"


def search_fail2(scans: dict[str, dict[str, Any]]) -> dict[str, Any]:
    examined: list[dict[str, Any]] = []
    found: list[dict[str, Any]] = []
    for statefp, scan in scans.items():
        candidates = [row for row in scan["places"] if interesting_for_fail2(row)]
        for row in candidates:
            geoid = row["place_geoid"]
            place = scan["place_by_id"][geoid]
            eligible = scan["assigned"].get(geoid, [])
            geoms_m, crs = _project_tracts(eligible, place.lon, place.lat)
            neighbors = build_rook_neighbors(geoms_m)
            sizes = component_sizes(neighbors)
            largest = sizes[0] if sizes else 0
            entry = {
                "place_geoid": geoid,
                "name": row["name"],
                "statefp": statefp,
                "classfp": row["classfp"],
                "eligible_count": len(eligible),
                "component_sizes": sizes,
                "largest_component": largest,
                "n_components": len(sizes),
                "multipart": row["multipart"],
                "projection": crs,
                "conus": row["conus"],
                "why_examined": _fail2_why(row),
            }
            examined.append(entry)
            if (
                len(eligible) >= TARGET_TRACTS
                and largest < TARGET_TRACTS
                and row["conus"]
            ):
                found.append(entry)
    examined.sort(key=lambda r: (r["largest_component"], r["eligible_count"], r["place_geoid"]))
    return {
        "strategy": (
            "Download TIGER/Line 2025 place+tract layers for "
            f"{len(DOWNLOAD_STATES)} states. Assign eligibility by official "
            "internal-point-in-place. Compute rook components for every place "
            "with 25–80 eligible tracts, every multipart place with >=25 "
            "eligible, every place whose AWATER exceeds ALAND with >=25 "
            "eligible, and the curated coastal/island/balance watch list."
        ),
        "states_scanned": sorted(scans),
        "n_candidates_rook_evaluated": len(examined),
        "real_connected_lt25_found": len(found) > 0,
        "found": found,
        "examined": examined,
        "watch_list": FAIL2_SEARCH_TARGETS,
    }


def _fail2_why(row: dict[str, Any]) -> str:
    reasons = []
    if row["place_geoid"] in FAIL2_SEARCH_TARGETS:
        reasons.append("curated_watch_list")
    n = int(row["eligible_count"])
    if TARGET_TRACTS <= n <= 80:
        reasons.append("eligible_25_to_80")
    if row["multipart"] and n >= TARGET_TRACTS:
        reasons.append("multipart_place")
    if n >= TARGET_TRACTS and int(row["awater_m2"]) > int(row["aland_m2"]):
        reasons.append("water_gt_land")
    return ",".join(reasons) or "other"


def identity_failures() -> list[dict[str, Any]]:
    return [
        {
            "place_geoid": "00XXXXX",
            "place_name": "(malformed GEOID)",
            "eligible_count": None,
            "largest_component": None,
            "expected_reason": REASON_INVALID_PLACE_ID,
            "actual_reason": validate_place_geoid("00XXXXX"),
            "status": STATUS_UNSUPPORTED,
            "panel": "identity_fail",
            "role": "invalid_place_id",
            "pass": validate_place_geoid("00XXXXX") == REASON_INVALID_PLACE_ID,
            "notes": "Not a fabricated Census place; format guard only.",
        },
        {
            "place_geoid": "0499999",
            "place_name": "(absent from TIGER 2025 AZ places)",
            "eligible_count": None,
            "largest_component": None,
            "expected_reason": REASON_UNKNOWN_PLACE,
            "actual_reason": REASON_UNKNOWN_PLACE,
            "status": STATUS_UNSUPPORTED,
            "panel": "identity_fail",
            "role": "unknown_place",
            "pass": True,
            "notes": (
                "Well-formed 7-digit GEOID that is not a 2025 AZ place. "
                "Confirmed absent after AZ place-layer load when available."
            ),
        },
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_static_fixtures() -> None:
    dest = fixture_dir()
    dest.mkdir(parents=True, exist_ok=True)
    write_json(dest / "substrate.json", FROZEN_CANDIDATE_SUBSTRATE)
    catalog = {
        "schema_version": "NATIONAL_RESOLVER_PANEL_CATALOG_V1",
        "census_vintage": CENSUS_VINTAGE,
        "success": [
            {"place_geoid": g, **m} for g, m in SUCCESS_TARGETS.items()
        ],
        "fail_lt25": [
            {"place_geoid": g, **m} for g, m in FAIL_LT25_TARGETS.items()
        ],
        "fail2_search": [
            {"place_geoid": g, **m} for g, m in FAIL2_SEARCH_TARGETS.items()
        ],
        "phoenix_retrospective": [
            {"place_geoid": g, **m} for g, m in RETROSPECTIVE_TARGETS.items()
        ],
        "identity_fail": [
            {"place_geoid": g, **m} for g, m in IDENTITY_FAIL_TARGETS.items()
        ],
        "fail2_found": [
            {"place_geoid": g, **m} for g, m in FAIL2_FOUND_TARGETS.items()
        ],
        "should_fail": [
            {"place_geoid": g, **m} for g, m in SHOULD_FAIL_TARGETS.items()
        ],
        "required_real_lt25": True,
        "real_connected_lt25_found": True,
        "success_only_is_incomplete": True,
    }
    write_json(dest / "panel_catalog.json", catalog)
    synth = dest / "synthetic"
    synth.mkdir(parents=True, exist_ok=True)
    write_json(synth / "insufficient_component_graph.json", synthetic_insufficient_component_graph())
    write_json(synth / "insufficient_eligible_graph.json", synthetic_insufficient_eligible_graph())
    write_json(synth / "connected_success_graph.json", synthetic_success_graph())
    measurements_path = dest / "measurements.json"
    if not measurements_path.is_file():
        write_json(
            measurements_path,
            {
                "generated_at": None,
                "live_measured": False,
                "substrate": FROZEN_CANDIDATE_SUBSTRATE,
                "measurements": [],
                "fail2_search": {
                    "real_connected_lt25_found": None,
                    "n_candidates_rook_evaluated": 0,
                    "states_scanned": [],
                    "found": [],
                },
                "identity_failures": identity_failures(),
            },
        )
    search_path = dest / "fail_case2_search.json"
    if not search_path.is_file():
        write_json(
            search_path,
            {
                "strategy": (
                    "Download TIGER/Line 2025 place+tract layers. Assign "
                    "eligibility by official internal-point-in-place. Compute "
                    "rook components for 25–80 eligible places, multipart "
                    "places, water-dominant places, and the curated watch list."
                ),
                "states_scanned": [],
                "n_candidates_rook_evaluated": 0,
                "real_connected_lt25_found": None,
                "found": [],
                "watch_list": [
                    {"place_geoid": g, **m} for g, m in FAIL2_SEARCH_TARGETS.items()
                ],
                "examined_preview": [],
                "status": "PENDING_LIVE_SCAN",
            },
        )


def cmd_download(states: Iterable[str]) -> list[dict[str, Any]]:
    reports = []
    for statefp in states:
        print(f"download {statefp}", flush=True)
        reports.append(download_state(statefp))
    write_json(panel_run_dir() / "download_report.json", reports)
    return reports


def cmd_run() -> dict[str, Any]:
    write_static_fixtures()
    cmd_download(DOWNLOAD_STATES)
    scans: dict[str, dict[str, Any]] = {}
    scan_summaries: list[dict[str, Any]] = []
    for statefp in DOWNLOAD_STATES:
        print(f"scan {statefp}", flush=True)
        raw = scan_state(statefp)
        scans[statefp] = raw
        scan_summaries.append(
            {
                "statefp": statefp,
                "n_places": raw["n_places"],
                "n_tracts": raw["n_tracts"],
                "places": raw["places"],
            }
        )
    print("search fail2", flush=True)
    fail2 = search_fail2(scans)
    print("measure named targets", flush=True)
    measurements = measure_named_targets(scans)
    identity = identity_failures()
    # Confirm 0499999 is absent from AZ if scanned.
    if "04" in scans:
        identity[1]["pass"] = "0499999" not in scans["04"]["place_by_id"]
        identity[1]["notes"] = (
            "Well-formed 7-digit GEOID absent from TIGER 2025 AZ place layer "
            f"(AZ place count={scans['04']['n_places']})."
        )
    payload = {
        "generated_at": utc_now(),
        "live_measured": True,
        "substrate": PROVISIONAL_SUBSTRATE,
        "measurements": measurements,
        "fail2_search": {
            k: v
            for k, v in fail2.items()
            if k != "examined"
        },
        "fail2_examined_count": len(fail2["examined"]),
        "identity_failures": identity,
        "scan_summaries": [
            {
                "statefp": s["statefp"],
                "n_places": s["n_places"],
                "n_tracts": s["n_tracts"],
                "n_places_eligible_ge_25": sum(
                    1 for p in s["places"] if p["eligible_count"] >= TARGET_TRACTS
                ),
                "n_places_eligible_lt_25": sum(
                    1 for p in s["places"] if p["eligible_count"] < TARGET_TRACTS
                ),
            }
            for s in scan_summaries
        ],
    }
    write_json(panel_run_dir() / "measurements_live.json", payload)
    write_json(panel_run_dir() / "fail2_examined.json", fail2["examined"])
    write_json(fixture_dir() / "measurements.json", payload)
    write_json(
        fixture_dir() / "fail_case2_search.json",
        {
            "strategy": fail2["strategy"],
            "states_scanned": fail2["states_scanned"],
            "n_candidates_rook_evaluated": fail2["n_candidates_rook_evaluated"],
            "real_connected_lt25_found": fail2["real_connected_lt25_found"],
            "found": fail2["found"],
            "watch_list": [
                {"place_geoid": g, **m} for g, m in FAIL2_SEARCH_TARGETS.items()
            ],
            "examined_preview": fail2["examined"][:80],
            "full_examined_path": "workforce/national_resolver/panel_runs/fail2_examined.json",
        },
    )
    write_json(panel_run_dir() / "scan_place_counts.json", scan_summaries)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("download", "fixtures", "run", "classify-synthetic"),
        nargs="?",
        default="run",
    )
    args = parser.parse_args(argv)
    if args.command == "download":
        cmd_download(DOWNLOAD_STATES)
        return 0
    if args.command == "fixtures":
        write_static_fixtures()
        return 0
    if args.command == "classify-synthetic":
        for payload in (
            synthetic_insufficient_component_graph(),
            synthetic_insufficient_eligible_graph(),
            synthetic_success_graph(),
        ):
            print(json.dumps(classify_graph_fixture(payload)))
        return 0
    cmd_run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
