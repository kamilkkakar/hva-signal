/** Unified zone record the map, hover chip, detail panel, and table all read. */

export type MapLayerKind =
  | "none"
  | "aoi_outline"
  | "historical_ordering"
  | "selected_time_snapshot";

export type InteractionValueKind = "q_A" | "order" | "mean_c" | "none";

export type ProductSourceLabel =
  | "REPLAY"
  | "CACHED"
  | "LIVE"
  | "PARTIAL"
  | "UNAVAILABLE";

export type InteractionZone = {
  geoid: string;
  zone_id: string;
  label: string;
  value_display: string;
  value_kind: InteractionValueKind;
  coverage: string;
  time_label: string;
  source_label: ProductSourceLabel;
  has_semantic_fill: boolean;
  q_A_display: string | null;
  q_A_value: number | null;
  relative_order: number | null;
  relative_order_of: number | null;
  observation_label: string;
  source_story: string;
  position_shown: boolean;
};

export type InteractionFeature = {
  type: "Feature";
  properties: Record<string, unknown> & { GEOID: string; zone_id: string };
  geometry: unknown;
};

export type InteractionCollection = {
  type: "FeatureCollection";
  features: InteractionFeature[];
};

export type InteractionCatalog = {
  kind: MapLayerKind;
  layer_title: string;
  meaning: string;
  time_label: string;
  source_label: ProductSourceLabel;
  fill_authorized: boolean;
  zones: InteractionZone[];
  collection: InteractionCollection;
};

export type InteractionState = {
  hoverId: string | null;
  selectedId: string | null;
  layerActive: boolean;
  fitGeneration: number;
};

export type InteractionEvent =
  | { type: "hover"; geoid: string | null }
  | { type: "select"; geoid: string }
  | { type: "clear_selection" }
  | { type: "clear_layer" }
  | { type: "restore_layer" }
  | { type: "fit_aoi" }
  | { type: "reset_aoi" };

export type HoverCard = {
  geoid: string;
  label: string;
  value_display: string;
  line: string;
  primary_evidence: string;
};

export type ZoneDetail = {
  geoid: string;
  label: string;
  value_display: string;
  coverage: string;
  time_label: string;
  source_label: ProductSourceLabel;
  observation_label: string;
  source_story: string;
  position_meaning: string;
  position_shown: boolean;
  position_pct: number | null;
  relative_order_line: string | null;
  q_A_display: string | null;
};

export type LegendItem = {
  id: string;
  label: string;
  meaning: string;
  swatch: string | null;
};

export type InteractionTableRow = {
  geoid: string;
  label: string;
  value_display: string;
  coverage: string;
  time_label: string;
  source_label: ProductSourceLabel;
};

export type InteractionVisualState =
  | "gated_off"
  | "empty"
  | "outline_only"
  | "semantic"
  | "layer_cleared";

export type MapInteractionView = {
  gated: boolean;
  visualState: InteractionVisualState;
  canvasAllowed: boolean;
  layerTitle: string;
  meaningCopy: string;
  legend: LegendItem[];
  hover: HoverCard | null;
  detail: ZoneDetail | null;
  tableRows: InteractionTableRow[];
  selectedId: string | null;
  hoverId: string | null;
  layerActive: boolean;
  fitGeneration: number;
  canFitAoi: boolean;
  canClearLayer: boolean;
  canRestoreLayer: boolean;
  announce: string;
  decorative: false;
};
