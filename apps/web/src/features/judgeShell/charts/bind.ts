import type { AnalysisResultStub, ZoneDecisionStub } from "@/api/analysisJobs";
import type {
  HistoricalPositionInput,
  HistoricalPositionMark,
  OrderingComparisonState,
} from "./types";

/** Accept only a finite existing index on the frozen 0–1 scale. Do not clamp or invent. */
export function finiteUnitInterval(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }
  if (value < 0 || value > 1) {
    return null;
  }
  return value;
}

function markFromZone(zone: ZoneDecisionStub): HistoricalPositionMark | null {
  const position = finiteUnitInterval(zone.q_A);
  if (position == null || !zone.zone_id) {
    return null;
  }
  return { zoneId: String(zone.zone_id), position };
}

function comparisonFromResult(
  result: AnalysisResultStub | null | undefined,
  markCount: number,
): OrderingComparisonState {
  if (markCount === 0) {
    return "unavailable";
  }
  const state = (
    result?.thermal_differentiation_state ??
    result?.hazard_spread?.differentiation_state ??
    ""
  ).toUpperCase();
  if (state === "SUFFICIENT") {
    return "supported";
  }
  if (state === "INSUFFICIENT") {
    return "withheld";
  }
  return "unavailable";
}

/**
 * Read existing job facts. Does not compute the historical index, spread, or a new floor.
 */
export function bindHistoricalPositions(input: {
  result?: AnalysisResultStub | null;
  selectedZoneId?: string | null;
}): HistoricalPositionInput {
  const result = input.result ?? null;
  const marks: HistoricalPositionMark[] = [];
  for (const zone of result?.zones ?? []) {
    const mark = markFromZone(zone);
    if (mark) {
      marks.push(mark);
    }
  }
  return {
    marks,
    comparison: comparisonFromResult(result, marks.length),
    selectedZoneId: input.selectedZoneId ?? null,
    historicalYears: result?.hazard_spread?.historical_years ?? null,
    referenceHour: result?.hazard_spread?.reference_hour ?? null,
  };
}

/** Details only. Three decimals — no 17-place dump, no percent. */
export function formatExactPosition(position: number): string {
  return position.toFixed(3);
}

export function formatYearSpan(years: readonly number[]): string | null {
  if (years.length === 0) {
    return null;
  }
  const sorted = [...years].sort((left, right) => left - right);
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  if (first == null || last == null) {
    return null;
  }
  if (first === last) {
    return String(first);
  }
  return `${first}–${last}`;
}

/** Caption only. Bind existing years/hour. No long reference IDs. */
export function formatComparisonFrame(
  years: readonly number[] | null,
  hour: string | null,
): string | null {
  if (!hour || !years?.length) {
    return null;
  }
  const span = formatYearSpan(years);
  if (!span) {
    return null;
  }
  return `${hour} · ${span} same hour`;
}

export function markForSelected(
  marks: readonly HistoricalPositionMark[],
  selectedZoneId: string | null,
): HistoricalPositionMark | null {
  if (!selectedZoneId) {
    return null;
  }
  return marks.find((mark) => mark.zoneId === selectedZoneId) ?? null;
}
