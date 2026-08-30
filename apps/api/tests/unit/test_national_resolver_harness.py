"""National resolver stress/failure harness — I7 / AGENT E.

CI-safe: synthetic graphs, catalog, ALG1 pin, and on-disk oracle.
Live TIGER downloads are not required. FortyGuard is not imported.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# Resolve from this test file so worktree fixtures are never confused with
# f:\cursor\hackathon main (and never the nested national_resolver/national_resolver path).
_TEST_FILE = Path(__file__).resolve()
FIXTURE_DIR = _TEST_FILE.parents[1] / "fixtures" / "national_resolver"
SCRIPT_PATH = _TEST_FILE.parents[4] / "scripts" / "national_resolver_panel.py"
TARGET_TRACTS = 25
ALG1_ID = "ALG1_GREEDY_LEX_PLACE_INTPT_V1"
SUCCESS_PLACE_GEOIDS = {
    "1714000",  # Chicago
    "3651000",  # New York
    "0644000",  # Los Angeles
    "4835000",  # Houston
    "1245000",  # Miami
    "0820000",  # Denver
    "4260000",  # Philadelphia
    "0477000",  # Tucson
}
KEY_WEST = "1236550"
YUMA = "0485540"


def _load_panel():
    spec = importlib.util.spec_from_file_location(
        "national_resolver_panel", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json(name: str) -> dict:
    path = FIXTURE_DIR / name
    assert path.is_file(), f"missing fixture {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixture_dir_is_not_nested() -> None:
    assert FIXTURE_DIR.name == "national_resolver"
    assert FIXTURE_DIR.parent.name == "fixtures"
    assert not (FIXTURE_DIR / "national_resolver").exists()
    assert (FIXTURE_DIR / "substrate.json").is_file()
    assert (FIXTURE_DIR / "panel_catalog.json").is_file()
    assert (FIXTURE_DIR / "synthetic" / "connected_success_graph.json").is_file()
    assert (FIXTURE_DIR / "synthetic" / "insufficient_eligible_graph.json").is_file()
    assert (FIXTURE_DIR / "synthetic" / "insufficient_component_graph.json").is_file()


def test_harness_script_exists_and_avoids_fortyguard() -> None:
    assert SCRIPT_PATH.is_file()
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "from app.integrations.fortyguard" not in text
    assert "import fortyguard" not in text.lower()
    assert "FortyGuardAdapter" not in text
    assert "q_A" not in text
    # Live TIGER CLI may mention Decision 8 only as a thing it does not import.


def test_harness_does_not_require_live_tiger_download() -> None:
    panel = _load_panel()
    assert hasattr(panel, "classify_graph_fixture")
    assert hasattr(panel, "disconnected_island_polygons")
    # These tests never call download / scan / live measure.
    assert not hasattr(panel, "LIVE_TIGER_REQUIRED_FOR_UNIT_TESTS")


def test_substrate_matches_alg1_frozen_candidate_pin() -> None:
    panel = _load_panel()
    substrate = panel.FROZEN_CANDIDATE_SUBSTRATE
    assert substrate["status"] == "FROZEN_CANDIDATE"
    assert substrate["algorithm"] == ALG1_ID
    assert substrate["policy_id"] == "NATIONAL_PLACE_GEOGRAPHY_V1"
    assert substrate["slug"] == "national-place-geography-v1"
    assert substrate["census_vintage"] == "2025"
    assert substrate["projection_conus"] == "EPSG:5070"
    assert substrate["published_crs"] == "EPSG:4269"
    assert substrate["rook_min_length_m"] == 0.001
    assert "1e-3" in substrate["rook"]
    assert "INTPT" in substrate["eligibility"]
    assert "place INTPT" in substrate["seed"]
    assert "greedy_lex" in substrate["growth"]
    assert substrate["outside_place_expansion"] is False
    assert substrate["phoenix_legacy_reproduction_required"] is False
    assert substrate["target_tracts"] == TARGET_TRACTS
    assert substrate["not_e_medoid_stub"] is True
    assert panel.ROOK_MIN_LENGTH_M == 1e-3
    on_disk = _json("substrate.json")
    assert on_disk["status"] == "FROZEN_CANDIDATE"
    assert on_disk["algorithm"] == ALG1_ID
    assert on_disk["rook_min_length_m"] == 0.001
    assert "place INTPT" in on_disk["seed"]
    assert "greedy_lex" in on_disk["growth"]
    assert on_disk["projection_conus"] == "EPSG:5070"


def test_catalog_lists_key_west_and_yuma_as_should_fail() -> None:
    catalog = _json("panel_catalog.json")
    should_fail = catalog["should_fail"]
    geoids = {row["place_geoid"] for row in should_fail}
    assert KEY_WEST in geoids
    assert YUMA in geoids
    key_west = next(row for row in should_fail if row["place_geoid"] == KEY_WEST)
    yuma = next(row for row in should_fail if row["place_geoid"] == YUMA)
    assert key_west["expected_reason"] == "INSUFFICIENT_ELIGIBLE_TRACTS"
    assert yuma["expected_reason"] == "INSUFFICIENT_CONNECTED_TRACTS"
    assert yuma.get("alg1_seed_component") == 6
    assert any(row["place_geoid"] == KEY_WEST for row in catalog["fail_lt25"])
    assert any(row["place_geoid"] == YUMA for row in catalog["fail2_found"])


def test_catalog_has_diverse_success_and_required_real_fail() -> None:
    catalog = _json("panel_catalog.json")
    success = catalog["success"]
    assert len(success) >= 7
    roles = {row["role"] for row in success}
    assert "dense_grid" in roles
    assert "coastal" in roles
    assert any("sprawl" in role or "western" in role for role in roles)
    assert any("irregular" in role or "river" in role for role in roles)
    geoids = {row["place_geoid"] for row in success}
    assert SUCCESS_PLACE_GEOIDS <= geoids
    fail = catalog["fail_lt25"]
    assert fail
    assert any(row["place_geoid"] == KEY_WEST for row in fail)
    assert all(len(row["place_geoid"]) == 7 and row["place_geoid"].isdigit() for row in fail)
    assert catalog["success_only_is_incomplete"] is True
    assert catalog["required_real_lt25"] is True
    assert "0455000" not in geoids


def test_synthetic_insufficient_connected_component() -> None:
    panel = _load_panel()
    payload = _json("synthetic/insufficient_component_graph.json")
    assert payload["synthetic"] is True
    assert payload["not_a_census_place"] is True
    assert payload["do_not_register_as_production_place"] is True
    assert payload["label"] == "SYNTHETIC_UNIT_TEST_GRAPH"
    result = panel.classify_graph_fixture(payload)
    assert result["eligible_count"] == 30
    assert result["component_sizes"] == [12, 10, 8]
    assert result["largest_component"] == 12
    assert result["status"] == panel.STATUS_UNSUPPORTED
    assert result["reason"] == panel.REASON_INSUFFICIENT_CONNECTED


def test_synthetic_insufficient_eligible() -> None:
    panel = _load_panel()
    payload = _json("synthetic/insufficient_eligible_graph.json")
    assert payload["synthetic"] is True
    assert payload["not_a_census_place"] is True
    result = panel.classify_graph_fixture(payload)
    assert result["eligible_count"] == 20
    assert result["largest_component"] == 20
    assert result["status"] == panel.STATUS_UNSUPPORTED
    assert result["reason"] == panel.REASON_INSUFFICIENT_ELIGIBLE


def test_synthetic_success_graph_supported_on_count_and_component() -> None:
    panel = _load_panel()
    payload = _json("synthetic/connected_success_graph.json")
    assert payload["synthetic"] is True
    assert payload["not_a_census_place"] is True
    result = panel.classify_graph_fixture(payload)
    assert result["eligible_count"] == 40
    assert result["largest_component"] == 40
    assert result["status"] == panel.STATUS_SUPPORTED
    assert result["reason"] is None


def test_rook_corner_touch_is_not_adjacent() -> None:
    panel = _load_panel()
    _squares, diagonal_rook = panel.corner_touch_squares()
    assert diagonal_rook is False
    _edge, edge_rook = panel.edge_adjacent_squares()
    assert edge_rook is True


def test_synthetic_island_polygons_largest_component_below_25() -> None:
    panel = _load_panel()
    geoms = panel.disconnected_island_polygons()
    assert len(geoms) == 27
    neighbors = panel.build_rook_neighbors(geoms)
    sizes = panel.component_sizes(neighbors)
    assert sizes == [9, 9, 9]
    status, reason = panel.classify_support(
        eligible_count=len(geoms),
        largest_component=sizes[0],
        seed_component=sizes[0],
        scope_ok=True,
        invalid_id=False,
        unknown=False,
    )
    assert status == panel.STATUS_UNSUPPORTED
    assert reason == panel.REASON_INSUFFICIENT_CONNECTED


def test_determinism_protocol_on_synthetic_islands() -> None:
    panel = _load_panel()
    geoms = panel.disconnected_island_polygons()
    orders = [list(range(27)), list(range(26, -1, -1))]
    shuffled = list(range(27))
    rng = __import__("random").Random(7)
    rng.shuffle(shuffled)
    orders.append(shuffled)
    signatures = []
    for order in orders:
        perm = [geoms[i] for i in order]
        sizes = tuple(panel.component_sizes(panel.build_rook_neighbors(perm)))
        signatures.append(sizes)
    assert len(set(signatures)) == 1
    assert signatures[0] == (9, 9, 9)


def test_invalid_and_unknown_place_ids() -> None:
    panel = _load_panel()
    assert panel.validate_place_geoid("00XXXXX") == panel.REASON_INVALID_PLACE_ID
    assert panel.validate_place_geoid("0499999") is None
    assert panel.validate_place_geoid(KEY_WEST) is None
    identity = panel.identity_failures()
    assert identity[0]["pass"] is True
    assert identity[0]["expected_reason"] == panel.REASON_INVALID_PLACE_ID


def test_fail2_search_fixture_is_honest_if_not_found() -> None:
    search = _json("fail_case2_search.json")
    assert "strategy" in search
    assert "watch_list" in search
    assert search["watch_list"]
    if search.get("real_connected_lt25_found") is False:
        assert search["n_candidates_rook_evaluated"] >= 1
        assert search.get("found") == []
    if search.get("real_connected_lt25_found") is True:
        assert search["found"]
        assert all(int(row["eligible_count"]) >= 25 for row in search["found"])
        assert all(int(row["largest_component"]) < 25 for row in search["found"])
        assert any(row["place_geoid"] == YUMA for row in search["found"])
    if search.get("status") == "PENDING_LIVE_SCAN":
        assert search["real_connected_lt25_found"] is None


def test_live_measurements_when_present_are_complete() -> None:
    payload = _json("measurements.json")
    if not payload.get("live_measured"):
        return
    assert payload.get("not_alg1_oracle") is True
    assert payload.get("algorithm_id") == "E_PANEL_MEDOID_STUB_NOT_ALG1"
    rows = payload["measurements"]
    success = [r for r in rows if r.get("panel") == "success"]
    fails = [r for r in rows if r.get("panel") == "fail_lt25"]
    assert len(success) >= 5
    assert fails
    real_lt25 = [
        r
        for r in fails
        if r.get("eligible_count") is not None
        and r["eligible_count"] < TARGET_TRACTS
        and r.get("place_geoid", "").isdigit()
    ]
    assert real_lt25, "live panel must include a real <25 eligible place"
    key_west = next((r for r in fails if r.get("place_geoid") == KEY_WEST), None)
    if key_west and key_west.get("measured"):
        assert key_west["eligible_count"] < TARGET_TRACTS
        assert key_west["reason"] == "INSUFFICIENT_ELIGIBLE_TRACTS"
    for row in success:
        if not row.get("measured"):
            continue
        assert row["eligible_count"] >= TARGET_TRACTS
        assert row["largest_component"] >= TARGET_TRACTS
        if row.get("selected_count") == TARGET_TRACTS:
            assert row.get("rook_connected_selected") is True
            assert row.get("determinism", {}).get("deterministic") is True


def test_panel_is_incomplete_without_failures() -> None:
    catalog = _json("panel_catalog.json")
    assert catalog["fail_lt25"], "a success-only panel is incomplete"
    assert catalog["should_fail"], "should-fail headlines are required"
    payload = _json("measurements.json")
    if payload.get("live_measured"):
        fail_reasons = {
            r.get("reason")
            for r in payload["measurements"]
            if r.get("status") == "UNSUPPORTED"
        }
        assert "INSUFFICIENT_ELIGIBLE_TRACTS" in fail_reasons


def test_alg1_oracle_is_labeled_alg1_not_e_medoid() -> None:
    oracle = _json("alg1_oracle.json")
    assert oracle["algorithm_id"] == ALG1_ID
    assert oracle["not_e_medoid_sets"] is True
    assert oracle["policy_id"] == "NATIONAL_PLACE_GEOGRAPHY_V1"
    assert oracle["rook_min_length_m"] == 0.001
    assert "place INTPT" in oracle["seed"]
    assert "greedy_lex" in oracle["growth"]
    assert set(oracle["success"]) == SUCCESS_PLACE_GEOIDS
    chicago = oracle["success"]["1714000"]
    assert chicago["seed_geoid"] == "17031841300"
    assert chicago["seed_rule"] == "place_intpt_container"
    assert chicago["selected_growth_order"][0] == "17031841300"
    assert len(chicago["selected_growth_order"]) == TARGET_TRACTS
    assert len(chicago["geoids_sorted"]) == TARGET_TRACTS
    # E medoid seed for Chicago was 17031282800 — must not appear as ALG1 seed.
    assert chicago["seed_geoid"] != "17031282800"
    for geoid, row in oracle["success"].items():
        assert len(row["selected_growth_order"]) == TARGET_TRACTS
        assert len(set(row["selected_growth_order"])) == TARGET_TRACTS
        assert row["selected_growth_order"][0] == row["seed_geoid"]
        assert row["supported"] is True
        assert row["rook_connected_selected"] is True
        assert row["place_geoid"] == geoid
    must_fail = oracle["must_fail"]
    assert KEY_WEST in must_fail
    assert YUMA in must_fail
    assert must_fail[KEY_WEST]["reason_code"] == "INSUFFICIENT_ELIGIBLE_TRACTS"
    assert must_fail[KEY_WEST]["eligible_count"] == 6
    assert must_fail[YUMA]["eligible_count"] == 26
    assert must_fail[YUMA]["component_sizes"] == [20, 6]
    assert must_fail[YUMA]["seed_component_size"] == 6
    assert must_fail[YUMA]["connected_family"] == "INSUFFICIENT_CONNECTED_TRACTS"
    assert oracle["phoenix_retrospective"]["do_not_score"] is True
    assert oracle["phoenix_retrospective"]["overlap_with_phoenix_demo_frozen_25"] == 0
