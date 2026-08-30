import { signalProvenanceBanner, SignalProvenanceError } from "./banner";
import type { ProvenanceBannerLabel, PublicSignalProvenance, SignalKind } from "./types";

export const ANALYSIS_ZONE_COUNT = 25;

export type Level1EvidenceMode = "REPLAY" | "CACHED" | "LIVE" | "PARTIAL" | "UNAVAILABLE";

export type Level1SourceLabel =
  | "Replay fixture"
  | "Cached vendor target"
  | "Live vendor target"
  | "Unavailable";

export type CoverageCount = {
  valid: number;
  expected: number;
};

export type PublicLevel1 = {
  signalKind: SignalKind;
  title: string;
  source: Level1SourceLabel;
  observation: string;
  geography: string;
  coverage: string;
  evidenceMode: Level1EvidenceMode;
};

const SHA256_HEX = /\b[0-9a-f]{64}\b/i;
const PROTOCOL_STAMP =
  /PHX_ZTSI_REF_V1|PHX_DEMO_AOI_POLICY|US_CENSUS_TIGERLINE|sha256|request_fingerprint/i;

export function formatCoverage(coverage: CoverageCount | null | undefined): string {
  if (coverage == null) {
    return "unknown";
  }
  return `${coverage.valid} / ${coverage.expected}`;
}

export function evidenceModeFromBanner(banner: ProvenanceBannerLabel): Level1EvidenceMode {
  switch (banner) {
    case "FORTYGUARD LIVE":
      return "LIVE";
    case "FORTYGUARD CACHED":
      return "CACHED";
    case "REPLAY":
      return "REPLAY";
    case "PARTIAL":
      return "PARTIAL";
    case "UNAVAILABLE":
      return "UNAVAILABLE";
  }
}

export function sourceLabelFromBanner(
  banner: ProvenanceBannerLabel,
  pathStem: string | null,
): Level1SourceLabel {
  const stem = banner === "PARTIAL" ? pathStem : banner;
  if (stem === "FORTYGUARD CACHED") {
    return "Cached vendor target";
  }
  if (stem === "FORTYGUARD LIVE") {
    return "Live vendor target";
  }
  if (stem === "REPLAY") {
    return "Replay fixture";
  }
  return "Unavailable";
}

export function geographyLine(
  view: PublicSignalProvenance,
  areaId?: string | null,
): string {
  const id = areaId ?? "";
  const geometry = view.geometry_version ?? "";
  if (id === "phoenix-demo" || geometry.includes("PHX_DEMO")) {
    return "25-zone Phoenix demo AOI";
  }
  if (id.startsWith("us-place-") || geometry.includes("PLACE_")) {
    return "25-zone analysis window";
  }
  return "25-zone analysis geography";
}

export function observationLine(view: PublicSignalProvenance): string {
  const timezone = view.timezone ? ` · ${view.timezone}` : "";
  if (view.signal_kind === "historical_normalized") {
    const date = view.target_timestamp?.slice(0, 10);
    return date ? `${date} · 03:00 local${timezone}` : `03:00 local${timezone}`;
  }
  if (!view.target_timestamp) {
    return "Selected hour";
  }
  const date = view.target_timestamp.slice(0, 10);
  const hour = view.target_timestamp.slice(11, 13) || "00";
  return `${date} · ${hour}:00${timezone}`;
}

export function level1FieldTexts(view: PublicLevel1): string[] {
  return [view.source, view.observation, view.geography, view.coverage, view.evidenceMode];
}

export function assertLevel1HasNoShaWall(view: PublicLevel1): void {
  for (const text of level1FieldTexts(view)) {
    if (SHA256_HEX.test(text) || PROTOCOL_STAMP.test(text)) {
      throw new SignalProvenanceError("Level 1 must not expose SHA or protocol stamps");
    }
  }
}

export function projectLevel1(input: {
  view: PublicSignalProvenance;
  coverage?: CoverageCount | null;
  areaId?: string | null;
}): PublicLevel1 {
  const title =
    input.view.signal_kind === "historical_normalized"
      ? "Nighttime Historical Thermal Signal"
      : "Selected-Time Thermal Snapshot";
  const geography = geographyLine(input.view, input.areaId);
  const coverage = formatCoverage(input.coverage);
  const observation = observationLine(input.view);

  if (input.view.availability === "NOT_PREPARED") {
    const notPrepared: PublicLevel1 = {
      signalKind: input.view.signal_kind,
      title,
      source: "Unavailable",
      observation: observation || "03:00 local",
      geography,
      coverage,
      evidenceMode: "UNAVAILABLE",
    };
    assertLevel1HasNoShaWall(notPrepared);
    return notPrepared;
  }

  const { banner, pathStem } = signalProvenanceBanner({
    source: input.view.source,
    dataStatus: input.view.data_status,
  });
  const level1: PublicLevel1 = {
    signalKind: input.view.signal_kind,
    title,
    source: sourceLabelFromBanner(banner, pathStem),
    observation,
    geography,
    coverage,
    evidenceMode: evidenceModeFromBanner(banner),
  };
  assertLevel1HasNoShaWall(level1);
  return level1;
}
