export type CapabilityId =
  | "signal_a"
  | "action"
  | "signal_b"
  | "place_search"
  | "geography_resolve"
  | "hosted_live"
  | "heatdose"
  | "afterheat"
  | "wbgt"
  | "probability";

export type CapabilityBandId = "on_this_surface" | "next_gated" | "in_development";

export type CapabilityStage =
  | "OBSERVE"
  | "CONTEXTUALIZE"
  | "EXPOSURE"
  | "PERSISTENCE"
  | "STRESS"
  | "ANTICIPATE"
  | "ACT"
  | "GEOGRAPHY"
  | "LIVE";

export type CapabilityRow = {
  id: CapabilityId;
  band: CapabilityBandId;
  stage: CapabilityStage;
  name: string;
  maturity: string;
  question: string;
  scope: string;
  numericPublic: false;
};

export type CapabilityModuleNote = {
  id: CapabilityId;
  name: string;
  what: string;
  rule: string;
};

export type HvaDecodeLine = {
  letter: "Heat" | "Vulnerability" | "Action";
  line: string;
};

export type CapabilityBand = {
  id: CapabilityBandId;
  title: string;
  rows: CapabilityRow[];
};

export type CapabilityExpansionView = {
  kicker: string;
  title: string;
  lead: string;
  spine: readonly string[];
  bands: CapabilityBand[];
  hva: readonly HvaDecodeLine[];
  notThisProduct: readonly string[];
  modulesIntro: string;
  modules: readonly CapabilityModuleNote[];
};
