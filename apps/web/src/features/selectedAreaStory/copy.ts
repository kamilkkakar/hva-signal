import type { MapMode } from "@/features/areaContext/types";
import type { MapModeMeta } from "./types";

export const Q_THERMAL = "What is happening here?";
export const Q_DIFFERENT = "What makes this area different?";
export const Q_SUPPORT = "What support is identified?";
export const Q_VERIFY = "What should be verified next?";
export const GEOID_DETAILS_SUMMARY = "Census tract identifier";

export const B_WORDING = "AVAILABLE NOW — CACHED EVIDENCE" as const;
export const B_CLOCK = "2025-07-15 03:00" as const;
export const B_TIMEZONE = "America/Phoenix" as const;
export const B_COVERAGE = "25/25" as const;

export const INVENTORY_DISCLAIMER =
  "Partial regional inventory. Identification is not proof that cooling is available. A dataset miss does not establish that no cooling resource exists.";

export const R0_TEXT =
  "Select a catalog analysis area before reviewing thermal evidence or context.";
export const R1_TEXT =
  "Thermal order is withheld. Do not treat a rank as available. Review whether the historical series is sufficient before comparing areas.";
export const R2_TEXT =
  "Review the shown thermal order as comparative evidence only. This is not an intervention priority.";
export const R3_TEXT =
  "Review the cached nighttime temperature as absolute evidence for 2025-07-15 03:00 America/Phoenix. This is not a historical-position score and not a rank.";
export const R4_TEXT =
  "Review published ACS and canopy quantities for this analysis area. Do not treat a missing or unreliable estimate as low need.";
export const R5_TEXT =
  "Verify cooling access on the ground. Inventory identification is not proof that cooling is available.";

export const FORBIDDEN_STORY_TOKENS = [
  "vulnerability =",
  "high-risk",
  "high risk",
  "resilience score",
  "combined score",
  "no cooling site",
  "individual vulnerability",
  "deploy",
  "dispatch",
  "treat first",
  "backend_order",
  "heat-risk",
] as const;

export const MAP_MODE_META: readonly MapModeMeta[] = [
  {
    mode: "THERMAL",
    label: "Thermal",
    source: "FortyGuard TCM",
    year: "published observation",
    unit: "°C",
    meaning: "Zone-mean temperature for the published observation. Exact °C on hover.",
    fill: "job_ranking",
  },
  {
    mode: "TREE_CANOPY",
    label: "Tree canopy",
    source: "National land-cover canopy",
    year: "published",
    unit: "percent",
    meaning: "Share of plantable ground with tree canopy. Unreliable estimates are not map color.",
    fill: "quantity",
  },
  {
    mode: "INCOME",
    label: "Median household income",
    source: "ACS 5-year",
    year: "2020-2024",
    unit: "USD",
    meaning: "Median household income for the census tract. Unreliable estimates are not map color.",
    fill: "quantity",
  },
  {
    mode: "OLDER_HOUSING",
    label: "Older housing",
    source: "ACS 5-year",
    year: "2020-2024",
    unit: "percent of homes",
    meaning: "Share of homes built before 1980. Year built is housing age, not air conditioning.",
    fill: "quantity",
  },
];

export function mapModeMeta(mode: MapMode): MapModeMeta {
  return MAP_MODE_META.find((row) => row.mode === mode) ?? MAP_MODE_META[0]!;
}
