import {
  COPE_QUESTION,
  LIST_CAPTION,
  MAP_MODE_LABEL,
  NOT_A_SCORE,
  SCORE_QUESTION,
  SCORE_REFUSAL,
  VERIFY_QUESTION,
} from "./copy";
import { analysisAreaLabel, analysisAreaNumber } from "@/features/selectedAreaStory/identity";
import type { AnalysisAreaContextView, AreaContextDocument, MapMode } from "./types";

const WARRANT = /warrants closer review/i;

function withoutWarrant(lines: string[]): string[] {
  return lines.filter((line) => !WARRANT.test(line));
}

/** Context/inventory table. Never labels the columns as thermal or FortyGuard. */
export function listCaption(mode: MapMode): string {
  if (mode === "THERMAL") {
    return LIST_CAPTION;
  }
  return `${MAP_MODE_LABEL[mode]} values for each analysis area`;
}


export type AreaContextPanelView = {
  areaLabel: string;
  tractId: string;
  thermalStatus: "AVAILABLE" | "UNKNOWN";
  facts: Array<{ label: string; sentence: string; comparisonAllowed: boolean }>;
  preparedness: string[];
  uncertainty: string[];
  direction: string[];
  cope: string[];
  verify: string[];
  sources: string[];
  notAScore: string;
  scoreRefusal: string;
};

export type AreaContextListRow = {
  tractId: string;
  areaNumber: number | null;
  areaLabel: string;
  canopy: number | null;
  income: number | null;
  olderHousing: number | null;
  coolingStatus: string;
};

export function presentSelectedArea(
  view: AnalysisAreaContextView,
): AreaContextPanelView {
  return {
    areaLabel: view.area_label,
    tractId: view.census_tract_geoid,
    thermalStatus: view.thermal_evidence_status,
    facts: view.context_facts.map((fact) => ({
      label: fact.label,
      sentence: fact.plain_language_sentence,
      comparisonAllowed: fact.comparison_allowed,
    })),
    preparedness: view.preparedness,
    uncertainty: view.uncertainty_notes,
    direction: withoutWarrant(view.direction),
    cope: withoutWarrant(view.cope_characteristics),
    verify: view.verify_before_action,
    sources: view.sources,
    notAScore: NOT_A_SCORE,
    scoreRefusal: SCORE_REFUSAL,
  };
}

export function presentList(document: AreaContextDocument): AreaContextListRow[] {
  return document.zones.map((zone) => ({
    tractId: zone.census_tract_geoid,
    areaNumber: analysisAreaNumber(zone.census_tract_geoid),
    areaLabel: analysisAreaLabel(zone.census_tract_geoid) ?? zone.census_tract_geoid,
    canopy: zone.canopy_comparison_allowed ? zone.canopy_cover_share : null,
    income: zone.income_comparison_allowed ? zone.median_household_income : null,
    olderHousing: zone.older_housing_comparison_allowed
      ? zone.share_pre_1980_housing
      : null,
    coolingStatus: zone.cooling_site_status,
  }));
}

export function answersProductQuestions(view: AnalysisAreaContextView): {
  [COPE_QUESTION]: string[];
  [VERIFY_QUESTION]: string[];
  [SCORE_QUESTION]: false;
} {
  return {
    [COPE_QUESTION]: view.cope_characteristics.length
      ? view.cope_characteristics
      : view.context_facts.map((fact) => fact.plain_language_sentence),
    [VERIFY_QUESTION]: view.verify_before_action,
    [SCORE_QUESTION]: false,
  };
}

export function allowedMapModes(document: AreaContextDocument): MapMode[] {
  return document.map_modes.filter((mode) => {
    if (mode === "THERMAL") {
      return true;
    }
    const row = document.metric_quality.find((item) => {
      if (mode === "TREE_CANOPY") return item.kind === "canopy_cover_share";
      if (mode === "INCOME") return item.kind === "median_household_income";
      return item.kind === "share_pre_1980_housing";
    });
    return row?.comparison_layer_allowed === true;
  });
}
