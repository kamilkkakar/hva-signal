import type { BoundField } from "./availability";
import type { AnalysisAreaId } from "./analysisArea";
import type { MapModeId } from "./questions";

export type MapLegendStop = {
  readonly id: string;
  readonly label: string;
  readonly swatch: string | null;
};

export type MapModeModel = {
  readonly id: MapModeId;
  readonly title: string;
  readonly unit: string;
  readonly period: string;
  readonly baseline: string;
  readonly legend: readonly MapLegendStop[];
  readonly fill: BoundField<Readonly<Record<AnalysisAreaId, number>>>;
};

export type MapSelection = {
  readonly areaId: AnalysisAreaId | null;
};
