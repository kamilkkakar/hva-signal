#!/usr/bin/env python3
"""Materialize CROSS_CITY_COMPARISON_GEOGRAPHY_V1 packages via ALG1.

Free Census TIGER only. No FortyGuard. Writes under data/areas/cross-city/.
CA statewide TIGER exceeds the in-app 80 MiB unzip cap, so this script
downloads/parses outside tiger_state_cache.ensure_state_tiger.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import httpx
import shapefile
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "apps" / "api"))

from app.domain.multicity.geography import (  # noqa: E402
    CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
    MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
)
from app.domain.national_geography_package import (  # noqa: E402
    NATIONAL_AGGREGATION_POLICY_ID,
    NATIONAL_ALGORITHM_ID,
    NATIONAL_CENSUS_VINTAGE,
    NATIONAL_RESOLVER_POLICY_ID,
    canonicalize_geography_geojson,
    geometry_sha256_hex,
)
from app.integrations.fortyguard.partitioning import (  # noqa: E402
    plan_partitions,
    polygon_area_km2,
)
from app.services.aoi_timezone import LonLat  # noqa: E402
from app.services.place_geography_resolver import (  # noqa: E402
    CensusPlaceGeometry,
    CensusTractRecord,
    PlaceGeographySuccess,
    ResolverPolicy,
    resolve_place_geography,
)


def _fixed_timezone_lookup(iana: str):
    """Offline allowlist timezone for curated cross-city places."""

    def lookup(lon: float, lat: float) -> str | None:
        del lon, lat
        return iana

    return lookup

CITIES: tuple[dict[str, str], ...] = (
    {
        "city_id": "phoenix",
        "display_name": "Phoenix",
        "place_geoid": "0455000",
        "state_fips": "04",
        "timezone": "America/Phoenix",
    },
    {
        "city_id": "las_vegas",
        "display_name": "Las Vegas",
        "place_geoid": "3240000",
        "state_fips": "32",
        "timezone": "America/Los_Angeles",
    },
    {
        "city_id": "tucson",
        "display_name": "Tucson",
        "place_geoid": "0477000",
        "state_fips": "04",
        "timezone": "America/Phoenix",
    },
    {
        "city_id": "los_angeles",
        "display_name": "Los Angeles",
        "place_geoid": "0644000",
        "state_fips": "06",
        "timezone": "America/Los_Angeles",
    },
)

OUT_ROOT = REPO / "data" / "areas" / "cross-city"
CACHE_ROOT = REPO / ".cache" / "geography" / "cross_city_tiger"
USER_AGENT = "HVA-Signal/0.1 (cross-city-geography; free Census only)"
RESOLUTION_M = 100


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tiger_url(state_fips: str, kind: str) -> str:
    return (
        f"https://www2.census.gov/geo/tiger/TIGER2025/{kind.upper()}/"
        f"tl_2025_{state_fips}_{kind}.zip"
    )


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1024:
        return dest
    print(f"DOWNLOAD {url}")
    with httpx.Client(
        timeout=httpx.Timeout(120.0, connect=20.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".partial")
            with tmp.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
            tmp.replace(dest)
    return dest


def _rings_to_geometry(shape_rec: Any) -> BaseGeometry:
    parts = list(shape_rec.parts) + [len(shape_rec.points)]
    rings: list[list[tuple[float, float]]] = []
    for index in range(len(parts) - 1):
        start, end = parts[index], parts[index + 1]
        ring = [(float(x), float(y)) for x, y, *_ in shape_rec.points[start:end]]
        if len(ring) >= 4:
            rings.append(ring)
    if not rings:
        raise ValueError("empty shapefile geometry")
    polygons: list[Polygon] = []
    exterior: list[tuple[float, float]] | None = None
    holes: list[list[tuple[float, float]]] = []
    for ring in rings:
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = make_valid(poly)
        # pyshp: first ring exterior; subsequent rings with opposite winding are holes.
        # Use area sign via shapely orientation: treat non-contained rings as new exteriors.
        if exterior is None:
            exterior = ring
            holes = []
            continue
        candidate = Polygon(ring)
        outer = Polygon(exterior)
        if outer.contains(candidate.representative_point()):
            holes.append(ring)
        else:
            polygons.append(Polygon(exterior, holes))
            exterior = ring
            holes = []
    if exterior is not None:
        polygons.append(Polygon(exterior, holes))
    if len(polygons) == 1:
        geom: BaseGeometry = polygons[0]
    else:
        geom = MultiPolygon(polygons)
    if not geom.is_valid:
        geom = make_valid(geom)
    return geom


def _open_shapefile(zip_path: Path) -> shapefile.Reader:
    zf = zipfile.ZipFile(zip_path)
    names = [n for n in zf.namelist() if n.lower().endswith(".shp")]
    if not names:
        raise FileNotFoundError(f"no .shp in {zip_path}")
    stem = names[0][:-4]
    # pyshp can read from zip via vfs path
    return shapefile.Reader(f"{zip_path}/{stem}.shp")


def _field_map(reader: shapefile.Reader) -> dict[str, int]:
    return {field[0].upper(): index for index, field in enumerate(reader.fields[1:])}


def load_place(zip_path: Path, place_geoid: str) -> CensusPlaceGeometry:
    reader = _open_shapefile(zip_path)
    fields = _field_map(reader)
    for sr in reader.iterShapeRecords():
        rec = sr.record
        geoid = str(rec[fields["GEOID"]]).zfill(7)
        if geoid != place_geoid:
            continue
        geom = _rings_to_geometry(sr.shape)
        return CensusPlaceGeometry(
            geometry=geom,
            intpt_lon=float(rec[fields["INTPTLON"]]),
            intpt_lat=float(rec[fields["INTPTLAT"]]),
        )
    raise KeyError(f"place {place_geoid} not found in {zip_path}")


def load_tracts(zip_path: Path, state_fips: str) -> list[CensusTractRecord]:
    reader = _open_shapefile(zip_path)
    fields = _field_map(reader)
    tracts: list[CensusTractRecord] = []
    for sr in reader.iterShapeRecords():
        rec = sr.record
        geoid = str(rec[fields["GEOID"]]).zfill(11)
        if not geoid.startswith(state_fips):
            continue
        geom = _rings_to_geometry(sr.shape)
        tracts.append(
            CensusTractRecord(
                geoid=geoid,
                geometry=geom,
                intpt_lon=float(rec[fields["INTPTLON"]]),
                intpt_lat=float(rec[fields["INTPTLAT"]]),
                aland=float(rec[fields["ALAND"]]),
            )
        )
    return tracts


def _feature_collection(
    success: PlaceGeographySuccess,
    tracts_by_geoid: dict[str, CensusTractRecord],
) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for geoid in success.geoids:
        tract = tracts_by_geoid[geoid]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "GEOID": geoid,
                    "STATEFP": geoid[:2],
                    "COUNTYFP": geoid[2:5],
                    "TRACTCE": geoid[5:],
                    "NAME": geoid[5:],
                    "NAMELSAD": f"Census Tract {geoid[5:]}",
                    "ALAND": tract.aland,
                    "INTPTLAT": f"{tract.intpt_lat:+.7f}",
                    "INTPTLON": f"{tract.intpt_lon:+.7f}",
                },
                "geometry": mapping(tract.geometry),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _area_config(
    *,
    city_id: str,
    place_geoid: str,
    geometry_sha: str,
    zone_count: int,
    expected_zone_ids: list[str],
) -> dict[str, Any]:
    return {
        "area_id": f"cross-city-{city_id}",
        "version": "CROSS_CITY_AREA_CONFIG_V1",
        "selection_policy_version": CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
        "analysis_geography_version": MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
        "comparison_geography_version": CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
        "place_geoid": place_geoid,
        "zone_definition_version": (
            f"US_CENSUS_TIGERLINE.CENSUS_TRACT.{NATIONAL_CENSUS_VINTAGE}."
            f"PLACE_{place_geoid}.{NATIONAL_ALGORITHM_ID}"
        ),
        "zone_type": "census_tract",
        "zone_source": "U.S. Census Bureau 2025 TIGER/Line",
        "zone_geometry_version": (
            f"US_CENSUS_TIGERLINE.CENSUS_TRACT.{NATIONAL_CENSUS_VINTAGE}."
            f"PLACE_{place_geoid}.{CROSS_CITY_COMPARISON_GEOGRAPHY_V1}."
            f"{geometry_sha[:8]}"
        ),
        "expected_zone_count": zone_count,
        "expected_zone_ids": expected_zone_ids,
        "granularity_m": RESOLUTION_M,
        "partition_strategy": "area_ceiling_130km2_grid",
        "partition_policy_version": "FORTYGUARD_PARTITION_CEILING_130KM2_V1",
        "thermal_aggregation": {
            "version": NATIONAL_AGGREGATION_POLICY_ID,
            "assignment_method": "centroid_within",
            "statistic": "mean",
            "minimum_coverage_ratio": None,
            "zero_tile_behavior": "insufficient_evidence",
            "boundary_behavior": "centroid_within_zone",
        },
        "resolver_policy_id": NATIONAL_RESOLVER_POLICY_ID,
        "algorithm_id": NATIONAL_ALGORITHM_ID,
        "gate0_status": "cross_city_comparison_frozen",
    }


def materialize_city(city: dict[str, str], tracts_cache: dict[str, list[CensusTractRecord]]) -> dict[str, Any]:
    state = city["state_fips"]
    place_zip = _download(_tiger_url(state, "place"), CACHE_ROOT / state / f"tl_2025_{state}_place.zip")
    tract_zip = _download(_tiger_url(state, "tract"), CACHE_ROOT / state / f"tl_2025_{state}_tract.zip")
    place = load_place(place_zip, city["place_geoid"])
    if state not in tracts_cache:
        print(f"PARSE tracts state={state}")
        tracts_cache[state] = load_tracts(tract_zip, state)
    tracts = tracts_cache[state]
    tracts_by_geoid = {t.geoid: t for t in tracts}
    print(f"RESOLVE {city['city_id']} place={city['place_geoid']} tracts={len(tracts)}")
    outcome = resolve_place_geography(
        {"place_geoid": city["place_geoid"], "state_fips": state},
        place,
        tracts,
        ResolverPolicy(timezone_lookup=_fixed_timezone_lookup(city["timezone"])),
    )
    if not isinstance(outcome, PlaceGeographySuccess):
        raise RuntimeError(f"{city['city_id']} ALG1 failed: {outcome}")

    fc = _feature_collection(outcome, tracts_by_geoid)
    canonical = canonicalize_geography_geojson(fc)
    geom_bytes = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    geom_sha = geometry_sha256_hex(canonical)
    selected = list(outcome.geoids)
    tract_hashes = {
        geoid: hashlib.sha256(
            json.dumps(
                mapping(tracts_by_geoid[geoid].geometry),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        for geoid in selected
    }
    union = unary_union([tracts_by_geoid[g].geometry for g in selected])
    union_poly = mapping(union if union.geom_type != "GeometryCollection" else union.buffer(0))
    # Provider adapter accepts polygon_aoi; use dissolved MultiPolygon/Polygon.
    if union_poly["type"] == "GeometryCollection":
        polys = [g for g in union.geoms if g.geom_type in {"Polygon", "MultiPolygon"}]
        union = unary_union(polys)
        union_poly = mapping(union)
    area_km2 = polygon_area_km2(union_poly)
    envelope = {
        "type": "Polygon",
        "coordinates": [
            [
                [union.bounds[0], union.bounds[1]],
                [union.bounds[2], union.bounds[1]],
                [union.bounds[2], union.bounds[3]],
                [union.bounds[0], union.bounds[3]],
                [union.bounds[0], union.bounds[1]],
            ]
        ],
    }
    envelope_km2 = polygon_area_km2(envelope)
    partitions = plan_partitions(union_poly)
    expected_tiles = max(
        len(partitions),
        int((area_km2 * 1_000_000.0) // float(RESOLUTION_M * RESOLUTION_M) + 1),
    )
    envelope_tiles = max(
        1,
        int((envelope_km2 * 1_000_000.0) // float(RESOLUTION_M * RESOLUTION_M) + 1),
    )
    area_config = _area_config(
        city_id=city["city_id"],
        place_geoid=city["place_geoid"],
        geometry_sha=geom_sha,
        zone_count=len(selected),
        expected_zone_ids=selected,
    )
    area_config_text = json.dumps(area_config, indent=2, sort_keys=True) + "\n"
    area_config_sha = _sha256_text(area_config_text)

    out_dir = OUT_ROOT / city["city_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    geometry_path = out_dir / "geometry.geojson"
    geometry_path.write_text(
        json.dumps(canonical, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "area_config.json").write_text(area_config_text, encoding="utf-8")
    provider_aoi_path = out_dir / "provider_polygon_aoi.geojson"
    provider_aoi_path.write_text(
        json.dumps(union_poly, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    freeze = {
        "city_id": city["city_id"],
        "display_name": city["display_name"],
        "place_geoid": city["place_geoid"],
        "timezone": city["timezone"],
        "timezone_source": "CITY_ALLOWLIST_IANA_V1",
        "selection_policy_version": CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
        "analysis_geography_version": MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
        "resolver_policy_id": NATIONAL_RESOLVER_POLICY_ID,
        "algorithm_id": NATIONAL_ALGORITHM_ID,
        "census_vintage": NATIONAL_CENSUS_VINTAGE,
        "exact_tract_geoids": selected,
        "analysis_area_count": len(selected),
        "tract_geometry_hashes": tract_hashes,
        "combined_geometry_hash": geom_sha,
        "area_config_hash": area_config_sha,
        "total_union_area_km2": round(area_km2, 6),
        "union_bounding_envelope": {
            "min_lon": union.bounds[0],
            "min_lat": union.bounds[1],
            "max_lon": union.bounds[2],
            "max_lat": union.bounds[3],
            "area_km2": round(envelope_km2, 6),
        },
        "geometry_version": area_config["zone_geometry_version"],
        "aggregation_policy": NATIONAL_AGGREGATION_POLICY_ID,
        "expected_zone_ids": selected,
        "seed_geoid": outcome.seed_geoid,
        "seed_rule": outcome.seed_rule,
        "provider_request": {
            "shape": "polygon_aoi_dissolved_union",
            "adapter_evidence": "build_heatmap_payload uses request.polygon_aoi",
            "analysis_union_area_km2": round(area_km2, 6),
            "provider_request_area_km2": round(area_km2, 6),
            "bounding_envelope_area_km2": round(envelope_km2, 6),
            "why_differ": (
                "Adapter sends dissolved analysis-union polygon, not the bounding "
                "envelope alone. Envelope area is reported for overhead awareness; "
                "partitions clip the union polygon to the 130 km2 ceiling."
            ),
            "partition_policy": "FORTYGUARD_PARTITION_CEILING_130KM2_V1",
            "partitions": len(partitions),
            "expected_provider_cells_tiles_union": expected_tiles,
            "expected_provider_cells_tiles_envelope": envelope_tiles,
            "resolution_m": RESOLUTION_M,
            "overhead_ratio_envelope_vs_union": round(envelope_km2 / area_km2, 4)
            if area_km2 > 0
            else None,
        },
        "paths": {
            "geometry": str(geometry_path.relative_to(REPO).as_posix()),
            "area_config": str((out_dir / "area_config.json").relative_to(REPO).as_posix()),
            "provider_polygon_aoi": str(provider_aoi_path.relative_to(REPO).as_posix()),
        },
    }
    (out_dir / "freeze.json").write_text(
        json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"OK {city['city_id']}: zones={len(selected)} union_km2={area_km2:.3f} "
        f"parts={len(partitions)} geom={geom_sha[:12]}"
    )
    return freeze


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    tracts_cache: dict[str, list[CensusTractRecord]] = {}
    freezes: list[dict[str, Any]] = []
    for city in CITIES:
        freezes.append(materialize_city(city, tracts_cache))
    index = {
        "contract": CROSS_CITY_COMPARISON_GEOGRAPHY_V1,
        "analysis_geography_version": MULTI_CITY_ANALYSIS_GEOGRAPHY_V1,
        "cities": freezes,
    }
    (OUT_ROOT / "INDEX.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"WROTE {OUT_ROOT / 'INDEX.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
