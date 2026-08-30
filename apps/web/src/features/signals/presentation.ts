import {
  B_CACHED_COPY,
  B_FETCHING_COPY,
  B_NOT_REQUESTED_COPY,
  B_PARTIAL_COPY,
  B_READY_COPY,
  B_UNAVAILABLE_COPY,
  FORBIDDEN_L6_PHRASES,
  LIVE_DEMO_BODY,
  NO_COMBINED_SCORE_COPY,
  REFERENCE_NOT_PREPARED_ACQUISITION_COPY,
  REFERENCE_NOT_PREPARED_COPY,
  REFERENCE_NOT_PREPARED_LOCK_COPY,
  REFERENCE_NOT_PREPARED_STAMP,
  REUSE_ONLY_COPY,
  SIGNAL_A_FAILED_COPY,
  SIGNAL_A_INERT_COPY,
  SIGNAL_A_INSUFFICIENT_COPY,
  SIGNAL_A_PENDING_COPY,
  SIGNAL_A_READY_COPY,
} from "./copy";
import type { SignalFeatureFlags } from "./flags";
import {
  SELECTED_TIME_TITLE,
  type HistoricalAvailability,
  type HistoricalSection,
  type HistoricalView,
  type SelectedTimeSection,
  type SelectedTimeView,
  type SignalATone,
  type SignalAUx,
  type SignalBSourceLabel,
  type SignalBUx,
  type SnapshotZone,
  type TwoSignalView,
} from "./types";

export function sortSnapshotZones(zones: readonly SnapshotZone[]): SnapshotZone[] {
  return [...zones].sort((left, right) => left.zone_id.localeCompare(right.zone_id));
}

export function historicalUx(availability: HistoricalAvailability): SignalAUx {
  switch (availability) {
    case "NOT_REQUESTED":
      return "historical_not_requested";
    case "NOT_PREPARED":
      return "historical_not_prepared";
    case "PENDING":
      return "historical_pending";
    case "READY":
      return "historical_ready";
    case "FAILED":
      return "historical_failed";
    default:
      return "historical_insufficient";
  }
}

function historicalTone(ux: SignalAUx): SignalATone {
  switch (ux) {
    case "historical_not_requested":
      return "inert";
    case "historical_not_prepared":
      return "not-prepared";
    case "historical_pending":
      return "pending";
    case "historical_ready":
      return "historical";
    case "historical_insufficient":
      return "insufficient";
    case "historical_failed":
      return "failed";
  }
}

function historicalStamp(ux: SignalAUx): string {
  switch (ux) {
    case "historical_not_requested":
      return "NOT REQUESTED";
    case "historical_not_prepared":
      return REFERENCE_NOT_PREPARED_STAMP;
    case "historical_pending":
      return "PENDING";
    case "historical_ready":
      return "HISTORICAL READY";
    case "historical_insufficient":
      return "INSUFFICIENT EVIDENCE";
    case "historical_failed":
      return "FAILED";
  }
}

function historicalCopy(ux: SignalAUx): string[] {
  switch (ux) {
    case "historical_not_requested":
      return [SIGNAL_A_INERT_COPY];
    case "historical_not_prepared":
      return [
        REFERENCE_NOT_PREPARED_COPY,
        REFERENCE_NOT_PREPARED_ACQUISITION_COPY,
        REFERENCE_NOT_PREPARED_LOCK_COPY,
      ];
    case "historical_pending":
      return [SIGNAL_A_PENDING_COPY];
    case "historical_ready":
      return [SIGNAL_A_READY_COPY];
    case "historical_insufficient":
      return [SIGNAL_A_INSUFFICIENT_COPY];
    case "historical_failed":
      return [SIGNAL_A_FAILED_COPY];
  }
}

export function presentHistorical(section: HistoricalSection): HistoricalView {
  const ux = historicalUx(section.availability);
  return {
    ux,
    stamp: historicalStamp(ux),
    tone: historicalTone(ux),
    availability: section.availability,
    copy: historicalCopy(ux),
  };
}

export function selectedTimeUx(
  section: SelectedTimeSection,
  flags: Pick<SignalFeatureFlags, "liveDemoConfirmation">,
): SignalBUx {
  if (
    section.reason_code === "LIVE_DEMO_NOT_REQUESTED" &&
    flags.liveDemoConfirmation
  ) {
    return "live_demo_confirmation";
  }
  switch (section.availability) {
    case "NOT_REQUESTED":
      return "b_not_requested";
    case "FETCHING":
    case "PENDING":
      return "b_fetching";
    case "PARTIAL":
      return "b_partial";
    case "UNAVAILABLE":
    case "FAILED":
      return "b_unavailable";
    case "READY":
      if (section.ready_scene === "ready") {
        return "b_ready";
      }
      return "b_cached";
  }
}

function selectedTimeStamp(ux: SignalBUx): string {
  switch (ux) {
    case "b_not_requested":
      return "NOT REQUESTED";
    case "b_cached":
      return "CACHED";
    case "b_unavailable":
      return "UNAVAILABLE";
    case "b_fetching":
      return "FETCHING";
    case "b_partial":
      return "PARTIAL";
    case "b_ready":
      return "READY";
    case "live_demo_confirmation":
      return "LIVE DEMO CONFIRMATION";
  }
}

function selectedTimeSource(
  ux: SignalBUx,
  section: SelectedTimeSection,
): SignalBSourceLabel | null {
  if (ux === "b_not_requested") {
    return null;
  }
  if (ux === "b_fetching") {
    return "FETCHING";
  }
  if (ux === "b_partial") {
    return "PARTIAL";
  }
  if (ux === "b_unavailable" || ux === "live_demo_confirmation") {
    return "UNAVAILABLE";
  }
  if (section.provenance_source === "replay" || section.data_status === "replay") {
    return "REPLAY";
  }
  if (
    section.provenance_source === "fortyguard_cached" ||
    section.data_status === "cached"
  ) {
    return "CACHED";
  }
  return "SNAPSHOT";
}

function selectedTimeCopy(ux: SignalBUx): string {
  switch (ux) {
    case "b_not_requested":
      return B_NOT_REQUESTED_COPY;
    case "b_cached":
      return B_CACHED_COPY;
    case "b_unavailable":
      return B_UNAVAILABLE_COPY;
    case "b_fetching":
      return B_FETCHING_COPY;
    case "b_partial":
      return B_PARTIAL_COPY;
    case "b_ready":
      return B_READY_COPY;
    case "live_demo_confirmation":
      return LIVE_DEMO_BODY;
  }
}

function coverageLabel(section: SelectedTimeSection): string | null {
  if (section.valid_zone_count == null) {
    return null;
  }
  const unknown =
    section.missing_zone_ids.length > 0
      ? ` · ${section.missing_zone_ids.length} unknown`
      : "";
  return `Zones ${section.valid_zone_count}/${section.expected_zone_count}${unknown}`;
}

function rangeLabel(section: SelectedTimeSection): string | null {
  if (section.temperature_min_c == null || section.temperature_max_c == null) {
    return null;
  }
  return `Range ${section.temperature_min_c}–${section.temperature_max_c} °C (text fact, not a color domain).`;
}

export function presentSelectedTime(
  section: SelectedTimeSection,
  flags: Pick<SignalFeatureFlags, "liveDemoConfirmation">,
): SelectedTimeView {
  const ux = selectedTimeUx(section, flags);
  return {
    ux,
    stamp: selectedTimeStamp(ux),
    source: selectedTimeSource(ux, section),
    availability: section.availability,
    reuse_only: REUSE_ONLY_COPY,
    copy: selectedTimeCopy(ux),
    show_live_demo: ux === "live_demo_confirmation",
    live_tape: false,
    title: SELECTED_TIME_TITLE,
    zones: sortSnapshotZones(section.zones),
    coverage_label: coverageLabel(section),
    range_label: rangeLabel(section),
  };
}

export function presentTwoSignals(input: {
  historical: HistoricalSection;
  selectedTime: SelectedTimeSection;
  flags: SignalFeatureFlags;
}): TwoSignalView {
  return {
    mounted: input.flags.selectedTimeSnapshotInterface,
    combined_score_authorized: false,
    combined_score: null,
    overall_job_complete: false,
    signal_a_blocks_signal_b: false,
    independence_copy: NO_COMBINED_SCORE_COPY,
    historical: presentHistorical(input.historical),
    selected_time: presentSelectedTime(input.selectedTime, input.flags),
  };
}

export function notPreparedLooksLikeLowRisk(view: HistoricalView): boolean {
  if (view.ux !== "historical_not_prepared") {
    return false;
  }
  if (view.tone !== "not-prepared") {
    return true;
  }
  if (view.stamp !== REFERENCE_NOT_PREPARED_STAMP) {
    return true;
  }
  if (/\bREADY\b/.test(view.stamp) || /\bCOMPLETE\b/.test(view.stamp)) {
    return true;
  }
  const blob = [view.stamp, ...view.copy].join("\n").toLowerCase();
  if (FORBIDDEN_L6_PHRASES.some((phrase) => blob.includes(phrase))) {
    return true;
  }
  if (/\bcool\b/.test(blob) && !blob.includes("not treated as cool")) {
    return true;
  }
  if (/\bs\s*[:=]\s*0\b/.test(blob)) {
    return true;
  }
  if (!blob.includes("not treated as safe")) {
    return true;
  }
  if (!blob.includes("not prepared")) {
    return true;
  }
  return false;
}

export function selectedTimeShowsLiveChrome(view: SelectedTimeView): boolean {
  if (view.live_tape) {
    return true;
  }
  const blob = [view.stamp, view.source ?? "", view.copy, view.reuse_only]
    .join("\n")
    .toLowerCase();
  return blob.includes("fortyguard live") || blob.includes("live tape");
}
