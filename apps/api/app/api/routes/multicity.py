"""Server-owned multi-city catalog and comparison endpoints."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.area_registry import PHOENIX_DEMO_AREA_ID, resolve_area_geography
from app.domain.multicity.capabilities import negotiate_capabilities
from app.domain.multicity.catalog import get_city, list_cities
from app.domain.multicity.city_config import CityConfig, CityId
from app.domain.observed_thermal_instants.assemble import load_tracked_snapshots
from app.services.vulnerability_preparedness.cache import (
    ContextCacheError,
    load_context_bundle_cached,
)

router = APIRouter()

_COMPARISON_DATE = "2024-07-08"
_COMPARISON_TIME = "15:00"
_COMPARISON_POLICY = "same_local_date_time"
_CROSS_CITY_CANOPY_MISSING = (
    "Cross-city canopy is not packaged yet; Phoenix local canopy is intentionally "
    "not reused for cross-city comparison."
)
_UNPACKAGED_CITY_REASON = (
    "Comparable multi-city analysis tracts are not packaged for this city yet."
)


class CapabilityView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city_id: CityId
    capabilities: dict[str, str]


class ComparisonClock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: str
    local_time: str
    policy: str


class MetricAxis(StrEnum):
    TEMPERATURE_C = "temperature_c"
    MEDIAN_HOUSEHOLD_INCOME = "median_household_income"
    POPULATION = "population"
    TREE_CANOPY_PCT = "tree_canopy_pct"


class CrossCityMetricRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city_id: CityId
    zone_id: str | None = None
    geoid: str | None = None
    label: str = Field(min_length=1)
    temperature_c: float | None = None
    median_household_income: float | None = None
    population: int | None = None
    tree_canopy_pct: float | None = None
    coverage_flags: dict[str, bool]
    missing_reasons: dict[str, str]
    comparison_clock: ComparisonClock


class CrossCityAxes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: MetricAxis
    y: MetricAxis
    size: MetricAxis
    fill: MetricAxis


class CrossCitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    included_count: int = Field(ge=0)
    omitted_axis_count: int = Field(ge=0)
    missing_fill_count: int = Field(ge=0)


class CrossCityMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    axes: CrossCityAxes
    rows: list[CrossCityMetricRow]
    summary: CrossCitySummary


def _city_or_404(city_id: str) -> CityConfig:
    try:
        return get_city(city_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _comparison_clock() -> ComparisonClock:
    return ComparisonClock(
        local_date=_COMPARISON_DATE,
        local_time=_COMPARISON_TIME,
        policy=_COMPARISON_POLICY,
    )


def _phoenix_temperature_by_zone() -> dict[str, float | None]:
    snapshot = load_tracked_snapshots()["15:00"]
    return {
        str(row["zone_id"]).zfill(11): (
            float(row["mean_temperature_c"])
            if row.get("mean_temperature_c") is not None
            else None
        )
        for row in snapshot["zones"]
    }


def _acs_geo_id(geoid: str) -> str:
    return f"1400000US{geoid}"


def _bundle_acs_value(
    bundle: dict[str, Any] | None,
    *,
    table: str,
    geoid: str,
    field: str,
) -> float | None:
    if bundle is None:
        return None
    rows = (((bundle.get("acs") or {}).get(table) or {}).get("rows") or {})
    row = rows.get(_acs_geo_id(geoid))
    if not isinstance(row, dict):
        return None
    value = row.get(field)
    if value is None:
        return None
    return float(value)


def _phoenix_rows() -> list[CrossCityMetricRow]:
    geography = resolve_area_geography(PHOENIX_DEMO_AREA_ID)
    geometry = json.loads(geography.geometry_body.decode("utf-8"))
    try:
        bundle = load_context_bundle_cached()
    except ContextCacheError:
        bundle = None
    temperatures = _phoenix_temperature_by_zone()
    rows: list[CrossCityMetricRow] = []
    for feature in geometry["features"]:
        props = feature["properties"]
        geoid = str(props["GEOID"]).zfill(11)
        income = _bundle_acs_value(bundle, table="B19013", geoid=geoid, field="B19013_E001")
        population_value = _bundle_acs_value(
            bundle,
            table="B01001",
            geoid=geoid,
            field="B01001_E001",
        )
        missing_reasons: dict[str, str] = {
            "tree_canopy_pct": _CROSS_CITY_CANOPY_MISSING,
        }
        if geoid not in temperatures or temperatures[geoid] is None:
            missing_reasons["temperature_c"] = (
                "Phoenix 2024-07-08 15:00 tracked snapshot did not contain this tract."
            )
        if income is None:
            missing_reasons["median_household_income"] = (
                "Phoenix ACS context is missing or this tract has no income row in the "
                "cached context bundle."
            )
        if population_value is None:
            missing_reasons["population"] = (
                "Phoenix ACS context is missing or this tract has no population row in the "
                "cached context bundle."
            )
        rows.append(
            CrossCityMetricRow(
                city_id=CityId.PHOENIX,
                zone_id=geoid,
                geoid=geoid,
                label=str(props.get("NAMELSAD") or props.get("NAME") or geoid),
                temperature_c=temperatures.get(geoid),
                median_household_income=income,
                population=(
                    int(round(population_value))
                    if population_value is not None
                    else None
                ),
                tree_canopy_pct=None,
                coverage_flags={
                    "temperature_c": temperatures.get(geoid) is not None,
                    "median_household_income": income is not None,
                    "population": population_value is not None,
                    "tree_canopy_pct": False,
                },
                missing_reasons=missing_reasons,
                comparison_clock=_comparison_clock(),
            )
        )
    return rows


def _placeholder_rows() -> list[CrossCityMetricRow]:
    rows: list[CrossCityMetricRow] = []
    for city in list_cities():
        if city.city_id == CityId.PHOENIX:
            continue
        rows.append(
            CrossCityMetricRow(
                city_id=city.city_id,
                zone_id=None,
                geoid=None,
                label=city.display_name,
                coverage_flags={
                    "temperature_c": False,
                    "median_household_income": False,
                    "population": False,
                    "tree_canopy_pct": False,
                },
                missing_reasons={
                    "temperature_c": _UNPACKAGED_CITY_REASON,
                    "median_household_income": _UNPACKAGED_CITY_REASON,
                    "population": _UNPACKAGED_CITY_REASON,
                    "tree_canopy_pct": _UNPACKAGED_CITY_REASON,
                },
                comparison_clock=_comparison_clock(),
            )
        )
    return rows


def _axis_value(row: CrossCityMetricRow, axis: MetricAxis) -> float | int | None:
    return getattr(row, axis.value)


def _build_metrics_response(*, axes: CrossCityAxes) -> CrossCityMetricsResponse:
    rows = _phoenix_rows() + _placeholder_rows()
    included_count = sum(
        1
        for row in rows
        if _axis_value(row, axes.x) is not None
        and _axis_value(row, axes.y) is not None
        and _axis_value(row, axes.size) is not None
    )
    missing_fill_count = sum(
        1
        for row in rows
        if _axis_value(row, axes.x) is not None
        and _axis_value(row, axes.y) is not None
        and _axis_value(row, axes.size) is not None
        and _axis_value(row, axes.fill) is None
    )
    return CrossCityMetricsResponse(
        axes=axes,
        rows=rows,
        summary=CrossCitySummary(
            included_count=included_count,
            omitted_axis_count=len(rows) - included_count,
            missing_fill_count=missing_fill_count,
        ),
    )


@router.get("/cities")
def get_cities() -> dict[str, list[dict[str, Any]]]:
    return {"cities": [city.model_dump(mode="json") for city in list_cities()]}


@router.get("/cities/{city_id}")
def get_city_detail(city_id: str) -> dict[str, Any]:
    return _city_or_404(city_id).model_dump(mode="json")


@router.get("/cities/{city_id}/capabilities")
def get_city_capabilities(city_id: str) -> CapabilityView:
    city = _city_or_404(city_id)
    capabilities = {
        key.value if hasattr(key, "value") else str(key): value.value
        if hasattr(value, "value")
        else str(value)
        for key, value in negotiate_capabilities(city.city_id).items()
    }
    return CapabilityView(city_id=city.city_id, capabilities=capabilities)


@router.get("/cross-city/metrics")
def get_cross_city_metrics() -> CrossCityMetricsResponse:
    return _build_metrics_response(
        axes=CrossCityAxes(
            x=MetricAxis.MEDIAN_HOUSEHOLD_INCOME,
            y=MetricAxis.TEMPERATURE_C,
            size=MetricAxis.POPULATION,
            fill=MetricAxis.TREE_CANOPY_PCT,
        )
    )


@router.get("/cross-city/query")
def query_cross_city_metrics(
    x: MetricAxis = Query(...),
    y: MetricAxis = Query(...),
    size: MetricAxis = Query(...),
    fill: MetricAxis = Query(...),
) -> CrossCityMetricsResponse:
    return _build_metrics_response(axes=CrossCityAxes(x=x, y=y, size=size, fill=fill))

