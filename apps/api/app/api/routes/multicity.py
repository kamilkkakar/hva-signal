"""Server-owned multi-city catalog and comparison endpoints."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.domain.multicity.capabilities import negotiate_capabilities
from app.domain.multicity.catalog import get_city, list_cities
from app.domain.multicity.city_config import CityConfig, CityId
from app.domain.multicity.cross_city_acs import acs_metric, acs_share_pct
from app.domain.multicity.cross_city_canopy import canopy_pct_for
from app.domain.multicity.cross_city_thermal import thermal_mean_c_for
from app.domain.multicity.observation_clock import (
    CROSS_CITY_OBSERVATION_V1,
    resolve_city_observation_clock,
)

router = APIRouter()

_COMPARISON_DATE = "2024-07-08"
_COMPARISON_TIME = "15:00"
_COMPARISON_POLICY = CROSS_CITY_OBSERVATION_V1
_MISSING_THERMAL = (
    "Selected-time temperature is not published for this cross-city geography yet; "
    "synthetic temperatures are refused."
)
_CITY_ID_TO_DIR = {
    CityId.PHOENIX: "phoenix",
    CityId.LAS_VEGAS: "las_vegas",
    CityId.TUCSON: "tucson",
    CityId.LOS_ANGELES: "los_angeles",
}


class CapabilityView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city_id: CityId
    capabilities: dict[str, str]


class ComparisonClock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: str
    local_time: str
    policy: str
    timezone: str | None = None
    utc_timestamp: str | None = None
    dst_active: bool | None = None


class MetricAxis(StrEnum):
    TEMPERATURE_C = "temperature_c"
    MEDIAN_HOUSEHOLD_INCOME = "median_household_income"
    POPULATION = "population"
    TREE_CANOPY_PCT = "tree_canopy_pct"
    OLDER_HOUSING = "homes_built_before_1980"


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
    homes_built_before_1980: float | None = None
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


def _repo_root() -> Path:
    # apps/api/app/api/routes/multicity.py → repo root
    return Path(__file__).resolve().parents[5]


def _city_or_404(city_id: str) -> CityConfig:
    try:
        return get_city(city_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _tract_display_name(geoid: str) -> str:
    """Census tract public label from GEOID (AREA_IDENTITY_V1 fallback level 3)."""
    padded = str(geoid).zfill(11)
    tractce = padded[-6:]
    suffix = tractce[-2:]
    prefix = tractce[:-2].lstrip("0") or "0"
    return f"Census Tract {prefix}.{suffix}"


def _comparison_clock(city_id: CityId) -> ComparisonClock:
    clock = resolve_city_observation_clock(_CITY_ID_TO_DIR[city_id])
    return ComparisonClock(
        local_date=_COMPARISON_DATE,
        local_time=_COMPARISON_TIME,
        policy=_COMPARISON_POLICY,
        timezone=clock.timezone,
        utc_timestamp=clock.utc_timestamp,
        dst_active=clock.dst_active,
    )


def _city_rows(city: CityConfig) -> list[CrossCityMetricRow]:
    city_dir = _CITY_ID_TO_DIR[city.city_id]
    geometry_path = (
        _repo_root() / "data" / "areas" / "cross-city" / city_dir / "geometry.geojson"
    )
    if not geometry_path.is_file():
        return []
    geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    rows: list[CrossCityMetricRow] = []
    for _index, feature in enumerate(geometry["features"], start=1):
        props = feature["properties"]
        geoid = str(props["GEOID"]).zfill(11)
        income = acs_metric(city_dir, geoid, "median_household_income")
        population_value = acs_metric(city_dir, geoid, "population")
        older = acs_share_pct(city_dir, geoid, "homes_built_before_1980")
        canopy = canopy_pct_for(city_dir, geoid)
        temperature = thermal_mean_c_for(city_dir, geoid)
        missing_reasons: dict[str, str] = {}
        if temperature is None:
            missing_reasons["temperature_c"] = _MISSING_THERMAL
        if income is None:
            missing_reasons["median_household_income"] = "ACS income estimate missing."
        if population_value is None:
            missing_reasons["population"] = "ACS population estimate missing."
        if canopy is None:
            missing_reasons["tree_canopy_pct"] = "National canopy value missing."
        if older is None:
            missing_reasons["homes_built_before_1980"] = (
                "ACS older-housing share missing."
            )
        rows.append(
            CrossCityMetricRow(
                city_id=city.city_id,
                zone_id=geoid,
                geoid=geoid,
                # AREA_IDENTITY_V1: Census tract label (not Comparison Area N).
                label=_tract_display_name(geoid),
                temperature_c=temperature,
                median_household_income=income,
                population=(
                    int(round(population_value)) if population_value is not None else None
                ),
                tree_canopy_pct=canopy,
                homes_built_before_1980=older,
                coverage_flags={
                    "temperature_c": temperature is not None,
                    "median_household_income": income is not None,
                    "population": population_value is not None,
                    "tree_canopy_pct": canopy is not None,
                    "homes_built_before_1980": older is not None,
                },
                missing_reasons=missing_reasons,
                comparison_clock=_comparison_clock(city.city_id),
            )
        )
    return rows


def _axis_value(row: CrossCityMetricRow, axis: MetricAxis) -> float | int | None:
    return getattr(row, axis.value)


def _build_metrics_response(*, axes: CrossCityAxes) -> CrossCityMetricsResponse:
    rows: list[CrossCityMetricRow] = []
    for city in list_cities():
        rows.extend(_city_rows(city))
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


@router.get("/cross-city/cities/{city_id}/geometry")
def get_cross_city_city_geometry(city_id: str) -> Any:
    """Per-city comparison geometry for the Explore City map."""
    city = _city_or_404(city_id)
    city_dir = _CITY_ID_TO_DIR.get(city.city_id)
    if not city_dir:
        raise HTTPException(status_code=404, detail=f"No geometry for {city_id}")
    geometry_path = (
        _repo_root() / "data" / "areas" / "cross-city" / city_dir / "geometry.geojson"
    )
    if not geometry_path.is_file():
        raise HTTPException(status_code=404, detail=f"Geometry not packaged for {city_id}")
    from fastapi.responses import Response

    return Response(
        content=geometry_path.read_text(encoding="utf-8"),
        media_type="application/geo+json",
        headers={"X-HVA-City-ID": str(city.city_id)},
    )


@router.get("/cross-city/metrics")
def get_cross_city_metrics() -> CrossCityMetricsResponse:
    return _build_metrics_response(
        axes=CrossCityAxes(
            x=MetricAxis.TREE_CANOPY_PCT,
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
