import {
  AXIS_HIGH,
  AXIS_LOW,
  STAMP_ORDERING_SUPPORTED,
  STAMP_ORDERING_WITHHELD,
  STRIP_MEANING,
} from "./copy";
import { formatComparisonFrame, formatExactPosition, markForSelected } from "./bind";
import type { HistoricalPositionInput, HistoricalPositionView } from "./types";

function stampFor(comparison: HistoricalPositionInput["comparison"]): string | null {
  if (comparison === "supported") {
    return STAMP_ORDERING_SUPPORTED;
  }
  if (comparison === "withheld") {
    return STAMP_ORDERING_WITHHELD;
  }
  return null;
}

function assistiveFor(input: {
  count: number;
  stamp: string | null;
}): string {
  const n = input.count;
  const noun = n === 1 ? "mark" : "marks";
  if (!input.stamp) {
    return `${n} zone ${noun} on each zone’s own 3 a.m. historical position.`;
  }
  return `${n} zone ${noun} on each zone’s own 3 a.m. historical position. ${input.stamp}.`;
}

export function presentHistoricalPosition(
  input: HistoricalPositionInput,
): HistoricalPositionView {
  const visible = input.marks.length > 0 && input.comparison !== "unavailable";
  const marks = visible ? input.marks : [];
  const comparison = visible ? input.comparison : "unavailable";
  const comparisonStamp = visible ? stampFor(comparison) : null;
  const selected = visible ? markForSelected(marks, input.selectedZoneId) : null;

  return {
    visible,
    marks,
    comparison,
    comparisonStamp,
    selected,
    selectedExact: selected ? formatExactPosition(selected.position) : null,
    axisLow: AXIS_LOW,
    axisHigh: AXIS_HIGH,
    meaning: STRIP_MEANING,
    frameCaption: visible
      ? formatComparisonFrame(input.historicalYears, input.referenceHour)
      : null,
    assistive: assistiveFor({ count: marks.length, stamp: comparisonStamp }),
    selectedAssistive: selected
      ? `Selected zone on its own 3 a.m. historical position. ${comparisonStamp ?? ""}`.trim()
      : null,
  };
}

export function chartChromeStrings(view: HistoricalPositionView): string[] {
  return [
    view.comparisonStamp ?? "",
    view.axisLow,
    view.axisHigh,
    view.meaning,
    view.frameCaption ?? "",
    view.assistive,
    view.selectedAssistive ?? "",
  ];
}

export function chartChromeLeaksMethod(view: HistoricalPositionView): boolean {
  const blob = chartChromeStrings(view).join("\n");
  return (
    blob.includes("q_A") ||
    blob.includes("Decision 8") ||
    blob.includes("D8") ||
    blob.includes("S =") ||
    blob.includes("0.10") ||
    blob.includes("quantile") ||
    blob.includes("ECDF") ||
    blob.includes("probability")
  );
}
