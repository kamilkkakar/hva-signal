import type { BoundField } from "./availability";
import type { GroupedSeries } from "./temporal";

export type InterventionModel = {
  readonly treatedLabel: string;
  readonly comparisonLabel: string;
  readonly coverage: BoundField<string>;
  readonly period: BoundField<string>;
  readonly chart: GroupedSeries;
  readonly efficacyClaim: false;
};
