export type ResultStoryKind =
  | "sufficient"
  | "insufficient"
  | "not_evaluated"
  | "awaiting"
  | "failed";

export type ResultStoryContextItem = {
  label: string;
  value: string;
};

export type HowDeterminedView = {
  historicalComparison: string;
  spatialDifferentiation: string;
  observedSeparation: string | null;
  minimumSeparation: string | null;
};

export type ResultStoryView = {
  kind: ResultStoryKind;
  stamp: string;
  headline: string;
  summary: string;
  context: ResultStoryContextItem[];
  supports: string;
  doesNotEstablish: string;
  how: HowDeterminedView;
};
