/** TEST_ONLY fixture. Not imported by production routes. */
import type { AnalysisArea } from "@/contracts";
import { analysisAreaId, analysisAreaLabel, ANALYSIS_AREA_COUNT } from "@/contracts";
import { TEST_ONLY } from "./TEST_ONLY";

export const TEST_ONLY_AREAS: readonly AnalysisArea[] = Array.from(
  { length: ANALYSIS_AREA_COUNT },
  (_, index) => {
    const ordinal = index + 1;
    return {
      id: analysisAreaId(ordinal),
      ordinal,
      primaryLabel: analysisAreaLabel(ordinal),
      censusTractGeoid: `TEST-ONLY-${String(ordinal).padStart(11, "0")}`,
    };
  },
);

export const TEST_ONLY_AREA_MARK = TEST_ONLY;
