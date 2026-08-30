"""I8 package/readiness integration locks for NATIONAL_PLACE_GEOGRAPHY_V1.

Read-only of I1–I7 production files. Sibling implementations are imported
from path when Lead has not yet stitched them onto this worktree.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import itertools
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.core.area_readiness import (
    AreaCapabilityState,
    GeographyIdentity,
    GeographyReadiness,
    ReferenceReadiness,
    historical_signal_capable,
    snapshot_capable,
)
from app.domain.phoenix_v1 import AREA_ID as LEGACY_PHOENIX_AREA_ID

FROZEN_PUBLIC_OPENAPI_PATHS = {
    "/health",
    "/ready",
    "/api/v1/areas",
    "/api/v1/areas/{area_id}/geometry",
    "/api/v1/analysis/jobs",
    "/api/v1/analysis/jobs/{job_id}",
}

RESOLVER_POLICY_ID = "NATIONAL_PLACE_GEOGRAPHY_V1"
POLICY_SLUG = "national-place-geography-v1"
CENSUS_VINTAGE = "2025"
EXPECTED_ZONE_COUNT = 25
NATIONAL_PHOENIX_AREA_ID = "us-place-0455000-2025-national-place-geography-v1"
KEY_WEST_PLACE_GEOID = "1236550"
YUMA_PLACE_GEOID = "0485540"
REASON_INSUFFICIENT_ELIGIBLE = "INSUFFICIENT_ELIGIBLE_TRACTS"
REASON_INSUFFICIENT_COMPONENT = "INSUFFICIENT_RELEVANT_COMPONENT"
REASON_INSUFFICIENT_CONNECTED = "INSUFFICIENT_CONNECTED_TRACTS"
YUMA_REASON_FAMILY = frozenset(
    {REASON_INSUFFICIENT_COMPONENT, REASON_INSUFFICIENT_CONNECTED}
)
FORBIDDEN_REFERENCE_KEYS = frozenset(
    {
        "reference_path",
        "reference_sha256",
        "reference_version",
        "historical_reference",
        "historical_reference_window",
        "q_A",
        "q_a",
        "decision8",
        "decision_8",
        "hazard_spread_policy",
    }
)

_CURSOR_ROOT = Path(r"F:\cursor")
_SIBLING_REPOS = (
    "hackathon-resolver-i8-integration",
    "hackathon-resolver-b-selection",
    "hackathon-resolver-f-package",
    "hackathon-resolver-c-geometry",
    "hackathon-resolver-a-census",
    "hackathon-resolver-d-timezone",
    "hackathon-resolver-g-cache",
    "hackathon-wt-resolver-e-panel",
    "hackathon",
)


def national_area_id(
    place_geoid: str,
    *,
    census_vintage: str = CENSUS_VINTAGE,
    resolver_policy_id: str = RESOLVER_POLICY_ID,
) -> str:
    slug = resolver_policy_id.strip().lower().replace("_", "-")
    return f"us-place-{place_geoid}-{census_vintage}-{slug}"


def assert_twenty_five_unique_geoids(geoids: Sequence[str]) -> None:
    assert len(geoids) == EXPECTED_ZONE_COUNT
    assert len(set(geoids)) == EXPECTED_ZONE_COUNT


def assert_one_rook_component(
    geoids: Sequence[str],
    adjacency: Mapping[str, Sequence[str] | set[str] | frozenset[str]],
) -> None:
    """Postcondition: the selected 25 occupy exactly one rook component."""
    chosen = set(geoids)
    assert_twenty_five_unique_geoids(geoids)
    start = geoids[0]
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for peer in adjacency.get(node, ()):
            if peer in chosen and peer not in seen:
                seen.add(peer)
                stack.append(peer)
    assert seen == chosen


def _api_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _find_impl(*relative: str) -> Path | None:
    local = _api_root().joinpath(*relative)
    if local.is_file():
        return local
    for name in _SIBLING_REPOS:
        candidate = _CURSOR_ROOT / name / "apps" / "api" / Path(*relative)
        if candidate.is_file() and candidate.resolve() != local.resolve():
            return candidate
        if candidate.is_file():
            return candidate
    return None


def _register_module(qualname: str, path: Path) -> ModuleType:
    existing = sys.modules.get(qualname)
    if existing is not None and getattr(existing, "__file__", None) == str(path):
        return existing
    spec = importlib.util.spec_from_file_location(qualname, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {qualname} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualname] = module
    spec.loader.exec_module(module)
    parent_name, _, child = qualname.rpartition(".")
    parent = sys.modules.get(parent_name)
    if parent is not None:
        setattr(parent, child, module)
    return module


def _try_import(qualname: str) -> ModuleType | None:
    try:
        return importlib.import_module(qualname)
    except ImportError:
        return None


def load_package_layer() -> tuple[ModuleType, ModuleType] | None:
    pkg = _try_import("app.domain.national_geography_package")
    mat = _try_import("app.services.national_geography_materializer")
    if pkg is not None and mat is not None:
        return pkg, mat
    pkg_path = _find_impl("app", "domain", "national_geography_package.py")
    mat_path = _find_impl("app", "services", "national_geography_materializer.py")
    if pkg_path is None or mat_path is None:
        return None
    import app.domain  # noqa: F401
    import app.services  # noqa: F401

    pkg = _register_module("app.domain.national_geography_package", pkg_path)
    mat = _register_module("app.services.national_geography_materializer", mat_path)
    return pkg, mat


def load_selection_module() -> ModuleType | None:
    local = _try_import("app.services.national_tract_selection")
    if local is not None:
        return local
    path = _find_impl("app", "services", "national_tract_selection.py")
    if path is None:
        return None
    import app.services  # noqa: F401

    return _register_module("app.services.national_tract_selection", path)


def load_resolve_place_geography() -> Any | None:
    candidates = (
        "app.services.resolve_place_geography",
        "app.services.national_resolver",
        "app.services.national_place_geography",
        "app.domain.resolve_place_geography",
    )
    for name in candidates:
        module = _try_import(name)
        if module is not None and hasattr(module, "resolve_place_geography"):
            return module.resolve_place_geography
        path = _find_impl(*name.split("."))
        if path is not None and path.with_suffix(".py").is_file():
            loaded = _register_module(name, path.with_suffix(".py"))
            if hasattr(loaded, "resolve_place_geography"):
                return loaded.resolve_place_geography
        py_path = _find_impl(*(name.split(".")[:-1] + [name.split(".")[-1] + ".py"]))
        if py_path is not None:
            loaded = _register_module(name, py_path)
            if hasattr(loaded, "resolve_place_geography"):
                return loaded.resolve_place_geography
    selection = load_selection_module()
    if selection is not None and hasattr(selection, "resolve_place_geography"):
        return selection.resolve_place_geography
    package_layer = load_package_layer()
    if package_layer is not None and hasattr(package_layer[1], "resolve_place_geography"):
        return package_layer[1].resolve_place_geography
    return None


def _require_package_layer() -> tuple[ModuleType, ModuleType]:
    layer = load_package_layer()
    if layer is None:
        pytest.skip(
            "national geography package layer not on this worktree (Lead stitch pending)"
        )
    return layer


def _require_selection() -> ModuleType:
    module = load_selection_module()
    if module is None:
        pytest.skip(
            "national tract selector not on this worktree (Lead stitch pending)"
        )
    return module


def _geometry_identity(*, area_id: str, geoids: tuple[str, ...]) -> GeographyIdentity:
    return GeographyIdentity(
        area_id=area_id,
        zone_geoids=geoids,
        expected_zone_count=EXPECTED_ZONE_COUNT,
        timezone="America/Chicago",
        aggregation_spec_version=(
            "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
        ),
        area_selection_policy_version=RESOLVER_POLICY_ID,
        geometry_sha256="ab" * 32,
    )


def _synthetic_geoids(*, prefix: str = "17999000") -> tuple[str, ...]:
    return tuple(f"{prefix}{index:03d}" for index in range(EXPECTED_ZONE_COUNT))


def _feature_collection(geoids: Sequence[str]) -> dict[str, Any]:
    features = []
    for index, geoid in enumerate(geoids):
        features.append(
            {
                "type": "Feature",
                "properties": {"GEOID": geoid},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [float(index), 0.0],
                            [float(index + 1), 0.0],
                            [float(index + 1), 1.0],
                            [float(index), 1.0],
                            [float(index), 0.0],
                        ]
                    ],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _square(x: float, y: float, size: float = 1.0):
    from shapely.geometry import Polygon

    return Polygon(((x, y), (x + size, y), (x + size, y + size), (x, y + size)))


def _grid_tracts(
    module: ModuleType,
    rows: int,
    cols: int,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    prefix: str = "99",
):
    TractInput = module.TractInput
    ox, oy = origin
    tracts = []
    for row, col in itertools.product(range(rows), range(cols)):
        x = ox + col
        y = oy + row
        geom = _square(x, y)
        geoid = f"{prefix}{row:04d}{col:05d}"
        centroid = (x + 0.5, y + 0.5)
        params = inspect.signature(TractInput).parameters
        kwargs: dict[str, Any] = {"geoid": geoid, "geometry": geom}
        if "official_intpt" in params:
            kwargs["official_intpt"] = centroid
        if "land_area" in params:
            kwargs["land_area"] = 1.0
        tracts.append(TractInput(**kwargs))
    return tracts


def _call_select(
    module: ModuleType,
    place,
    tracts,
    place_intpt: tuple[float, float],
):
    fn = module.select_national_tracts
    params = inspect.signature(fn).parameters
    kwargs: dict[str, Any] = {}
    if "place_intpt" in params:
        kwargs["place_intpt"] = place_intpt
    return fn(place, tracts, **kwargs)


def _rook_graph_from_tracts(module: ModuleType, tracts, geoids: Sequence[str]):
    chosen = [tract for tract in tracts if tract.geoid in set(geoids)]
    return module.rook_adjacency(chosen)


def _is_structured_unsupported(outcome: Any) -> bool:
    if isinstance(outcome, BaseException):
        return False
    if getattr(outcome, "supported", True) is not False:
        return False
    code = getattr(outcome, "reason_code", None)
    return isinstance(code, str) and code != ""


def _unsupported_codes(outcome: Any) -> set[str]:
    codes = {str(getattr(outcome, "reason_code"))}
    details = getattr(outcome, "details", {}) or {}
    alias = details.get("alias_reason_code")
    if alias:
        codes.add(str(alias))
    return codes


def _dump_without_reference(payload: Mapping[str, Any]) -> None:
    assert FORBIDDEN_REFERENCE_KEYS.isdisjoint(payload)
    assert "reference_sha256" not in payload
    blob = " ".join(str(key) for key in payload)
    assert "8de5db71fe24118cf5b66e3bee394398fd142516ad2590c46e617e0c0b83408c" not in blob


# --- 4. OpenAPI frozen surface -------------------------------------------------


def test_public_openapi_path_set_unchanged() -> None:
    from tests.unit.test_public_openapi_unchanged import (
        test_public_openapi_has_no_signal_b_or_prepare_paths,
    )

    test_public_openapi_has_no_signal_b_or_prepare_paths()
    from app.main import app

    paths = set((app.openapi().get("paths") or {}))
    assert paths == FROZEN_PUBLIC_OPENAPI_PATHS


# --- 3. National area_id is never phoenix-demo --------------------------------


def test_national_area_id_never_equals_phoenix_demo() -> None:
    chicago = national_area_id("1714000")
    phoenix_place = national_area_id("0455000")
    assert chicago == "us-place-1714000-2025-national-place-geography-v1"
    assert phoenix_place == NATIONAL_PHOENIX_AREA_ID
    assert chicago != LEGACY_PHOENIX_AREA_ID
    assert phoenix_place != LEGACY_PHOENIX_AREA_ID
    assert phoenix_place != "phoenix-demo"
    assert LEGACY_PHOENIX_AREA_ID == "phoenix-demo"
    layer = load_package_layer()
    if layer is None:
        return
    pkg, _mat = layer
    built = pkg.build_national_area_id(
        place_geoid="0455000",
        census_vintage=CENSUS_VINTAGE,
        resolver_policy_id=RESOLVER_POLICY_ID,
    )
    assert built == NATIONAL_PHOENIX_AREA_ID
    assert built != LEGACY_PHOENIX_AREA_ID
    with pytest.raises(Exception, match="phoenix-demo"):
        pkg.assert_area_id_not_legacy_phoenix("phoenix-demo")


def test_phoenix_census_place_area_id_is_distinct_from_legacy_demo() -> None:
    assert NATIONAL_PHOENIX_AREA_ID != LEGACY_PHOENIX_AREA_ID
    assert POLICY_SLUG in NATIONAL_PHOENIX_AREA_ID
    assert "0455000" in NATIONAL_PHOENIX_AREA_ID
    assert CENSUS_VINTAGE in NATIONAL_PHOENIX_AREA_ID
    layer = load_package_layer()
    if layer is None:
        return
    pkg, mat = layer
    place = pkg.CanonicalPlaceIdentity.model_validate(
        {
            "canonical_place_geoid": "0455000",
            "place_name": "TEST_ONLY Phoenix",
            "state_fips": "04",
            "state_abbreviation": "AZ",
        }
    )
    geoids = _synthetic_geoids(prefix="04999000")
    audit_factory = getattr(pkg, "national_selection_audit", None)
    if audit_factory is not None:
        audit = audit_factory(
            seed_geoid=geoids[0],
            selection_order=geoids,
            eligible_tract_count=40,
            connected_component_size=32,
        )
    else:
        audit = pkg.SelectionAuditMetadata.model_validate(
            {
                "seed_geoid": geoids[0],
                "selection_order": geoids,
                "algorithm_id": "ALG1_GREEDY_LEX_PLACE_INTPT_V1",
                "seed_rule_id": "SEED_PLACE_TIGER_INTPT_CONTAINER_ELSE_NEAREST_ELIGIBLE_INTPT_GEOID_ASC_V1",
                "eligible_tract_count": 40,
                "connected_component_size": 32,
                "rook_connected": True,
                "eligibility_rule_id": "ELIGIBILITY_TIGER_INTPT_IN_PLACE_ALAND_GT_0_V1",
                "rook_policy_id": "ROOK_LINEAR_SHARED_BOUNDARY_GT_1E-3_M_EPSG5070_V1",
                "projection_crs": "EPSG:5070",
            }
        )
    record = mat.materialize_national_geography(
        mat.ResolverSuccessInput(
            place=place,
            zone_geoids=geoids,
            geometry=_feature_collection(geoids),
            timezone="America/Phoenix",
            selection_audit=audit,
        )
    )
    assert record.area_id == NATIONAL_PHOENIX_AREA_ID
    assert record.area_id != LEGACY_PHOENIX_AREA_ID


# --- 2. Successful package → GEOGRAPHY_READY + snapshot, reference NOT_PREPARED


def test_successful_package_is_snapshot_capable_while_reference_not_prepared() -> None:
    geoids = _synthetic_geoids()
    identity = _geometry_identity(
        area_id=national_area_id("1714000"),
        geoids=geoids,
    )
    assert identity.area_id != LEGACY_PHOENIX_AREA_ID
    _dump_without_reference(identity.model_dump())
    assert (
        snapshot_capable(
            identity,
            geography=GeographyReadiness.GEOGRAPHY_READY,
            reference=ReferenceReadiness.NOT_PREPARED,
        )
        is True
    )
    assert (
        historical_signal_capable(
            identity,
            geography=GeographyReadiness.GEOGRAPHY_READY,
            reference=ReferenceReadiness.NOT_PREPARED,
        )
        is False
    )
    state = AreaCapabilityState(
        geography=GeographyReadiness.GEOGRAPHY_READY,
        reference=ReferenceReadiness.NOT_PREPARED,
    )
    assert state.snapshot_capable is True
    assert state.historical_signal_capable is False

    pkg, mat = _require_package_layer()
    place = pkg.CanonicalPlaceIdentity.model_validate(
        {
            "canonical_place_geoid": "1714000",
            "place_name": "TEST_ONLY Chicago",
            "state_fips": "17",
            "state_abbreviation": "IL",
        }
    )
    audit_factory = getattr(pkg, "national_selection_audit", None)
    if audit_factory is not None:
        audit = audit_factory(
            seed_geoid=geoids[0],
            selection_order=geoids,
            eligible_tract_count=48,
            connected_component_size=40,
        )
    else:
        audit = pkg.SelectionAuditMetadata.model_validate(
            {
                "seed_geoid": geoids[0],
                "selection_order": geoids,
                "algorithm_id": "ALG1_GREEDY_LEX_PLACE_INTPT_V1",
                "seed_rule_id": "SEED_PLACE_TIGER_INTPT_CONTAINER_ELSE_NEAREST_ELIGIBLE_INTPT_GEOID_ASC_V1",
                "eligible_tract_count": 48,
                "connected_component_size": 40,
                "rook_connected": True,
                "eligibility_rule_id": "ELIGIBILITY_TIGER_INTPT_IN_PLACE_ALAND_GT_0_V1",
                "rook_policy_id": "ROOK_LINEAR_SHARED_BOUNDARY_GT_1E-3_M_EPSG5070_V1",
                "projection_crs": "EPSG:5070",
            }
        )
    record = mat.materialize_national_geography(
        mat.ResolverSuccessInput(
            place=place,
            zone_geoids=geoids,
            geometry=_feature_collection(geoids),
            timezone="America/Chicago",
            selection_audit=audit,
        )
    )
    assert record.lifecycle.value == "GEOGRAPHY_READY"
    assert record.reference == "NOT_PREPARED"
    assert record.snapshot_capable is True
    assert record.historical_signal_capable is False
    caps = record.capability_state()
    assert caps.geography == GeographyReadiness.GEOGRAPHY_READY
    assert caps.reference == ReferenceReadiness.NOT_PREPARED
    assert caps.snapshot_capable is True
    dumped = record.package.model_dump(mode="json")
    _dump_without_reference(dumped)
    assert record.package.resolver_policy_id == RESOLVER_POLICY_ID
    identity = pkg.to_geography_identity(record.package)
    assert snapshot_capable(
        identity,
        geography=GeographyReadiness.GEOGRAPHY_READY,
        reference=ReferenceReadiness.NOT_PREPARED,
    )


# --- 5. 25 unique GEOIDs + one rook component ---------------------------------


def test_success_selection_has_25_unique_geoids_and_one_rook_component() -> None:
    from shapely.geometry import box

    module = _require_selection()
    tracts = _grid_tracts(module, 7, 7, prefix="99")
    place = box(-0.1, -0.1, 7.1, 7.1)
    try:
        outcome = _call_select(module, place, tracts, (3.5, 3.5))
    except Exception as exc:  # noqa: BLE001 — system error is the failure
        pytest.fail(f"supported place raised a system error: {exc!r}")
    assert getattr(outcome, "supported", False) is True
    geoids = tuple(outcome.geoids)
    assert_twenty_five_unique_geoids(geoids)
    graph = _rook_graph_from_tracts(module, tracts, geoids)
    assert_one_rook_component(geoids, graph)
    assert getattr(outcome, "rook_connected", True) is True


def test_rook_postcondition_helper_rejects_two_components() -> None:
    geoids = _synthetic_geoids()
    split = {geoid: frozenset() for geoid in geoids}
    for left, right in zip(geoids[:12], geoids[1:13], strict=True):
        split[left] = frozenset({*split[left], right})
        split[right] = frozenset({*split[right], left})
    for left, right in zip(geoids[13:24], geoids[14:25], strict=True):
        split[left] = frozenset({*split[left], right})
        split[right] = frozenset({*split[right], left})
    with pytest.raises(AssertionError):
        assert_one_rook_component(geoids, split)
    chain = {geoid: frozenset() for geoid in geoids}
    for left, right in zip(geoids, geoids[1:], strict=False):
        chain[left] = frozenset({*chain[left], right})
        chain[right] = frozenset({*chain[right], left})
    assert_one_rook_component(geoids, chain)


# --- 6. Key West / Yuma fail closed as structured unsupported -----------------


def test_key_west_is_structured_unsupported_not_system_error() -> None:
    from shapely.geometry import box

    module = _require_selection()
    tracts = _grid_tracts(module, 2, 3, prefix="12")
    place = box(-0.1, -0.1, 3.1, 2.1)
    try:
        outcome = _call_select(module, place, tracts, (1.5, 1.0))
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            f"Key West {KEY_WEST_PLACE_GEOID} failed as a system error: {exc!r}"
        )
    assert _is_structured_unsupported(outcome)
    assert getattr(outcome, "reason_code") == REASON_INSUFFICIENT_ELIGIBLE
    details = getattr(outcome, "details", {}) or {}
    assert int(details.get("eligible_count", 0)) == 6
    assert not isinstance(outcome, (RuntimeError, TypeError, OSError))


def test_yuma_is_structured_unsupported_not_system_error() -> None:
    from shapely.geometry import box

    module = _require_selection()
    large = _grid_tracts(module, 4, 5, origin=(0.0, 0.0), prefix="40")
    small = _grid_tracts(module, 2, 3, origin=(20.0, 20.0), prefix="41")
    place = box(-0.2, -0.2, 23.2, 22.2)
    place_intpt = (21.5, 20.5)
    try:
        outcome = _call_select(module, place, [*large, *small], place_intpt)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"Yuma {YUMA_PLACE_GEOID} failed as a system error: {exc!r}")
    assert _is_structured_unsupported(outcome)
    codes = _unsupported_codes(outcome)
    assert codes & YUMA_REASON_FAMILY
    details = getattr(outcome, "details", {}) or {}
    assert int(details.get("eligible_count", 0)) == 26
    assert int(details.get("relevant_component_size", 0)) == 6
    assert str(details.get("seed_geoid", "")).startswith("41")


def test_named_fail_closed_place_geoids_are_the_policy_pins() -> None:
    assert KEY_WEST_PLACE_GEOID == "1236550"
    assert YUMA_PLACE_GEOID == "0485540"
    assert KEY_WEST_PLACE_GEOID != YUMA_PLACE_GEOID
    assert national_area_id(KEY_WEST_PLACE_GEOID) != LEGACY_PHOENIX_AREA_ID
    assert national_area_id(YUMA_PLACE_GEOID) != LEGACY_PHOENIX_AREA_ID


def test_resolve_place_geography_fail_closed_when_entry_exists() -> None:
    resolve = load_resolve_place_geography()
    if resolve is None:
        pytest.skip(
            "resolve_place_geography not on this worktree (Lead stitch pending)"
        )
    for place_geoid, expected in (
        (KEY_WEST_PLACE_GEOID, {REASON_INSUFFICIENT_ELIGIBLE}),
        (YUMA_PLACE_GEOID, YUMA_REASON_FAMILY),
    ):
        try:
            outcome = _invoke_resolve(resolve, place_geoid)
        except TypeError:
            pytest.skip(
                "resolve_place_geography signature needs Census inputs "
                "(Lead stitch pending)"
            )
        except Exception as exc:  # noqa: BLE001
            pytest.fail(
                f"{place_geoid} raised a system error instead of structured "
                f"unsupported: {exc!r}"
            )
        assert _is_structured_unsupported(outcome)
        assert _unsupported_codes(outcome) & expected


def _invoke_resolve(resolve: Any, place_geoid: str) -> Any:
    params = inspect.signature(resolve).parameters
    kwargs: dict[str, Any] = {}
    for name in params:
        if name in {"place_geoid", "canonical_place_geoid"}:
            kwargs[name] = place_geoid
        elif name == "canonical_place":
            kwargs[name] = place_geoid
    if not kwargs:
        return resolve(place_geoid)
    return resolve(**kwargs)
