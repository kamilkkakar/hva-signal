"""National resolver geometry: CRS, metrics, repair, components, hash.

Phoenix UTM 12N (EPSG:32612) is not the national analysis CRS.
v1 scope is CONUS + DC in EPSG:5070. Alaska, Hawaii, and territories
are rejected. Computation copies never rewrite official Census rings.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shp_transform
from shapely.ops import unary_union
from shapely.validation import make_valid

SOURCE_CRS = "EPSG:4269"
ANALYSIS_CRS = "EPSG:5070"
ANALYSIS_SCOPE = "CONUS_DC"
SOURCE_CRS_URN = "urn:ogc:def:crs:EPSG::4269"
FORBIDDEN_NATIONAL_ANALYSIS_CRS = frozenset({"EPSG:32612", "EPSG:26912"})
TARGET_ZONE_COUNT = 25
MAX_REPAIR_REL_AREA_CHANGE = 0.001
PP_COMPARE_DECIMALS = 6
_AREA_EPS = 1e-9

# GRS80 / EPSG:5070 Albers Equal Area (NAD83 / Conus Albers).
_A = 6378137.0
_INV_F = 298.257222101
_F = 1.0 / _INV_F
_E2 = 2.0 * _F - _F * _F
_E = math.sqrt(_E2)
_PHI1 = math.radians(29.5)
_PHI2 = math.radians(45.5)
_PHI0 = math.radians(23.0)
_LAM0 = math.radians(-96.0)


def _albers_m(phi: float) -> float:
    s = math.sin(phi)
    return math.cos(phi) / math.sqrt(1.0 - _E2 * s * s)


def _albers_q(phi: float) -> float:
    s = math.sin(phi)
    es = _E * s
    return (1.0 - _E2) * (
        s / (1.0 - _E2 * s * s) - (1.0 / (2.0 * _E)) * math.log((1.0 - es) / (1.0 + es))
    )


_M1 = _albers_m(_PHI1)
_M2 = _albers_m(_PHI2)
_Q0 = _albers_q(_PHI0)
_Q1 = _albers_q(_PHI1)
_Q2 = _albers_q(_PHI2)
_N = (_M1 * _M1 - _M2 * _M2) / (_Q2 - _Q1)
_C = _M1 * _M1 + _N * _Q1
_RHO0 = _A * math.sqrt(_C - _N * _Q0) / _N

CONUS_DC_STATEFP = frozenset(
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
UNSUPPORTED_STATEFP = frozenset({"02", "15", "60", "66", "69", "72", "78"})
CONUS_DC_LON_RANGE = (-124.8, -66.9)
CONUS_DC_LAT_RANGE = (24.4, 49.5)

CANONICAL_PROPERTY_KEYS = (
    "GEOID",
    "STATEFP",
    "COUNTYFP",
    "TRACTCE",
    "NAME",
    "NAMELSAD",
    "ALAND",
    "AWATER",
    "INTPTLAT",
    "INTPTLON",
)

__all__ = [
    "ANALYSIS_CRS",
    "ANALYSIS_SCOPE",
    "CANONICAL_PROPERTY_KEYS",
    "CONUS_DC_STATEFP",
    "ComponentTooSmallError",
    "FORBIDDEN_NATIONAL_ANALYSIS_CRS",
    "ForbiddenAnalysisCRSError",
    "GeometryRepairRejected",
    "LandOrientedPolsbyPopperError",
    "NationalGeometryError",
    "PP_COMPARE_DECIMALS",
    "PlanarMetrics",
    "SOURCE_CRS",
    "SOURCE_CRS_URN",
    "TARGET_ZONE_COUNT",
    "UNSUPPORTED_STATEFP",
    "UnsupportedTerritoryError",
    "canonical_sha256",
    "canonicalize_feature_collection",
    "compare_polsby_popper",
    "computation_geometry",
    "connected_component",
    "dump_canonical",
    "lonlat_to_5070",
    "official_rings_unchanged",
    "planar_distance_m",
    "planar_metrics",
    "project_to_analysis",
    "require_analysis_crs",
    "require_component_supports_target",
    "require_conus_dc_lonlat",
    "require_conus_dc_statefp",
    "require_place_scope",
    "source_bytes_sha256",
    "union_planar_metrics",
    "utm_zone_from_lon",
    "xy5070_to_lonlat",
]


class NationalGeometryError(ValueError):
    """Fail-closed national geometry / topology error."""


class ForbiddenAnalysisCRSError(NationalGeometryError):
    """A Phoenix-only or regional CRS was offered as the national default."""


class UnsupportedTerritoryError(NationalGeometryError):
    """Alaska, Hawaii, or a territory — analysis math is not ready."""


class GeometryRepairRejected(NationalGeometryError):
    """make_valid emptied the geometry or changed area too much."""


class LandOrientedPolsbyPopperError(NationalGeometryError):
    """ALAND cannot be paired with official perimeter to form PP."""


class ComponentTooSmallError(NationalGeometryError):
    """Seed rook component cannot hold the required zone count."""


@dataclass(frozen=True)
class PlanarMetrics:
    area_m2: float
    perimeter_m: float
    polsby_popper: float
    pp_raw: float
    pp_compare: float
    crs: str
    scope: str
    land_oriented: bool


def _normalize_epsg(crs: str) -> str:
    compact = str(crs).strip().upper().replace(" ", "")
    if compact.startswith("EPSG:"):
        return f"EPSG:{compact.split(':', 1)[1]}"
    if compact.isdigit():
        return f"EPSG:{compact}"
    return compact


def require_analysis_crs(crs: str) -> None:
    normalized = _normalize_epsg(crs)
    if normalized in FORBIDDEN_NATIONAL_ANALYSIS_CRS:
        raise ForbiddenAnalysisCRSError(
            f"{crs} is not a national analysis CRS (Phoenix UTM 12N / 32612 is not reusable)."
        )
    if normalized != ANALYSIS_CRS:
        raise ForbiddenAnalysisCRSError(
            f"national v1 analysis CRS is {ANALYSIS_CRS}, not {crs}."
        )


def _statefp_code(statefp: str | int) -> str:
    text = str(statefp).strip()
    if text.isdigit():
        return text.zfill(2)
    return text.zfill(2)


def require_conus_dc_statefp(statefp: str | int | None) -> None:
    if statefp is None or (isinstance(statefp, str) and not statefp.strip()):
        raise UnsupportedTerritoryError(
            "STATEFP is missing; reject unless an explicit CONUS+DC centroid test is supplied."
        )
    code = _statefp_code(statefp)
    if code in UNSUPPORTED_STATEFP or code not in CONUS_DC_STATEFP:
        raise UnsupportedTerritoryError(
            f"STATEFP={code} is outside CONUS+DC; Alaska/Hawaii/territories are not claimed."
        )


def require_conus_dc_lonlat(lon: float, lat: float) -> None:
    """Coarse CONUS+DC box. Not a shoreline. Used when STATEFP is absent."""
    lon_ok = CONUS_DC_LON_RANGE[0] <= lon <= CONUS_DC_LON_RANGE[1]
    lat_ok = CONUS_DC_LAT_RANGE[0] <= lat <= CONUS_DC_LAT_RANGE[1]
    if not (lon_ok and lat_ok):
        raise UnsupportedTerritoryError(
            f"lon/lat ({lon}, {lat}) is outside the CONUS+DC pre-filter box; "
            "Alaska/Hawaii/territories are not in v1 scope."
        )


def require_place_scope(
    statefp: str | int | None,
    *,
    lon: float | None = None,
    lat: float | None = None,
) -> None:
    """Reject AK/HI/territories. Missing STATEFP requires a CONUS+DC centroid."""
    if statefp is None or (isinstance(statefp, str) and not statefp.strip()):
        if lon is None or lat is None:
            raise UnsupportedTerritoryError(
                "STATEFP is missing; supply an explicit CONUS+DC centroid test."
            )
        require_conus_dc_lonlat(lon, lat)
        return
    require_conus_dc_statefp(statefp)


def utm_zone_from_lon(lon: float) -> int:
    """Diagnostic UTM zone from longitude. Not an analysis CRS."""
    return int(math.floor((lon + 180.0) / 6.0)) + 1


def lonlat_to_5070(lon: float, lat: float) -> tuple[float, float]:
    lam = math.radians(lon)
    phi = math.radians(lat)
    rho = _A * math.sqrt(_C - _N * _albers_q(phi)) / _N
    theta = _N * (lam - _LAM0)
    return rho * math.sin(theta), _RHO0 - rho * math.cos(theta)


def _phi_from_authalic_q(q: float) -> float:
    phi = math.asin(max(-1.0, min(1.0, q / 2.0)))
    for _ in range(16):
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)
        if abs(cos_phi) < 1e-15:
            break
        denom = 1.0 - _E2 * sin_phi * sin_phi
        dphi = (q - _albers_q(phi)) * (denom * denom) / (2.0 * (1.0 - _E2) * cos_phi)
        phi += dphi
        if abs(dphi) < 1e-14:
            break
    return phi


def xy5070_to_lonlat(x: float, y: float) -> tuple[float, float]:
    rho = math.copysign(math.hypot(x, _RHO0 - y), _N)
    theta = math.atan2(x, _RHO0 - y)
    q = (_C - (rho * _N / _A) ** 2) / _N
    lon = math.degrees(_LAM0 + theta / _N)
    return lon, math.degrees(_phi_from_authalic_q(q))


def _require_lonlat_bounds(geom: BaseGeometry) -> None:
    if geom.is_empty:
        return
    minx, miny, maxx, maxy = geom.bounds
    if not (
        -180.0 <= minx <= 180.0
        and -180.0 <= maxx <= 180.0
        and -90.0 <= miny <= 90.0
        and -90.0 <= maxy <= 90.0
    ):
        raise NationalGeometryError(
            "official geometry must be EPSG:4269 lon/lat; "
            "analysis metres cannot be treated as degrees"
        )


def project_to_analysis(geom: BaseGeometry) -> BaseGeometry:
    if geom.is_empty:
        return geom
    _require_lonlat_bounds(geom)
    return shp_transform(lambda x, y, z=None: lonlat_to_5070(x, y), geom)


def _polsby_popper(area_m2: float, perimeter_m: float) -> float:
    if area_m2 <= 0.0 or perimeter_m <= 0.0:
        return 0.0
    return (4.0 * math.pi * area_m2) / (perimeter_m * perimeter_m)


def compare_polsby_popper(pp_raw: float) -> float:
    """PP_COMPARE = round(PP_raw, 6). Ranking only; traces store PP_raw unrounded."""
    return round(float(pp_raw), PP_COMPARE_DECIMALS)


def _metrics_from_projected(projected: BaseGeometry) -> PlanarMetrics:
    area = float(projected.area)
    perim = float(projected.length)
    raw = _polsby_popper(area, perim)
    return PlanarMetrics(
        area_m2=area,
        perimeter_m=perim,
        polsby_popper=raw,
        pp_raw=raw,
        pp_compare=compare_polsby_popper(raw),
        crs=ANALYSIS_CRS,
        scope=ANALYSIS_SCOPE,
        land_oriented=False,
    )


def planar_metrics(
    geom_lonlat: BaseGeometry,
    *,
    land_area_m2: float | None = None,
) -> PlanarMetrics:
    if land_area_m2 is not None:
        raise LandOrientedPolsbyPopperError(
            "land-oriented Polsby-Popper from ALAND + official perimeter is refused; "
            "ALAND is an area scalar, not a land polygon."
        )
    return _metrics_from_projected(computation_geometry(geom_lonlat))


def union_planar_metrics(geoms_lonlat: Iterable[BaseGeometry]) -> PlanarMetrics:
    """Official-ring union PP in EPSG:5070. Does not rewrite source coordinates."""
    copies = [computation_geometry(geom) for geom in geoms_lonlat]
    if not copies:
        raise NationalGeometryError("union compactness requires at least one geometry")
    return _metrics_from_projected(unary_union(copies))


def planar_distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    x1, y1 = lonlat_to_5070(lon1, lat1)
    x2, y2 = lonlat_to_5070(lon2, lat2)
    return math.hypot(x2 - x1, y2 - y1)


def _area_change_too_large(original: float, repaired: float) -> bool:
    measurable = abs(original) > _AREA_EPS or abs(repaired) > _AREA_EPS
    if not measurable:
        return False
    rel = abs(repaired - original) / max(abs(original), _AREA_EPS)
    return rel > MAX_REPAIR_REL_AREA_CHANGE


def computation_geometry(geom_lonlat: BaseGeometry) -> BaseGeometry:
    """Valid EPSG:5070 copy. Does not mutate the caller's official rings."""
    official = geom_lonlat
    if official.is_empty:
        raise GeometryRepairRejected("empty geometry cannot be repaired for computation")
    _require_lonlat_bounds(official)

    working = official
    if not working.is_valid:
        working = make_valid(working)
        if working.is_empty:
            raise GeometryRepairRejected("make_valid produced an empty geometry")

    projected = project_to_analysis(working)
    if projected.is_empty:
        raise GeometryRepairRejected("projected computation copy is empty")

    if working is not official:
        original_projected = project_to_analysis(official)
        if _area_change_too_large(float(original_projected.area), float(projected.area)):
            raise GeometryRepairRejected(
                "make_valid changed projected area by more than 0.1%; "
                "Census rings will not be rewritten"
            )

    if not projected.is_valid:
        first_area = float(projected.area)
        repaired = make_valid(projected)
        if repaired.is_empty:
            raise GeometryRepairRejected("projected make_valid produced an empty geometry")
        if _area_change_too_large(first_area, float(repaired.area)):
            raise GeometryRepairRejected(
                f"make_valid changed projected area by more than {MAX_REPAIR_REL_AREA_CHANGE}; "
                "Census rings will not be rewritten"
            )
        projected = repaired
    return projected


def official_rings_unchanged(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    return before == after


def connected_component(graph: Mapping[str, Iterable[str]], seed: str) -> frozenset[str]:
    if seed not in graph:
        raise NationalGeometryError(f"seed {seed!r} is not in the eligible graph")
    seen: set[str] = set()
    stack = [seed]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for nbr in graph.get(node, ()):
            if nbr not in seen:
                stack.append(str(nbr))
    return frozenset(seen)


def require_component_supports_target(
    component: frozenset[str],
    n: int = TARGET_ZONE_COUNT,
) -> frozenset[str]:
    if len(component) < n:
        raise ComponentTooSmallError(
            f"seed rook component has {len(component)} tracts; cannot support {n}"
        )
    return component


def _ordered_properties(props: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in CANONICAL_PROPERTY_KEYS:
        if key in props:
            out[key] = props[key]
    extras = sorted(key for key in props if key not in CANONICAL_PROPERTY_KEYS)
    for key in extras:
        out[key] = props[key]
    return out


def canonicalize_feature_collection(
    features: list[dict[str, Any]],
    *,
    name: str,
    collection_properties: Mapping[str, Any],
) -> dict[str, Any]:
    ordered_features: list[dict[str, Any]] = []
    for feature in sorted(
        features,
        key=lambda item: str(item.get("properties", {}).get("GEOID", "")),
    ):
        props = feature.get("properties") or {}
        ordered_features.append(
            {
                "type": "Feature",
                "properties": _ordered_properties(props),
                "geometry": feature["geometry"],
            }
        )
    return {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": SOURCE_CRS_URN}},
        "properties": {key: collection_properties[key] for key in sorted(collection_properties)},
        "features": ordered_features,
    }


def dump_canonical(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(dump_canonical(payload)).hexdigest()


def source_bytes_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
