"""LON-P: matched-window TCM against the frozen FortyGuard panel.

Uses real mean_tcm_c. Does not invent temperatures. Does not call FortyGuard.
Does not import Signal A / q_A construction.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app.core.phoenix_v1_area_config import CANONICAL_REFERENCE_RELATIVE_PATH, hackathon_root
from app.domain.matched_nighttime_window import (
    WINDOW_LABEL,
    api_contract,
    assemble_zone_packet,
    load_fortyguard_nighttime_panel,
    matched_date_comparison,
    matched_window_summary,
    selected_zone_story,
    year_over_year_zone_change,
)
from app.domain.matched_nighttime_window.analysis_geography_change_context import (
    analysis_geography_change_context,
)
from app.domain.matched_nighttime_window.claims import (
    ForbiddenClaimError,
    assert_claim_allowed,
    claim_violations,
)
from app.domain.matched_nighttime_window.panel import NighttimePanel, NighttimeTcmObservation
from app.domain.matched_nighttime_window.present import yoy_change_map_layer
from app.services.matched_nighttime_window import assemble_selected_zone

OBS_PATH = hackathon_root() / CANONICAL_REFERENCE_RELATIVE_PATH
SEED = "04013107401"
PACKAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "domain"
    / "matched_nighttime_window"
)
FORBIDDEN_IMPORTS = {
    "app.services.temporal_anomaly",
    "app.services.phoenix_v1_thermal",
    "app.services.year_over_year",
}


@pytest.fixture(scope="module")
def raw_rows() -> list[dict]:
    assert OBS_PATH.is_file(), f"missing FortyGuard panel {OBS_PATH}"
    return [
        json.loads(line)
        for line in OBS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def panel() -> NighttimePanel:
    return load_fortyguard_nighttime_panel(OBS_PATH)


def _independent_mean(raw_rows: list[dict], geoid: str, year: int) -> float:
    values = [
        float(row["mean_tcm_c"])
        for row in raw_rows
        if str(row["geoid"]).zfill(11) == geoid and int(row["year"]) == year
    ]
    assert values, f"no real TCM rows for {geoid} {year}"
    return sum(values) / len(values)


def test_panel_has_real_tcm_not_q_a(raw_rows: list[dict], panel: NighttimePanel) -> None:
    assert len(raw_rows) == 2325
    assert set(raw_rows[0]) == {
        "contributing_tiles",
        "date",
        "geoid",
        "local_time",
        "mean_tcm_c",
        "usable",
        "year",
    }
    assert all(row.get("mean_tcm_c") is not None for row in raw_rows)
    assert all(row["local_time"] == "03:00" for row in raw_rows)
    assert all(row["usable"] is True for row in raw_rows)
    assert panel.n_rows == 2325
    assert panel.n_timestamps == 93
    assert panel.n_zones == 25
    assert panel.years == (2022, 2023, 2024)
    assert panel.has_q_a_field is False
    assert panel.has_iso_timestamp_field is False
    assert panel.has_row_provenance_field is False
    assert panel.temperature_quantity == "tcm_zone_mean"
    assert panel.window_label == WINDOW_LABEL


def test_seed_year_means_match_independent_panel_average(
    raw_rows: list[dict], panel: NighttimePanel
) -> None:
    for year in (2022, 2023, 2024):
        summary = matched_window_summary(panel, SEED, year)
        expected = _independent_mean(raw_rows, SEED, year)
        assert summary.n_valid_nights == 31
        assert summary.n_expected_nights == 31
        assert summary.coverage_supported is True
        assert summary.mean_tcm_c == pytest.approx(expected)
        assert summary.temperature_quantity == "tcm_zone_mean"
        assert summary.min_tcm_c is not None
        assert summary.max_tcm_c is not None
        assert summary.stdev_tcm_c is not None


def test_all_zones_have_complete_three_year_coverage(panel: NighttimePanel) -> None:
    for geoid in panel.zone_ids():
        for year in (2022, 2023, 2024):
            summary = matched_window_summary(panel, geoid, year)
            assert summary.n_valid_nights == 31
            assert summary.coverage_supported is True
            assert summary.mean_tcm_c is not None


def test_year_over_year_uses_tcm_degrees_not_index(
    raw_rows: list[dict], panel: NighttimePanel
) -> None:
    change = year_over_year_zone_change(panel, SEED, 2022, 2024)
    expected = _independent_mean(raw_rows, SEED, 2024) - _independent_mean(
        raw_rows, SEED, 2022
    )
    assert change.delta_c == pytest.approx(expected)
    assert change.delta_c == pytest.approx(1.535640952620966, abs=1e-6)
    assert change.public_sentence is not None
    assert "1.5°C warmer" in change.public_sentence
    assert WINDOW_LABEL in change.public_sentence
    assert "q_A" not in change.public_sentence
    assert "climate trend" not in change.public_sentence.lower() or "not a climate trend" in change.public_sentence.lower()


def test_every_zone_mean_warmer_2024_than_2022(panel: NighttimePanel) -> None:
    deltas = []
    for geoid in panel.zone_ids():
        change = year_over_year_zone_change(panel, geoid, 2022, 2024)
        assert change.delta_c is not None
        assert change.delta_c > 0
        deltas.append(change.delta_c)
    assert min(deltas) == pytest.approx(1.4649, abs=1e-3)
    assert max(deltas) == pytest.approx(1.5566, abs=1e-3)


def test_matched_date_persistence_is_a_count_not_an_index(panel: NighttimePanel) -> None:
    pair = matched_date_comparison(panel, SEED, 2022, 2024)
    assert pair.n_matched == 31
    assert pair.n_warmer == 22
    assert pair.n_cooler == 9
    assert pair.n_warmer + pair.n_cooler + pair.n_equal == 31
    assert pair.persistence_sentence is not None
    assert "22 of 31" in pair.persistence_sentence
    assert "persistence index" in pair.persistence_sentence.lower()
    assert pair.window_label == WINDOW_LABEL


def test_2024_vs_2023_mean_and_night_count_can_disagree(panel: NighttimePanel) -> None:
    yoy = year_over_year_zone_change(panel, "04013106400", 2023, 2024)
    pair = matched_date_comparison(panel, "04013106400", 2023, 2024)
    assert yoy.delta_c is not None and yoy.delta_c > 0
    assert pair.n_cooler > pair.n_warmer
    assert pair.median_delta_c is not None and pair.median_delta_c < 0


def test_geography_median_context_is_not_an_effect(panel: NighttimePanel) -> None:
    context = analysis_geography_change_context(panel, SEED, 2022, 2024)
    assert context.n_zones == 25
    assert context.n_zones_with_delta == 25
    assert context.geography_median_delta_c == pytest.approx(1.5316, abs=1e-3)
    assert context.public_sentence is not None
    assert "not an intervention effect" in context.public_sentence.lower()
    assert context.zone_minus_median_c is not None
    assert abs(context.zone_minus_median_c) < 0.05


def test_selected_zone_story_answers_the_contract(panel: NighttimePanel) -> None:
    story = selected_zone_story(panel, SEED)
    blob = " ".join(story.sentences).lower()
    assert story.window_label == WINDOW_LABEL
    assert "03:00" in story.exact_period
    assert "america/phoenix" in story.exact_period.lower()
    assert "1.5°c" in story.by_how_much.lower()
    assert "25-area" in story.geography_context or "25-area" in blob
    assert "climate trend" in story.direction.lower()
    for token in ("heatdose", "afterheat", "summer trend", "annual trend", "jja"):
        assert token not in blob


def test_charts_and_map_use_tcm_not_q_a(panel: NighttimePanel) -> None:
    packet = assemble_zone_packet(panel, SEED)
    chart_ids = {chart.chart_id for chart in packet.charts}
    assert chart_ids == {
        "three_year_nighttime_line",
        "matched_date_distributions",
        "selected_zone_matched_date_strip",
        "analysis_geography_change_distribution",
    }
    assert all(chart.quantity == "tcm_zone_mean" for chart in packet.charts)
    line = next(chart for chart in packet.charts if chart.chart_id == "three_year_nighttime_line")
    years = [point["year"] for point in line.payload["points"]]
    assert years == [2022, 2023, 2024]
    assert all(point["mean_tcm_c"] is not None for point in line.payload["points"])
    layer = yoy_change_map_layer(panel)
    assert len(layer.features) == 25
    assert layer.quantity == "tcm_zone_mean"
    assert "intervention effect" in layer.legend_note.lower()
    assert packet.not_signal_a is True
    assert packet.descriptive_three_year_change_c_per_year == pytest.approx(
        packet.year_over_year[-1].delta_c / 2.0  # 2022→2024 pair is last
    )
    assert packet.intervention.daytime_shade_not_evaluable_from_0300_alone is True
    assert packet.intervention.not_an_intervention_effect is True


def test_service_assembler_matches_domain(panel: NighttimePanel) -> None:
    packet = assemble_selected_zone(SEED, path=OBS_PATH)
    assert packet.geoid == SEED
    assert packet.year_summaries[0].mean_tcm_c == pytest.approx(
        matched_window_summary(panel, SEED, 2022).mean_tcm_c
    )


def test_api_contract_is_unpublished_and_not_signal_a() -> None:
    contract = api_contract()
    assert contract["unpublished"] is True
    assert contract["not_signal_a"] is True
    assert contract["window_label"] == WINDOW_LABEL
    assert "matched_window_summary" in contract["operations"]
    assert "year_over_year_zone_change" in contract["operations"]
    assert "matched_date_comparison" in contract["operations"]
    assert "analysis_geography_change_context" in contract["operations"]


def test_incomplete_coverage_uses_real_rows_only(raw_rows: list[dict]) -> None:
    subset = [
        row
        for row in raw_rows
        if str(row["geoid"]).zfill(11) == SEED and int(row["year"]) == 2022
    ][:5]
    assert len(subset) == 5
    observations = tuple(
        NighttimeTcmObservation(
            date=str(row["date"]),
            year=int(row["year"]),
            local_time=str(row["local_time"]),
            geoid=str(row["geoid"]).zfill(11),
            mean_tcm_c=float(row["mean_tcm_c"]),
            contributing_tiles=int(row["contributing_tiles"]),
            usable=bool(row["usable"]),
            month_day=str(row["date"])[5:],
        )
        for row in subset
    )
    thin = NighttimePanel(
        observations=observations,
        source_path="subset-of-real-panel",
        source_sha256="0" * 64,
        n_rows=5,
        n_timestamps=5,
        n_zones=1,
        years=(2022,),
        hour_local="03:00",
        timezone="America/Phoenix",
        window_label=WINDOW_LABEL,
        window_dates="30 Jun–30 Jul",
        temperature_quantity="tcm_zone_mean",
        source_family="fortyguard",
        source_mode="replay",
        zone_geometry_version="test",
        aggregation_spec_version="test",
        has_iso_timestamp_field=False,
        has_row_provenance_field=False,
        has_q_a_field=False,
        raw_fields=tuple(sorted(subset[0])),
    )
    summary = matched_window_summary(thin, SEED, 2022)
    assert summary.n_valid_nights == 5
    assert summary.coverage_supported is False
    expected = sum(float(row["mean_tcm_c"]) for row in subset) / 5
    assert summary.mean_tcm_c == pytest.approx(expected)
    change = year_over_year_zone_change(thin, SEED, 2022, 2024)
    assert change.delta_c is None
    assert change.coverage_supported is False


def test_forbidden_claim_tokens_are_rejected() -> None:
    with pytest.raises(ForbiddenClaimError):
        assert_claim_allowed("This is a climate trend.")
    assert claim_violations("This is not a climate trend.") == []
    assert_claim_allowed("This is not a climate trend.")


def test_package_does_not_import_signal_a() -> None:
    for path in PACKAGE_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in FORBIDDEN_IMPORTS
                assert "temporal_anomaly" not in node.module
                assert "phoenix_v1_thermal" not in node.module
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                assert not any("temporal_anomaly" in name for name in names)
        text = path.read_text(encoding="utf-8")
        assert "compute_q_a" not in text
