import type { BoundField } from "./availability";
import type { ChartKind } from "./questions";

/** Every temporal visual must carry these chrome fields. No unlabeled sparkline. */
export type ChartChrome = {
  readonly title: string;
  readonly unit: string;
  readonly period: string;
  readonly baseline: string;
  readonly coverage: string;
  readonly source: string;
};

export type SeriesPoint = {
  readonly x: string;
  readonly y: number;
  readonly label?: string;
};

export type TemporalSeries = {
  readonly kind: ChartKind;
  readonly chrome: ChartChrome;
  readonly points: BoundField<readonly SeriesPoint[]>;
};

export type GroupedSeries = {
  readonly kind: ChartKind;
  readonly chrome: ChartChrome;
  readonly groups: BoundField<
    readonly {
      readonly id: string;
      readonly label: string;
      readonly points: readonly SeriesPoint[];
    }[]
  >;
};

export type TemporalChartModel = TemporalSeries | GroupedSeries;

export function isGroupedSeries(model: TemporalChartModel): model is GroupedSeries {
  return "groups" in model;
}
