import type {
  ProvenanceBannerLabel,
  ProvenanceDataStatus,
  ProvenanceSource,
} from "./types";

const ALLOWED_STATUS: Record<ProvenanceSource, ReadonlySet<ProvenanceDataStatus>> = {
  replay: new Set(["replay", "partial", "unavailable"]),
  fortyguard_cached: new Set(["cached", "partial", "unavailable"]),
  fortyguard_live: new Set(["live", "partial", "unavailable"]),
};

const PATH_STEM: Record<ProvenanceSource, Exclude<ProvenanceBannerLabel, "PARTIAL" | "UNAVAILABLE">> =
  {
    fortyguard_live: "FORTYGUARD LIVE",
    fortyguard_cached: "FORTYGUARD CACHED",
    replay: "REPLAY",
  };

export class SignalProvenanceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SignalProvenanceError";
  }
}

export function signalProvenanceBanner(input: {
  source?: ProvenanceSource | null;
  dataStatus?: ProvenanceDataStatus | null;
}): { banner: ProvenanceBannerLabel; pathStem: string | null } {
  if (input.dataStatus === "unavailable" || (input.source == null && input.dataStatus == null)) {
    return { banner: "UNAVAILABLE", pathStem: null };
  }
  if (input.source == null || input.dataStatus == null) {
    return { banner: "UNAVAILABLE", pathStem: null };
  }
  if (!ALLOWED_STATUS[input.source].has(input.dataStatus)) {
    throw new SignalProvenanceError(
      "illegal source/data_status pair; live does not beat cached",
    );
  }
  const pathStem = PATH_STEM[input.source];
  if (input.dataStatus === "partial") {
    return { banner: "PARTIAL", pathStem };
  }
  return { banner: pathStem, pathStem };
}

export function refuseCollapsedSourceTape(): never {
  throw new SignalProvenanceError(
    "A and B never collapse into one SourceTape, data_status, or thermal_source",
  );
}
