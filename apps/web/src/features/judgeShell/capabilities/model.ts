import {
  ACTION_MATURITY,
  ACTION_NAME,
  ACTION_QUESTION,
  ACTION_RULE,
  ACTION_SCOPE,
  ACTION_WHAT,
  AFTERHEAT_MATURITY,
  AFTERHEAT_NAME,
  AFTERHEAT_QUESTION,
  AFTERHEAT_RULE,
  AFTERHEAT_SCOPE,
  AFTERHEAT_WHAT,
  BAND_IN_DEVELOPMENT,
  BAND_NEXT_GATED,
  BAND_ON_THIS_SURFACE,
  CAPABILITY_KICKER,
  CAPABILITY_LEAD,
  CAPABILITY_SPINE,
  CAPABILITY_TITLE,
  GEOGRAPHY_MATURITY,
  GEOGRAPHY_NAME,
  GEOGRAPHY_QUESTION,
  GEOGRAPHY_RULE,
  GEOGRAPHY_SCOPE,
  GEOGRAPHY_WHAT,
  HEATDOSE_MATURITY,
  HEATDOSE_NAME,
  HEATDOSE_QUESTION,
  HEATDOSE_RULE,
  HEATDOSE_SCOPE,
  HEATDOSE_WHAT,
  HOSTED_LIVE_MATURITY,
  HOSTED_LIVE_NAME,
  HOSTED_LIVE_QUESTION,
  HOSTED_LIVE_RULE,
  HOSTED_LIVE_SCOPE,
  HOSTED_LIVE_WHAT,
  HVA_ACTION_LINE,
  HVA_HEAT_LINE,
  HVA_VULNERABILITY_LINE,
  MODULES_INTRO,
  NOT_THIS_PRODUCT,
  PLACE_SEARCH_MATURITY,
  PLACE_SEARCH_NAME,
  PLACE_SEARCH_QUESTION,
  PLACE_SEARCH_RULE,
  PLACE_SEARCH_SCOPE,
  PLACE_SEARCH_WHAT,
  PROBABILITY_MATURITY,
  PROBABILITY_NAME,
  PROBABILITY_QUESTION,
  PROBABILITY_RULE,
  PROBABILITY_SCOPE,
  PROBABILITY_WHAT,
  SIGNAL_A_MATURITY,
  SIGNAL_A_NAME,
  SIGNAL_A_QUESTION,
  SIGNAL_A_RULE,
  SIGNAL_A_SCOPE,
  SIGNAL_A_WHAT,
  SIGNAL_B_MATURITY,
  SIGNAL_B_NAME,
  SIGNAL_B_QUESTION,
  SIGNAL_B_RULE,
  SIGNAL_B_SCOPE,
  SIGNAL_B_WHAT,
  WBGT_MATURITY,
  WBGT_NAME,
  WBGT_QUESTION,
  WBGT_RULE,
  WBGT_SCOPE,
  WBGT_WHAT,
} from "./copy";
import type {
  CapabilityBand,
  CapabilityBandId,
  CapabilityExpansionView,
  CapabilityId,
  CapabilityModuleNote,
  CapabilityRow,
  HvaDecodeLine,
} from "./types";

const BAND_TITLE: Record<CapabilityBandId, string> = {
  on_this_surface: BAND_ON_THIS_SURFACE,
  next_gated: BAND_NEXT_GATED,
  in_development: BAND_IN_DEVELOPMENT,
};

const BAND_ORDER: readonly CapabilityBandId[] = [
  "on_this_surface",
  "next_gated",
  "in_development",
];

export const CAPABILITY_ROWS: readonly CapabilityRow[] = [
  {
    id: "signal_a",
    band: "on_this_surface",
    stage: "CONTEXTUALIZE",
    name: SIGNAL_A_NAME,
    maturity: SIGNAL_A_MATURITY,
    question: SIGNAL_A_QUESTION,
    scope: SIGNAL_A_SCOPE,
    numericPublic: false,
  },
  {
    id: "action",
    band: "on_this_surface",
    stage: "ACT",
    name: ACTION_NAME,
    maturity: ACTION_MATURITY,
    question: ACTION_QUESTION,
    scope: ACTION_SCOPE,
    numericPublic: false,
  },
  {
    id: "signal_b",
    band: "on_this_surface",
    stage: "OBSERVE",
    name: SIGNAL_B_NAME,
    maturity: SIGNAL_B_MATURITY,
    question: SIGNAL_B_QUESTION,
    scope: SIGNAL_B_SCOPE,
    numericPublic: false,
  },
  {
    id: "place_search",
    band: "next_gated",
    stage: "GEOGRAPHY",
    name: PLACE_SEARCH_NAME,
    maturity: PLACE_SEARCH_MATURITY,
    question: PLACE_SEARCH_QUESTION,
    scope: PLACE_SEARCH_SCOPE,
    numericPublic: false,
  },
  {
    id: "geography_resolve",
    band: "next_gated",
    stage: "GEOGRAPHY",
    name: GEOGRAPHY_NAME,
    maturity: GEOGRAPHY_MATURITY,
    question: GEOGRAPHY_QUESTION,
    scope: GEOGRAPHY_SCOPE,
    numericPublic: false,
  },
  {
    id: "hosted_live",
    band: "next_gated",
    stage: "LIVE",
    name: HOSTED_LIVE_NAME,
    maturity: HOSTED_LIVE_MATURITY,
    question: HOSTED_LIVE_QUESTION,
    scope: HOSTED_LIVE_SCOPE,
    numericPublic: false,
  },
  {
    id: "heatdose",
    band: "in_development",
    stage: "EXPOSURE",
    name: HEATDOSE_NAME,
    maturity: HEATDOSE_MATURITY,
    question: HEATDOSE_QUESTION,
    scope: HEATDOSE_SCOPE,
    numericPublic: false,
  },
  {
    id: "afterheat",
    band: "in_development",
    stage: "PERSISTENCE",
    name: AFTERHEAT_NAME,
    maturity: AFTERHEAT_MATURITY,
    question: AFTERHEAT_QUESTION,
    scope: AFTERHEAT_SCOPE,
    numericPublic: false,
  },
  {
    id: "wbgt",
    band: "in_development",
    stage: "STRESS",
    name: WBGT_NAME,
    maturity: WBGT_MATURITY,
    question: WBGT_QUESTION,
    scope: WBGT_SCOPE,
    numericPublic: false,
  },
  {
    id: "probability",
    band: "in_development",
    stage: "ANTICIPATE",
    name: PROBABILITY_NAME,
    maturity: PROBABILITY_MATURITY,
    question: PROBABILITY_QUESTION,
    scope: PROBABILITY_SCOPE,
    numericPublic: false,
  },
];

export const HVA_DECODE: readonly HvaDecodeLine[] = [
  { letter: "Heat", line: HVA_HEAT_LINE },
  { letter: "Vulnerability", line: HVA_VULNERABILITY_LINE },
  { letter: "Action", line: HVA_ACTION_LINE },
];

export const CAPABILITY_MODULES: readonly CapabilityModuleNote[] = [
  { id: "signal_a", name: SIGNAL_A_NAME, what: SIGNAL_A_WHAT, rule: SIGNAL_A_RULE },
  { id: "action", name: ACTION_NAME, what: ACTION_WHAT, rule: ACTION_RULE },
  { id: "signal_b", name: SIGNAL_B_NAME, what: SIGNAL_B_WHAT, rule: SIGNAL_B_RULE },
  {
    id: "place_search",
    name: PLACE_SEARCH_NAME,
    what: PLACE_SEARCH_WHAT,
    rule: PLACE_SEARCH_RULE,
  },
  {
    id: "geography_resolve",
    name: GEOGRAPHY_NAME,
    what: GEOGRAPHY_WHAT,
    rule: GEOGRAPHY_RULE,
  },
  {
    id: "hosted_live",
    name: HOSTED_LIVE_NAME,
    what: HOSTED_LIVE_WHAT,
    rule: HOSTED_LIVE_RULE,
  },
  { id: "heatdose", name: HEATDOSE_NAME, what: HEATDOSE_WHAT, rule: HEATDOSE_RULE },
  { id: "afterheat", name: AFTERHEAT_NAME, what: AFTERHEAT_WHAT, rule: AFTERHEAT_RULE },
  { id: "wbgt", name: WBGT_NAME, what: WBGT_WHAT, rule: WBGT_RULE },
  {
    id: "probability",
    name: PROBABILITY_NAME,
    what: PROBABILITY_WHAT,
    rule: PROBABILITY_RULE,
  },
];

const UNPUBLISHED_NUMERIC_IDS: ReadonlySet<CapabilityId> = new Set([
  "heatdose",
  "afterheat",
  "wbgt",
  "probability",
]);

export function capabilityRow(id: CapabilityId): CapabilityRow {
  const row = CAPABILITY_ROWS.find((item) => item.id === id);
  if (!row) {
    throw new Error(`Unknown capability ${id}`);
  }
  return row;
}

export function groupCapabilityBands(): CapabilityBand[] {
  return BAND_ORDER.map((id) => ({
    id,
    title: BAND_TITLE[id],
    rows: CAPABILITY_ROWS.filter((row) => row.band === id),
  }));
}

export function presentCapabilityExpansion(): CapabilityExpansionView {
  return {
    kicker: CAPABILITY_KICKER,
    title: CAPABILITY_TITLE,
    lead: CAPABILITY_LEAD,
    spine: CAPABILITY_SPINE,
    bands: groupCapabilityBands(),
    hva: HVA_DECODE,
    notThisProduct: NOT_THIS_PRODUCT,
    modulesIntro: MODULES_INTRO,
    modules: CAPABILITY_MODULES,
  };
}

export function isUnpublishedNumericCapability(id: CapabilityId): boolean {
  return UNPUBLISHED_NUMERIC_IDS.has(id);
}
