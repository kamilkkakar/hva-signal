import { ANALYSIS_AREA_COUNT, analysisAreaId, type AnalysisAreaId } from "@/contracts";

export type AreaCell = {
  readonly id: AnalysisAreaId;
  readonly ordinal: number;
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
};

const COLS = 5;
const CELL_W = 64;
const CELL_H = 48;
const GAP = 4;
const ORIGIN_X = 16;
const ORIGIN_Y = 16;

export function areaCells(): readonly AreaCell[] {
  return Array.from({ length: ANALYSIS_AREA_COUNT }, (_, index) => {
    const ordinal = index + 1;
    const col = index % COLS;
    const row = Math.floor(index / COLS);
    const jitterX = ((ordinal * 17) % 5) - 2;
    const jitterY = ((ordinal * 11) % 5) - 2;
    return {
      id: analysisAreaId(ordinal),
      ordinal,
      x: ORIGIN_X + col * (CELL_W + GAP) + jitterX,
      y: ORIGIN_Y + row * (CELL_H + GAP) + jitterY,
      w: CELL_W,
      h: CELL_H,
    };
  });
}

export const MAP_VIEWBOX = "0 0 360 280";
