import type { JobStatus, ThermalDataSource } from "@/types";

export type SourceBannerLabel =
  | "FORTYGUARD LIVE"
  | "FORTYGUARD CACHED"
  | "REPLAY"
  | "PARTIAL"
  | "UNAVAILABLE";

export const SOURCE_TAPE_SEGMENTS = [
  { id: "live", label: "LIVE", banner: "FORTYGUARD LIVE" },
  { id: "cached", label: "CACHED", banner: "FORTYGUARD CACHED" },
  { id: "replay", label: "REPLAY", banner: "REPLAY" },
  { id: "partial", label: "PARTIAL", banner: "PARTIAL" },
  { id: "unavailable", label: "UNAVAILABLE", banner: "UNAVAILABLE" },
] as const;

export function sourceBannerLabel(input: {
  status: JobStatus | null;
  thermalSource?: ThermalDataSource | null;
  dataStatus?: string | null;
}): SourceBannerLabel {
  if (input.status === "partial" || input.dataStatus === "partial") {
    return "PARTIAL";
  }
  if (input.dataStatus === "unavailable") {
    return "UNAVAILABLE";
  }
  if (input.dataStatus === "live" || input.thermalSource === "fortyguard_live") {
    return "FORTYGUARD LIVE";
  }
  if (input.dataStatus === "cached" || input.thermalSource === "fortyguard_cached") {
    return "FORTYGUARD CACHED";
  }
  if (input.dataStatus === "replay" || input.thermalSource === "replay") {
    return "REPLAY";
  }
  return "UNAVAILABLE";
}
