"""National resolver geometry: CRS, metrics, repair, multipart, hash."""

from __future__ import annotations

import hashlib
import json

import pytest
from shapely.geometry import MultiPolygon, Polygon, mapping


def _box(lon0: float, lat0: float, lon1: float, lat1: float) -> Polygon:
    return Polygon(
        [
            (lon0, lat0),
            (lon1, lat0),
            (lon1, lat1),
            (lon0, lat1),
            (lon0, lat0),
        ]
    )


def test_origin_projects_to_5070_false_origin() -> None:
    from app.services.national_geometry import lonlat_to_5070

    x, y = lonlat_to_5070(-96.0, 23.0)
    assert abs(x) < 1e-6
    assert abs(y) < 1e-6


def test_phoenix_and_dc_match_proj_control_points() -> None:
    from app.services.national_geometry import lonlat_to_5070, xy5070_to_lonlat

    x, y = lonlat_to_5070(-112.0740, 33.4484)
    assert x == pytest.approx(-1477242.845010892, abs=1e-3)
    assert y == pytest.approx(1278582.822713835, abs=1e-3)
    lon, lat = xy5070_to_lonlat(x, y)
    assert lon == pytest.approx(-112.0740, abs=1e-9)
    assert lat == pytest.approx(33.4484, abs=1e-9)
    x, y = lonlat_to_5070(-77.0369, 38.9072)
    assert x == pytest.approx(1618355.2979319915, abs=1e-3)
    assert y == pytest.approx(1926511.4991328965, abs=1e-3)


def test_phoenix_utm12n_is_forbidden_as_national_analysis_crs() -> None:
    from app.services.national_geometry import (
        ForbiddenAnalysisCRSError,
        require_analysis_crs,
    )

    require_analysis_crs("EPSG:5070")
    require_analysis_crs("epsg:5070")
    with pytest.raises(ForbiddenAnalysisCRSError, match="32612"):
        require_analysis_crs("EPSG:32612")
    with pytest.raises(ForbiddenAnalysisCRSError, match="32612"):
        require_analysis_crs("32612")
    with pytest.raises(ForbiddenAnalysisCRSError, match="26912"):
        require_analysis_crs("EPSG:26912")
    with pytest.raises(ForbiddenAnalysisCRSError, match="26912"):
        require_analysis_crs("26912")


def test_alaska_hawaii_territories_are_out_of_scope() -> None:
    from app.services.national_geometry import (
        UnsupportedTerritoryError,
        require_conus_dc_statefp,
    )

    require_conus_dc_statefp("04")
    require_conus_dc_statefp("11")
    require_conus_dc_statefp(4)
    for fips in ("02", "15", "60", "66", "69", "72", "78"):
        with pytest.raises(UnsupportedTerritoryError, match=fips):
            require_conus_dc_statefp(fips)
    with pytest.raises(UnsupportedTerritoryError, match="02"):
        require_conus_dc_statefp(2)
    with pytest.raises(UnsupportedTerritoryError, match="missing"):
        require_conus_dc_statefp(None)
    with pytest.raises(UnsupportedTerritoryError, match="missing"):
        require_conus_dc_statefp("")


def test_centroid_outside_conus_dc_box_is_rejected() -> None:
    from app.services.national_geometry import (
        UnsupportedTerritoryError,
        require_conus_dc_lonlat,
    )

    require_conus_dc_lonlat(-112.0740, 33.4484)
    with pytest.raises(UnsupportedTerritoryError, match="scope"):
        require_conus_dc_lonlat(-157.8583, 21.3069)
    with pytest.raises(UnsupportedTerritoryError, match="scope"):
        require_conus_dc_lonlat(-149.9003, 61.2181)


def test_local_utm_zone_is_diagnostic_only() -> None:
    from app.services.national_geometry import utm_zone_from_lon

    assert utm_zone_from_lon(-112.0740) == 12
    assert utm_zone_from_lon(-77.0369) == 18
    assert utm_zone_from_lon(-87.6298) == 16


def test_planar_metrics_are_positive_and_pp_in_unit_interval() -> None:
    from app.services.national_geometry import planar_metrics

    geom = _box(-112.10, 33.40, -112.09, 33.41)
    metrics = planar_metrics(geom)
    assert metrics.crs == "EPSG:5070"
    assert metrics.scope == "CONUS_DC"
    assert metrics.land_oriented is False
    assert metrics.area_m2 > 0
    assert metrics.perimeter_m > 0
    assert 0 < metrics.polsby_popper < 1
    assert metrics.pp_raw == metrics.polsby_popper
    assert metrics.pp_compare == round(metrics.pp_raw, 6)
    assert metrics.pp_compare == round(metrics.polsby_popper, 6)


def test_land_oriented_polsby_popper_from_aland_is_refused() -> None:
    from app.services.national_geometry import (
        LandOrientedPolsbyPopperError,
        planar_metrics,
    )

    geom = _box(-112.10, 33.40, -112.09, 33.41)
    with pytest.raises(LandOrientedPolsbyPopperError, match="ALAND"):
        planar_metrics(geom, land_area_m2=1000.0)


def test_planar_distance_is_finite_metres() -> None:
    from app.services.national_geometry import planar_distance_m

    metres = planar_distance_m(-112.0740, 33.4484, -112.0640, 33.4484)
    assert 800 < metres < 1200


def test_computation_copy_does_not_rewrite_official_rings() -> None:
    from app.services.national_geometry import computation_geometry, official_rings_unchanged

    official = _box(-112.10, 33.40, -112.09, 33.41)
    official_mapping = mapping(official)
    projected = computation_geometry(official)
    assert projected.is_valid
    assert official_rings_unchanged(official_mapping, mapping(official))


def test_self_crossing_bowtie_is_rejected_as_material_rewrite() -> None:
    from app.services.national_geometry import GeometryRepairRejected, computation_geometry

    bowtie = Polygon(
        [
            (-112.10, 33.40),
            (-112.09, 33.41),
            (-112.10, 33.41),
            (-112.09, 33.40),
            (-112.10, 33.40),
        ]
    )
    assert bowtie.is_valid is False
    with pytest.raises(GeometryRepairRejected, match="area"):
        computation_geometry(bowtie)


def test_make_valid_material_area_change_is_rejected() -> None:
    from app.services.national_geometry import (
        GeometryRepairRejected,
        computation_geometry,
    )

    emptyish = Polygon()
    with pytest.raises(GeometryRepairRejected):
        computation_geometry(emptyish)


def test_seed_component_must_support_twenty_five() -> None:
    from app.services.national_geometry import (
        ComponentTooSmallError,
        connected_component,
        require_component_supports_target,
    )

    island = {
        "I1": ["I2"],
        "I2": ["I1", "I3"],
        "I3": ["I2"],
    }
    mainland = {f"M{i:02d}": [] for i in range(30)}
    for i in range(29):
        a, b = f"M{i:02d}", f"M{i + 1:02d}"
        mainland[a].append(b)
        mainland[b].append(a)
    graph = {**island, **mainland}

    island_component = connected_component(graph, "I1")
    assert island_component == frozenset({"I1", "I2", "I3"})
    with pytest.raises(ComponentTooSmallError, match="25"):
        require_component_supports_target(island_component)

    land_component = connected_component(graph, "M00")
    assert len(land_component) == 30
    assert "I1" not in land_component
    require_component_supports_target(land_component)


def test_missing_seed_fails_closed() -> None:
    from app.services.national_geometry import NationalGeometryError, connected_component

    with pytest.raises(NationalGeometryError, match="seed"):
        connected_component({"A": []}, "MISSING")


def test_canonical_feature_order_is_geoid_and_hash_is_stable() -> None:
    from app.services.national_geometry import (
        canonical_sha256,
        canonicalize_feature_collection,
        dump_canonical,
        source_bytes_sha256,
    )

    features = [
        {
            "type": "Feature",
            "properties": {
                "NAME": "b",
                "GEOID": "04013107500",
                "STATEFP": "04",
                "ALAND": 2,
                "selection_order": 1,
            },
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        },
        {
            "type": "Feature",
            "properties": {
                "GEOID": "04013107401",
                "NAME": "a",
                "STATEFP": "04",
                "ALAND": 1,
                "selection_order": 2,
            },
            "geometry": {"type": "Polygon", "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 2]]]},
        },
    ]
    payload = canonicalize_feature_collection(
        features,
        name="TEST_NATIONAL_V1",
        collection_properties={"seed_geoid": "04013107401", "policy_version": "V1"},
    )
    assert [f["properties"]["GEOID"] for f in payload["features"]] == [
        "04013107401",
        "04013107500",
    ]
    assert list(payload.keys()) == ["type", "name", "crs", "properties", "features"]
    assert list(payload["features"][0]["properties"].keys())[0] == "GEOID"
    assert payload["crs"]["properties"]["name"] == "urn:ogc:def:crs:EPSG::4269"
    digest = canonical_sha256(payload)
    assert digest == hashlib.sha256(dump_canonical(payload)).hexdigest()
    assert digest == canonical_sha256(payload)
    raw = b'{"not":"canonical"}'
    assert source_bytes_sha256(raw) == hashlib.sha256(raw).hexdigest()
    assert source_bytes_sha256(raw) != digest


def test_canonical_dump_has_no_spaces() -> None:
    from app.services.national_geometry import canonicalize_feature_collection, dump_canonical

    payload = canonicalize_feature_collection(
        [
            {
                "type": "Feature",
                "properties": {"GEOID": "1"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
        name="X",
        collection_properties={},
    )
    raw = dump_canonical(payload)
    assert b": " not in raw
    assert raw.decode("utf-8") == json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    )


def test_multipart_official_geometry_keeps_all_parts() -> None:
    from app.services.national_geometry import planar_metrics

    a = _box(-112.10, 33.40, -112.09, 33.41)
    b = _box(-112.07, 33.40, -112.06, 33.41)
    multi = MultiPolygon([a, b])
    metrics = planar_metrics(multi)
    single = planar_metrics(a)
    assert metrics.area_m2 == pytest.approx(2 * single.area_m2, rel=0.05)


def test_pp_compare_rounds_six_decimals_pp_raw_stays_unrounded() -> None:
    from app.services.national_geometry import compare_polsby_popper, planar_metrics

    metrics = planar_metrics(_box(-112.10, 33.40, -112.09, 33.41))
    assert metrics.pp_raw == metrics.polsby_popper
    assert metrics.pp_compare == round(metrics.pp_raw, 6)
    assert metrics.pp_compare == compare_polsby_popper(metrics.pp_raw)
    raw_text = f"{metrics.pp_raw:.12f}"
    assert raw_text != f"{metrics.pp_compare:.12f}"


def test_missing_statefp_requires_conus_dc_centroid() -> None:
    from app.services.national_geometry import (
        UnsupportedTerritoryError,
        require_place_scope,
    )

    require_place_scope("04")
    require_place_scope(None, lon=-112.0740, lat=33.4484)
    with pytest.raises(UnsupportedTerritoryError, match="centroid"):
        require_place_scope(None)
    with pytest.raises(UnsupportedTerritoryError, match="15"):
        require_place_scope("15", lon=-157.8583, lat=21.3069)


def test_canonical_geometry_is_source_rings_not_make_valid() -> None:
    from shapely.validation import make_valid

    from app.services.national_geometry import canonicalize_feature_collection

    official_coords = [
        [
            [-112.10, 33.40],
            [-112.09, 33.41],
            [-112.10, 33.41],
            [-112.09, 33.40],
            [-112.10, 33.40],
        ]
    ]
    official_geom = {"type": "Polygon", "coordinates": official_coords}
    bowtie = Polygon([(x, y) for x, y in official_coords[0]])
    assert bowtie.is_valid is False
    repaired_mapping = mapping(make_valid(bowtie))
    payload = canonicalize_feature_collection(
        [
            {
                "type": "Feature",
                "properties": {"GEOID": "04013107401"},
                "geometry": official_geom,
            }
        ],
        name="TEST_NATIONAL_V1",
        collection_properties={},
    )
    published = payload["features"][0]["geometry"]
    assert published is official_geom
    assert published["coordinates"] == official_coords
    assert published != repaired_mapping


def test_pretty_source_bytes_hash_is_not_canonical_hash() -> None:
    from app.services.national_geometry import (
        canonical_sha256,
        canonicalize_feature_collection,
        dump_canonical,
        source_bytes_sha256,
    )

    payload = canonicalize_feature_collection(
        [
            {
                "type": "Feature",
                "properties": {"GEOID": "1"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
        name="X",
        collection_properties={},
    )
    pretty = json.dumps(payload, indent=2).encode("utf-8")
    assert source_bytes_sha256(pretty) != canonical_sha256(payload)
    assert source_bytes_sha256(pretty) != hashlib.sha256(dump_canonical(payload)).hexdigest()


def test_union_metrics_use_projected_copies() -> None:
    from app.services.national_geometry import planar_metrics, union_planar_metrics

    a = _box(-112.10, 33.40, -112.09, 33.41)
    b = _box(-112.09, 33.40, -112.08, 33.41)
    unioned = union_planar_metrics([a, b])
    single = planar_metrics(a)
    assert unioned.area_m2 == pytest.approx(2 * single.area_m2, rel=0.05)
    assert unioned.pp_raw == unioned.polsby_popper
    assert unioned.pp_compare == round(unioned.pp_raw, 6)
    assert unioned.crs == "EPSG:5070"


def test_projected_metres_are_rejected_as_official_rings() -> None:
    from app.services.national_geometry import NationalGeometryError, computation_geometry

    metres = Polygon([(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0), (0.0, 0.0)])
    with pytest.raises(NationalGeometryError, match="4269"):
        computation_geometry(metres)
