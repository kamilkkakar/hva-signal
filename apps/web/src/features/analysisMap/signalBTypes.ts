/** Public Signal B snapshot shape. Absolute °C only. No rank, quantile, or Decision 8. */

export type SignalBCoverageStatus = "valid" | "missing" | (string & {});

export type SignalBSnapshotZone = {
  zone_id: string;
  mean_temperature_c: number | null;
  tile_count?: number;
  coverage_status: string;
};

export type SignalBSnapshot = {
  units: "celsius";
  aggregation_method: "centroid_within_mean";
  spatial_resolution: "zone";
  user_facing_tile_map: false;
  target_timestamp?: string;
  timezone?: string;
  zones: SignalBSnapshotZone[];
  expected_zone_count?: number | null;
  valid_zone_count?: number | null;
  missing_zone_ids?: string[];
  temperature_min_c?: number | null;
  temperature_max_c?: number | null;
};

export type SignalBGeometryFeature = {
  type: "Feature";
  properties: Record<string, unknown> | null;
  geometry: unknown;
};

export type SignalBGeometryCollection = {
  type: "FeatureCollection";
  features: SignalBGeometryFeature[];
};

export type SignalBBoundProperties = {
  GEOID: string;
  zone_id: string;
  mean_temperature_c: number | null;
  coverage_status: string;
  display_temperature: string;
  has_valid_temperature: boolean;
  units: "celsius";
  aggregation_method: "centroid_within_mean";
};

export type SignalBBoundFeature = {
  type: "Feature";
  properties: SignalBBoundProperties;
  geometry: unknown;
};

export type SignalBBoundCollection = {
  type: "FeatureCollection";
  features: SignalBBoundFeature[];
};

export type SignalBMapAvailability =
  | "idle"
  | "fetching"
  | "unavailable"
  | "partial"
  | "ready";

export type SignalBMapVisualState =
  | "gated_off"
  | "idle"
  | "loading"
  | "ready"
  | "partial"
  | "unavailable"
  | "error";

export type SignalBTableRow = {
  zone_id: string;
  mean_temperature_c: number | null;
  display_temperature: string;
  coverage_status: string;
  units: "celsius";
};

export type SignalBHover = {
  zone_id: string;
  display_temperature: string;
  coverage_status: string;
  units: "celsius";
  aggregation_method: "centroid_within_mean";
};

export type SignalBSnapshotFacts = {
  temperature_min_c: number | null;
  temperature_max_c: number | null;
  factText: string | null;
};

export type SignalBFillPaint = {
  "fill-color": string;
  "fill-opacity": unknown;
};

export type SignalBLinePaint = {
  "line-color": string;
  "line-width": number;
};

export type SignalBMapPresentation = {
  layerTitle: "Selected-Time Thermal Snapshot";
  visualState: SignalBMapVisualState;
  fillPaint: SignalBFillPaint;
  linePaint: SignalBLinePaint;
  collection: SignalBBoundCollection;
  tableRows: SignalBTableRow[];
  snapshotFacts: SignalBSnapshotFacts;
  autoContrastBanner: null;
  meaningCopy: string;
  methodologyCopy: string;
  stretchCopy: string;
  message: string | null;
  outlineCount: number;
  validFillCount: number;
};
