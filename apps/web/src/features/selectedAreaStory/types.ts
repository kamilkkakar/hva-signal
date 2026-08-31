/** Client-side selected-area join. API thermal stays UNKNOWN. */

import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { AnalysisAreaContextView, AreaContextDocument, MapMode } from "@/features/areaContext/types";

export const ANALYSIS_AREA_GEOIDS = [
  "04013107401",
  "04013107500",
  "04013107601",
  "04013107602",
  "04013108802",
  "04013108602",
  "04013108601",
  "04013117100",
  "04013108501",
  "04013107700",
  "04013108502",
  "04013107404",
  "04013107403",
  "04013107402",
  "04013108902",
  "04013108901",
  "04013106703",
  "04013106600",
  "04013106501",
  "04013106502",
  "04013106400",
  "04013106702",
  "04013106701",
  "04013107800",
  "04013108400",
] as const;

export type AnalysisAreaGeoid = (typeof ANALYSIS_AREA_GEOIDS)[number];

export type ThermalProductStatus = "AVAILABLE" | "UNKNOWN";

export type Decision8State = "SUFFICIENT" | "INSUFFICIENT" | null;

export type ThermalAKind = "order_shown" | "order_withheld" | "absent";

export type ThermalAPane = {
  kind: ThermalAKind;
  hasRealPane: boolean;
  decision8: Decision8State;
  q_A: number | null;
  orderShown: boolean;
  source: "fortyguard_replay";
};

export type ThermalBPane = {
  kind: "cached" | "missing";
  wording: "AVAILABLE NOW — CACHED EVIDENCE";
  temperatureC: number | null;
  coverage: "25/25";
  clock: "2025-07-15 03:00";
  timezone: "America/Phoenix";
  source: "fortyguard_cached";
  notQA: true;
  notDecision8: true;
  notRank: true;
};

export type PreparednessStatus =
  | "IDENTIFIED"
  | "NOT_IDENTIFIED_IN_DATASET"
  | "UNKNOWN";

export type DirectionRuleId = "R0" | "R1" | "R2" | "R3" | "R4" | "R5";

export type DirectionRule = {
  id: DirectionRuleId;
  text: string;
};

export type StoryFact = {
  kind: string;
  label: string;
  sentence: string;
  sourceFamily: "acs" | "canopy";
  comparisonAllowed: boolean;
  qualityStatus: string;
};

export type MapModeMeta = {
  mode: MapMode;
  label: string;
  source: string;
  year: string;
  unit: string;
  meaning: string;
  fill: "job_ranking" | "quantity" | "none";
};

export type SelectedAreaIdentity = {
  geoid: string | null;
  areaNumber: number | null;
  label: string | null;
  inCatalog: boolean;
  secondaryLabel?: string | null;
  nameSource?: string | null;
};

export type SelectedAreaDecisionStory = {
  identity: SelectedAreaIdentity;
  questions: {
    thermal: {
      label: string;
      status: ThermalProductStatus;
      a: ThermalAPane;
      b: ThermalBPane;
    };
    different: {
      label: string;
      facts: StoryFact[];
    };
    support: {
      label: string;
      status: PreparednessStatus;
      sentences: string[];
      disclaimer: string;
    };
    verify: {
      label: string;
      rules: DirectionRule[];
    };
  };
  sources: {
    fortyguard: string[];
    acs: string[];
    canopy: string[];
    mag: string[];
  };
  mapModes: MapModeMeta[];
  combined_score_authorized: false;
  vulnerability_score_authorized: false;
};

export type ComposeInput = {
  selectedGeoid?: string | null;
  result?: AnalysisResultStub | null;
  context?: AnalysisAreaContextView | null;
  document?: AreaContextDocument | null;
};
