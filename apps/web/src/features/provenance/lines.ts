import { signalProvenanceBanner } from "./banner";
import { assertBHasNoReference } from "./fieldGuarantees";
import {
  A_NOT_PREPARED_COPY,
  B_FORBIDDEN_COPY,
  type PublicSignalProvenance,
} from "./types";

function clockLine(
  timestamp: string,
  timezone: string,
  signalA: boolean,
): string {
  const date = timestamp.slice(0, 10);
  if (signalA) {
    return `${date} 03:00 ${timezone}`;
  }
  const hour = timestamp.slice(11, 13) || "00";
  return `${date} ${hour}:00 ${timezone}`;
}

export function historicalLines(view: PublicSignalProvenance): string[] {
  if (view.availability === "NOT_PREPARED") {
    return ["Nighttime Historical Thermal Signal", A_NOT_PREPARED_COPY];
  }
  const { banner } = signalProvenanceBanner({
    source: view.source,
    dataStatus: view.data_status,
  });
  const lines = ["Nighttime Historical Thermal Signal"];
  if (view.target_timestamp && view.timezone) {
    lines.push(clockLine(view.target_timestamp, view.timezone, true));
  }
  lines.push(`Target source: ${banner}`);
  if (view.reference_version && view.reference_source) {
    lines.push(`Reference: ${view.reference_version} (${view.reference_source})`);
  } else if (view.reference_version) {
    lines.push(`Reference: ${view.reference_version}`);
  }
  if (view.geometry_version) {
    lines.push(`Geometry: ${view.geometry_version}`);
  }
  return lines;
}

export function selectedTimeLines(view: PublicSignalProvenance): string[] {
  assertBHasNoReference(view);
  const { banner, pathStem } = signalProvenanceBanner({
    source: view.source,
    dataStatus: view.data_status,
  });
  const target =
    banner === "PARTIAL" && pathStem != null ? `PARTIAL (${pathStem})` : banner;
  const lines = ["Selected-Time Thermal Snapshot"];
  if (view.target_timestamp && view.timezone) {
    lines.push(clockLine(view.target_timestamp, view.timezone, false));
  }
  lines.push(`Target source: ${target}`);
  if (view.geometry_version) {
    lines.push(`Geometry: ${view.geometry_version}`);
  }
  if (view.aggregation_spec_version) {
    lines.push(`Aggregation: ${view.aggregation_spec_version}`);
  }
  const text = lines.join("\n");
  for (const token of B_FORBIDDEN_COPY) {
    if (text.includes(token)) {
      throw new Error(`Signal B lines leaked ${token}`);
    }
  }
  return lines;
}
