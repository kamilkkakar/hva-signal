"""Map modes: thermal / canopy / income / older housing. No 0/25 choropleths."""

from __future__ import annotations

from app.domain.vulnerability_preparedness.metrics import MetricKind
from app.services.vulnerability_preparedness.public_catalog import (
    MAP_LAYER_KINDS,
    MAP_MODE_KIND,
    MAP_MODES,
    QUANTITY_ONLY_KINDS,
    comparison_layer_allowed,
)
from app.services.vulnerability_preparedness.view_model import map_properties
from tests.unit.test_vulnerability_preparedness_support import (
    ACS_AS_OF,
    ACS_SOURCE,
    ZONE_ID,
    cooling_preparedness,
    zone_context,
)
from app.domain.vulnerability_preparedness.metrics import DirectMetric


def test_map_modes_are_the_four_candidates() -> None:
    assert MAP_MODES == ("THERMAL", "TREE_CANOPY", "INCOME", "OLDER_HOUSING")
    assert MAP_MODE_KIND["THERMAL"] is None
    assert MAP_MODE_KIND["TREE_CANOPY"] is MetricKind.CANOPY_COVER_SHARE
    assert MAP_MODE_KIND["INCOME"] is MetricKind.MEDIAN_HOUSEHOLD_INCOME
    assert MAP_MODE_KIND["OLDER_HOUSING"] is MetricKind.SHARE_PRE_1980_HOUSING


def test_zero_eligible_kinds_cannot_be_map_layers() -> None:
    for kind in QUANTITY_ONLY_KINDS:
        assert comparison_layer_allowed(kind, 0) is False
        assert kind not in MAP_LAYER_KINDS
    assert comparison_layer_allowed(MetricKind.SHARE_AGE_65_PLUS, 6) is False


def test_map_properties_do_not_color_unreliable_income() -> None:
    income = DirectMetric(
        name="median household income",
        value=41000.0,
        unit="usd",
        kind=MetricKind.MEDIAN_HOUSEHOLD_INCOME,
        geography=ZONE_ID,
        source=ACS_SOURCE,
        as_of=ACS_AS_OF,
        moe=20000.0,
    )
    context = zone_context()
    context = context.model_copy(update={"additional_metrics": [income]})
    props = map_properties(
        context,
        cooling_preparedness(status="UNKNOWN"),
        {MetricKind.MEDIAN_HOUSEHOLD_INCOME: 21},
    )
    assert props.median_household_income is None
    assert props.income_comparison_allowed is False
    dumped = props.model_dump()
    assert "share_under_5" not in dumped
    assert "poverty_rate" not in dumped
    assert "hva_score" not in dumped
