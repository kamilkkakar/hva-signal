import { SignalProvenanceError } from "./banner";
import type { Level1SourceLabel } from "./level1";
import type { SignalKind } from "./types";

const SHA256_HEX = /\b[0-9a-f]{64}\b/i;

export type SelectedZoneCoverage = "valid" | "missing" | "unknown";

export type SelectedZoneLevel1 = {
  zoneId: string;
  coverage: SelectedZoneCoverage;
  observation: string;
  source: Level1SourceLabel;
  signalKind: SignalKind;
};

export function selectedZoneLevel1(input: SelectedZoneLevel1): SelectedZoneLevel1 {
  const texts = [input.zoneId, input.coverage, input.observation, input.source];
  for (const text of texts) {
    if (SHA256_HEX.test(text)) {
      throw new SignalProvenanceError("Selected-zone Level 1 must not expose SHA");
    }
  }
  return {
    zoneId: input.zoneId,
    coverage: input.coverage,
    observation: input.observation,
    source: input.source,
    signalKind: input.signalKind,
  };
}
