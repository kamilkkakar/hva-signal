"""Unpublished held-document assemble. GET never acquires. No spend fields.

publication_status stays UNPUBLISHED. NOT_PREPARED is not a fetch trigger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal

from app.services.daily_thermal_profile import DailyProfileComputation, build_profile
from app.services.seasonal_thermal import SlotValue, assemble_seasonal_summary
from app.services.year_over_year import YearComparisonComputation, compare_s2_anchor_0300_from_reference_panel

ASSEMBLE_FROM = "held_only"
PUBLICATION_STATUS = "UNPUBLISHED"
FAMILY_CONTRACT = "hva-signal-temporal-documents-v1"

SPEND_FIELD_NAMES = frozenset(
    {
        "spend",
        "allowance",
        "authorized_max_units",
        "approval",
        "acquisition_preference",
        "credits",
        "price",
        "units_spent",
    }
)


class AssembleAcquireError(RuntimeError):
    """GET/assemble must never start FortyGuard or 93-night prep."""


@dataclass
class TemporalDocument:
    document_id: str
    resource_kind: str
    availability: str
    publication_status: str
    assemble_from: str
    withhold_reason: str | None
    payload: dict[str, Any] = field(default_factory=dict)

    def public_projection(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "resource_kind": self.resource_kind,
            "availability": self.availability,
            "publication_status": self.publication_status,
            "metrics": self.payload.get("metrics", []),
        }


def _assert_held_only(assemble_from: str) -> None:
    if assemble_from != ASSEMBLE_FROM:
        raise AssembleAcquireError("assemble refuses any path that would acquire")


def _assert_no_spend(record: dict[str, Any]) -> None:
    keys = set(record)
    leaked = keys & SPEND_FIELD_NAMES
    if leaked:
        raise ValueError(f"spend fields are forbidden: {sorted(leaked)}")


def daily_document_id(area_id: str, zone_id: str, local_date: date, design: str, source_mode: str) -> str:
    return f"tdp.v1.{area_id}.{zone_id}.{local_date.isoformat()}.{design}.{source_mode}"


def season_document_id(area_id: str, zone_id: str, window_id: str, design: str, source_mode: str) -> str:
    return f"tss.v1.{area_id}.{zone_id}.{window_id}.{design}.{source_mode}"


def yoy_document_id(
    area_id: str,
    zone_id: str,
    window_id: str,
    year_a: int,
    year_b: int,
    design: str,
    source_mode: str,
) -> str:
    return f"tyc.v1.{area_id}.{zone_id}.{window_id}.{year_a}.{year_b}.{design}.{source_mode}"


def assemble_daily_profile(
    *,
    area_id: str,
    zone_id: str,
    local_date: date,
    hours: dict[int, float] | None,
    sampling_design: str = "HOURLY_24",
    source_mode: str = "replay",
    assemble_from: str = ASSEMBLE_FROM,
) -> TemporalDocument:
    _assert_held_only(assemble_from)
    doc_id = daily_document_id(area_id, zone_id, local_date, sampling_design, source_mode)
    if hours is None:
        doc = TemporalDocument(
            document_id=doc_id,
            resource_kind="daily_profile",
            availability="NOT_PREPARED",
            publication_status=PUBLICATION_STATUS,
            assemble_from=ASSEMBLE_FROM,
            withhold_reason="CUBE_NOT_HELD",
            payload={"metrics": []},
        )
        _assert_no_spend(doc.payload)
        return doc
    profile = build_profile(local_date=local_date, hours=hours, design=sampling_design, source_mode=source_mode)
    if sampling_design == "HOURLY_24" and profile.n_present < 18:
        availability = "NOT_PREPARED" if profile.n_present <= 1 else "WITHHELD"
        reason = "HOURLY_24_ON_SPARSE_CUBE" if profile.n_present <= 1 else "COVERAGE"
    else:
        availability = "READY"
        reason = None
    payload = {
        "metrics": _daily_metrics(profile),
        "coverage_class": profile.temporal_coverage_class,
        "interpolated": False,
    }
    _assert_no_spend(payload)
    return TemporalDocument(
        document_id=doc_id,
        resource_kind="daily_profile",
        availability=availability,
        publication_status=PUBLICATION_STATUS,
        assemble_from=ASSEMBLE_FROM,
        withhold_reason=reason,
        payload=payload,
    )


def assemble_season_summary(
    *,
    area_id: str,
    zone_id: str,
    window_id: str,
    slots: list[SlotValue] | None,
    sampling_design: str = "ANCHOR_0300",
    source_mode: str = "replay",
    assemble_from: str = ASSEMBLE_FROM,
) -> TemporalDocument:
    _assert_held_only(assemble_from)
    doc_id = season_document_id(area_id, zone_id, window_id, sampling_design, source_mode)
    if slots is None:
        return TemporalDocument(
            document_id=doc_id,
            resource_kind="season_summary",
            availability="NOT_PREPARED",
            publication_status=PUBLICATION_STATUS,
            assemble_from=ASSEMBLE_FROM,
            withhold_reason="CUBE_NOT_HELD",
            payload={"metrics": []},
        )
    summary = assemble_seasonal_summary(window_id=window_id, slots=slots, sampling_design=sampling_design)
    payload = {
        "window_id": summary.window_id,
        "public_label": summary.public_label,
        "mean_temperature_c": summary.mean_temperature_c,
        "coverage_class": summary.coverage_class,
        "metrics": [],
    }
    _assert_no_spend(payload)
    return TemporalDocument(
        document_id=doc_id,
        resource_kind="season_summary",
        availability=summary.availability,
        publication_status=PUBLICATION_STATUS,
        assemble_from=ASSEMBLE_FROM,
        withhold_reason=summary.withhold_reason,
        payload=payload,
    )


def assemble_year_comparison(
    *,
    area_id: str,
    zone_id: str,
    window_id: str,
    year_a: int,
    year_b: int,
    reference_path: Path | None,
    sampling_design: str = "ANCHOR_0300",
    source_mode: str = "replay",
    assemble_from: str = ASSEMBLE_FROM,
) -> TemporalDocument:
    _assert_held_only(assemble_from)
    doc_id = yoy_document_id(area_id, zone_id, window_id, year_a, year_b, sampling_design, source_mode)
    if reference_path is None:
        return TemporalDocument(
            document_id=doc_id,
            resource_kind="year_comparison",
            availability="NOT_PREPARED",
            publication_status=PUBLICATION_STATUS,
            assemble_from=ASSEMBLE_FROM,
            withhold_reason="CUBE_NOT_HELD",
            payload={"metrics": []},
        )
    result = compare_s2_anchor_0300_from_reference_panel(
        reference_path, year_earlier=year_a, year_later=year_b
    )
    availability = "READY" if result.mean_difference_c is not None else "WITHHELD"
    if result.comparability == "INCOMPARABLE":
        availability = "WITHHELD"
    payload = {
        "comparability": result.comparability,
        "mean_difference_c": result.mean_difference_c,
        "label": result.label,
        "pair_coverage_class": result.pair_coverage_class,
        "metrics": [],
    }
    _assert_no_spend(payload)
    return TemporalDocument(
        document_id=doc_id,
        resource_kind="year_comparison",
        availability=availability,
        publication_status=PUBLICATION_STATUS,
        assemble_from=ASSEMBLE_FROM,
        withhold_reason=None if availability == "READY" else (result.fail_closed_reasons[0] if result.fail_closed_reasons else "COVERAGE"),
        payload=payload,
    )


def _daily_metrics(profile: DailyProfileComputation) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    if profile.n_present:
        metrics.append(
            {
                "metric_id": "observed_hour_c",
                "what": "Observed hour zone-mean TCM °C among present hours",
                "relative_to": "absolute zone-mean TCM °C",
                "period": f"{profile.local_date.isoformat()} {profile.iana_timezone}",
                "why_it_matters": "Shows the local day in °C among hours actually observed; Signal A does not.",
                "direction": "warmer or cooler among observed hours",
                "value": profile.t_max_obs_c,
                "unit": "celsius",
                "withheld": False,
            }
        )
    return metrics
