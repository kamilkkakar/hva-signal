"""Build per-signal public provenance views. Do not collapse A and B.

Unpublished helper. Does not bind a route, call FortyGuard, or edit job APIs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from app.domain.enums import DataStatus, ThermalDataSource
from app.domain.signals import SignalAvailability, SignalProvenance, ThermalSignalKind
from app.schemas.signal_provenance import (
    A_REQUIRED_WHEN_COMPUTED,
    A_UNCOMPUTED_AVAILABILITY,
    B_FORBIDDEN_FIELDS,
    B_REQUIRED_WHEN_PATH_KNOWN,
    NATIONAL_AGGREGATION_SPEC,
    NATIONAL_AREA_PREFIX,
    PHOENIX_AGGREGATION_SPEC,
    PHOENIX_GEOMETRY_TOKEN,
    PHOENIX_REFERENCE_TOKEN,
    SOURCE_STATUS_PAIRS,
    BannerLabel,
    ProvenanceDisplayState,
    PublicSignalProvenanceView,
)

B_FORBIDDEN_COPY: Final[tuple[str, ...]] = (
    "Reference:",
    "reference_version",
    "reference_source",
    "Decision 8",
    "decision8",
    "q_A",
    "NOW",
    "current conditions",
)
A_TITLE: Final = "Nighttime Historical Thermal Signal"
B_TITLE: Final = "Selected-Time Thermal Snapshot"
A_NOT_PREPARED_COPY: Final = (
    "Historical nighttime signal is not prepared for this analysis window."
)
PATH_STEM: Final[dict[ThermalDataSource, str]] = {
    ThermalDataSource.FORTYGUARD_LIVE: "FORTYGUARD LIVE",
    ThermalDataSource.FORTYGUARD_CACHED: "FORTYGUARD CACHED",
    ThermalDataSource.REPLAY: "REPLAY",
}


class SignalProvenanceError(ValueError):
    """Policy violation. Fail closed; do not relabel live over cached."""


def a_is_computed(availability: SignalAvailability | None) -> bool:
    if availability is None:
        return False
    return availability not in A_UNCOMPUTED_AVAILABILITY


def decision8_panel_permitted(signal_kind: ThermalSignalKind) -> bool:
    return signal_kind == ThermalSignalKind.HISTORICAL_NORMALIZED


def reference_fields_permitted(signal_kind: ThermalSignalKind) -> bool:
    return signal_kind == ThermalSignalKind.HISTORICAL_NORMALIZED


def qa_hover_permitted(signal_kind: ThermalSignalKind) -> bool:
    return signal_kind == ThermalSignalKind.HISTORICAL_NORMALIZED


def legacy_thermal_source(
    *,
    selected_time_requested: bool,
    historical_source: ThermalDataSource | str | None,
) -> str | None:
    """A-only compatibility. Null whenever Signal B is requested."""
    if selected_time_requested:
        return None
    if historical_source is None:
        return None
    if isinstance(historical_source, ThermalDataSource):
        return historical_source.value
    return historical_source


def refuse_collapsed_source_tape() -> None:
    raise SignalProvenanceError(
        "A and B never collapse into one SourceTape, data_status, or thermal_source"
    )


def refuse_areas_catalog_as_b_provenance(
    catalog_reference_version: str | None = None,
) -> None:
    """L9: GET /areas.reference_version is not selected_time.provenance."""
    raise SignalProvenanceError(
        "GET /areas reference_version is not B provenance"
        + (f" ({catalog_reference_version})" if catalog_reference_version else "")
    )


def refuse_preference_as_source(acquisition_preference: str | None = None) -> None:
    """L10: acquisition_preference is intent, not evidence."""
    raise SignalProvenanceError(
        "acquisition_preference is not source; live only after a live acquire"
        + (f" ({acquisition_preference})" if acquisition_preference else "")
    )


def provenance_banner(
    source: ThermalDataSource | None,
    data_status: DataStatus | None,
) -> tuple[BannerLabel, str | None]:
    """Map one signal's source+status. Mixed live/cached pairs raise; live never wins."""
    if data_status == DataStatus.UNAVAILABLE or (
        source is None and data_status is None
    ):
        return "UNAVAILABLE", None
    if source is None or data_status is None:
        return "UNAVAILABLE", None
    allowed = SOURCE_STATUS_PAIRS[source]
    if data_status not in allowed:
        raise SignalProvenanceError(
            "illegal source/data_status pair; live does not beat cached"
        )
    stem = PATH_STEM[source]
    if data_status == DataStatus.PARTIAL:
        return "PARTIAL", stem
    if source == ThermalDataSource.FORTYGUARD_CACHED:
        return "FORTYGUARD CACHED", stem
    if source == ThermalDataSource.FORTYGUARD_LIVE:
        return "FORTYGUARD LIVE", stem
    return "REPLAY", stem


def _require_fields(
    view: PublicSignalProvenanceView, required: frozenset[str], *, role: str
) -> None:
    missing = [name for name in sorted(required) if getattr(view, name) is None]
    if missing:
        raise SignalProvenanceError(f"{role} provenance missing required fields: {missing}")


def assert_b_has_no_reference(view: PublicSignalProvenanceView) -> None:
    if view.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
        return
    dumped = view.public_dump()
    leaked = sorted(B_FORBIDDEN_FIELDS.intersection(dumped))
    if leaked:
        raise SignalProvenanceError(f"Signal B public dump leaked forbidden fields: {leaked}")
    if view.reference_version is not None or view.reference_source is not None:
        raise SignalProvenanceError("Signal B provenance cannot carry a historical reference")


def assert_national_b_stamps(*, area_id: str, view: PublicSignalProvenanceView) -> None:
    if not area_id.startswith(NATIONAL_AREA_PREFIX):
        return
    if view.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
        raise SignalProvenanceError("national stitch identity is not a historical reference")
    assert_b_has_no_reference(view)
    geometry = view.geometry_version or ""
    if PHOENIX_GEOMETRY_TOKEN in geometry or PHOENIX_REFERENCE_TOKEN in geometry:
        raise SignalProvenanceError(
            "national B cannot inherit Phoenix A geometry or reference stamps"
        )
    if view.aggregation_spec_version == PHOENIX_AGGREGATION_SPEC:
        raise SignalProvenanceError("national B cannot use the Phoenix aggregation id")
    if (
        view.aggregation_spec_version is not None
        and view.aggregation_spec_version != NATIONAL_AGGREGATION_SPEC
    ):
        raise SignalProvenanceError("national B aggregation_spec_version must be the national id")


def assert_ab_field_guarantees(
    historical: PublicSignalProvenanceView | None,
    selected_time: PublicSignalProvenanceView | None,
    *,
    a_computed: bool = False,
    b_path_known: bool = False,
    selected_time_requested: bool = False,
    national_area_id: str | None = None,
) -> None:
    """Acceptance locks from 07 §5 / §13. Raises on any A/B collapse or B leak."""
    if historical is not None:
        if historical.signal_kind != ThermalSignalKind.HISTORICAL_NORMALIZED:
            raise SignalProvenanceError("historical view must be historical_normalized")
        if a_computed:
            _require_fields(historical, A_REQUIRED_WHEN_COMPUTED, role="Signal A computed")
    if selected_time is not None:
        if selected_time.signal_kind != ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
            raise SignalProvenanceError("selected_time view must be selected_time_snapshot")
        assert_b_has_no_reference(selected_time)
        if b_path_known:
            _require_fields(
                selected_time, B_REQUIRED_WHEN_PATH_KNOWN, role="Signal B path-known"
            )
        if national_area_id is not None:
            assert_national_b_stamps(area_id=national_area_id, view=selected_time)
    if selected_time_requested:
        if legacy_thermal_source(
            selected_time_requested=True,
            historical_source=historical.source if historical else None,
        ) is not None:
            raise SignalProvenanceError("legacy_thermal_source must be null when B is requested")
    if (
        historical is not None
        and selected_time is not None
        and historical.request_fingerprint
        and selected_time.request_fingerprint
        and historical.request_fingerprint == selected_time.request_fingerprint
    ):
        raise SignalProvenanceError(
            "A and B request fingerprints must not be the same digest"
        )


def view_from_internal(
    provenance: SignalProvenance,
    *,
    geometry_sha256: str | None = None,
    availability: SignalAvailability | None = None,
    snapshot_present: bool = False,
    computed: bool | None = None,
    area_id: str | None = None,
) -> PublicSignalProvenanceView:
    """Project internal SignalProvenance to the public view. Never maps /areas onto B."""
    kind = provenance.signal_kind
    if kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
        if provenance.reference_version is not None or provenance.reference_source is not None:
            raise SignalProvenanceError("Signal B provenance cannot carry a historical reference")
    view = PublicSignalProvenanceView(
        signal_kind=kind,
        source=provenance.source,
        data_status=provenance.data_status,
        target_timestamp=provenance.target_timestamp,
        timezone=provenance.timezone,
        geometry_version=provenance.geometry_version,
        geometry_sha256=geometry_sha256,
        aggregation_spec_version=provenance.aggregation_spec_version,
        reference_version=provenance.reference_version,
        reference_source=provenance.reference_source,
        request_fingerprint=provenance.vendor_request_fingerprint,
    )
    a_computed = computed if computed is not None else (
        kind == ThermalSignalKind.HISTORICAL_NORMALIZED and a_is_computed(availability)
    )
    b_path = snapshot_present or (
        kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT and provenance.source is not None
    )
    if a_computed and kind == ThermalSignalKind.HISTORICAL_NORMALIZED:
        _require_fields(view, A_REQUIRED_WHEN_COMPUTED, role="Signal A computed")
    if b_path and kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
        _require_fields(view, B_REQUIRED_WHEN_PATH_KNOWN, role="Signal B path-known")
        if snapshot_present and view.request_fingerprint is None:
            raise SignalProvenanceError(
                "Signal B snapshot identity requires request_fingerprint"
            )
    if area_id is not None and kind == ThermalSignalKind.SELECTED_TIME_SNAPSHOT:
        assert_national_b_stamps(area_id=area_id, view=view)
    return view


def _format_clock(ts: datetime, timezone: str, *, signal_a: bool) -> str:
    date = ts.strftime("%Y-%m-%d")
    if signal_a:
        return f"{date} 03:00 {timezone}"
    return f"{date} {ts.strftime('%H:00')} {timezone}"


def historical_lines(
    view: PublicSignalProvenanceView,
    *,
    availability: SignalAvailability | None = None,
) -> tuple[str, ...]:
    if availability == SignalAvailability.NOT_PREPARED:
        return (A_TITLE, A_NOT_PREPARED_COPY)
    banner, _stem = provenance_banner(view.source, view.data_status)
    lines = [A_TITLE]
    if view.target_timestamp is not None and view.timezone:
        lines.append(_format_clock(view.target_timestamp, view.timezone, signal_a=True))
    lines.append(f"Target source: {banner}")
    if view.reference_version and view.reference_source:
        lines.append(f"Reference: {view.reference_version} ({view.reference_source})")
    elif view.reference_version:
        lines.append(f"Reference: {view.reference_version}")
    if view.geometry_version:
        lines.append(f"Geometry: {view.geometry_version}")
    return tuple(lines)


def selected_time_lines(view: PublicSignalProvenanceView) -> tuple[str, ...]:
    assert_b_has_no_reference(view)
    banner, stem = provenance_banner(view.source, view.data_status)
    target = banner if banner != "PARTIAL" else f"PARTIAL ({stem})"
    lines = [B_TITLE]
    if view.target_timestamp is not None and view.timezone:
        lines.append(_format_clock(view.target_timestamp, view.timezone, signal_a=False))
    lines.append(f"Target source: {target}")
    if view.geometry_version:
        lines.append(f"Geometry: {view.geometry_version}")
    if view.aggregation_spec_version:
        lines.append(f"Aggregation: {view.aggregation_spec_version}")
    text = "\n".join(lines)
    for token in B_FORBIDDEN_COPY:
        if token in text:
            raise SignalProvenanceError(f"Signal B lines leaked {token!r}")
    return tuple(lines)


def display_state(
    view: PublicSignalProvenanceView,
    *,
    selected_time_requested: bool = False,
    availability: SignalAvailability | None = None,
) -> ProvenanceDisplayState:
    banner, stem = provenance_banner(view.source, view.data_status)
    kind = view.signal_kind
    if kind == ThermalSignalKind.HISTORICAL_NORMALIZED:
        lines = historical_lines(view, availability=availability)
    else:
        lines = selected_time_lines(view)
    return ProvenanceDisplayState(
        signal_kind=kind,
        banner=banner,
        path_stem=stem,
        lines=lines,
        show_reference=reference_fields_permitted(kind),
        show_decision8=decision8_panel_permitted(kind),
        show_qa_hover=qa_hover_permitted(kind),
        legacy_thermal_source=legacy_thermal_source(
            selected_time_requested=selected_time_requested,
            historical_source=view.source
            if kind == ThermalSignalKind.HISTORICAL_NORMALIZED
            else None,
        ),
    )


def active_signal_view(
    active: ThermalSignalKind,
    historical: PublicSignalProvenanceView | None,
    selected_time: PublicSignalProvenanceView | None,
) -> PublicSignalProvenanceView | None:
    """Return the active signal only. Never blends fields."""
    if active == ThermalSignalKind.HISTORICAL_NORMALIZED:
        return historical
    return selected_time
