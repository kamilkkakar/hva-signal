import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { SPATIAL_SUPPORTED, SPATIAL_WITHHELD } from "./disclosureCopy";

export const PUBLIC_SEPARATION_DECIMALS = 4;
export const PUBLIC_POLICY_DECIMALS = 2;
export const PHOENIX_REFERENCE_YEARS = [2022, 2023, 2024] as const;
export const PHOENIX_REFERENCE_HOUR = "03:00";
export const DEFAULT_POLICY_FLOOR = 0.1;

export function formatPublicSeparation(value: number): string {
  if (!Number.isFinite(value)) {
    return "unavailable";
  }
  return value.toFixed(PUBLIC_SEPARATION_DECIMALS);
}

export function formatPublicPolicyRequirement(value: number): string {
  if (!Number.isFinite(value)) {
    return "unavailable";
  }
  return value.toFixed(PUBLIC_POLICY_DECIMALS);
}

export function formatYearSpan(years: readonly number[]): string {
  if (years.length === 0) {
    return "unavailable";
  }
  const sorted = [...years].sort((a, b) => a - b);
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  if (first === last) {
    return String(first);
  }
  return `${first}–${last}`;
}

export function spatialDifferentiationPlain(
  state: string | null | undefined,
): typeof SPATIAL_SUPPORTED | typeof SPATIAL_WITHHELD | null {
  if (state === "SUFFICIENT") {
    return SPATIAL_SUPPORTED;
  }
  if (state === "INSUFFICIENT") {
    return SPATIAL_WITHHELD;
  }
  return null;
}

export type HowDeterminedView = {
  historicalComparison: string;
  spatialDifferentiation: typeof SPATIAL_SUPPORTED | typeof SPATIAL_WITHHELD;
  observedSeparation: string;
  policyRequirement: string;
  observedSeparationExact: number;
};

function referenceYears(
  snapshot: AnalysisJobPayload,
  spreadYears: number[] | null | undefined,
): readonly number[] {
  if (spreadYears && spreadYears.length > 0) {
    return spreadYears;
  }
  if (snapshot.request?.area_id === "phoenix-demo") {
    return PHOENIX_REFERENCE_YEARS;
  }
  return [];
}

export function howDeterminedFromJob(
  snapshot: AnalysisJobPayload | null | undefined,
): HowDeterminedView | null {
  const spread = snapshot?.result?.hazard_spread;
  if (snapshot == null || spread == null) {
    return null;
  }
  const spatial = spatialDifferentiationPlain(
    spread.differentiation_state ?? snapshot.result?.thermal_differentiation_state,
  );
  if (spatial == null) {
    return null;
  }
  const observed = spread.observed_spread;
  if (observed == null || !Number.isFinite(observed)) {
    return null;
  }
  const hour = spread.reference_hour ?? PHOENIX_REFERENCE_HOUR;
  const yearSpan = formatYearSpan(referenceYears(snapshot, spread.historical_years));
  const historicalComparison =
    yearSpan === "unavailable" ? `unavailable at ${hour}` : `${yearSpan} at ${hour}`;
  return {
    historicalComparison,
    spatialDifferentiation: spatial,
    observedSeparation: formatPublicSeparation(observed),
    policyRequirement: formatPublicPolicyRequirement(spread.floor ?? DEFAULT_POLICY_FLOOR),
    observedSeparationExact: observed,
  };
}
