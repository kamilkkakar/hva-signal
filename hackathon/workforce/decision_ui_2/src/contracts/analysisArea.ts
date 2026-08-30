/** Analysis areas are the primary spatial unit. GEOID is secondary only. */

export const ANALYSIS_AREA_COUNT = 25 as const;

export type AnalysisAreaId = `area-${number}`;

export type AnalysisArea = {
  readonly id: AnalysisAreaId;
  readonly ordinal: number;
  readonly primaryLabel: string;
  /** Secondary identifier. Null on the public surface until geography is bound. */
  readonly censusTractGeoid: string | null;
};

export function analysisAreaId(ordinal: number): AnalysisAreaId {
  if (ordinal < 1 || ordinal > ANALYSIS_AREA_COUNT) {
    throw new Error(`Analysis area ordinal out of range: ${ordinal}`);
  }
  return `area-${ordinal}`;
}

export function analysisAreaLabel(ordinal: number): string {
  return `Analysis area ${ordinal}`;
}

export function buildAnalysisAreas(): readonly AnalysisArea[] {
  return Array.from({ length: ANALYSIS_AREA_COUNT }, (_, index) => {
    const ordinal = index + 1;
    return {
      id: analysisAreaId(ordinal),
      ordinal,
      primaryLabel: analysisAreaLabel(ordinal),
      censusTractGeoid: null,
    };
  });
}
