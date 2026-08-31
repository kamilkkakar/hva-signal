import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { AreaGeometryPayload } from "@/api/areaGeometry";
import { phoenixDemoCachedSelectedTime } from "@/features/judgeShell/signalB/cachedPhoenix";
import { catalogFromSnapshot } from "@/features/mapInteraction/fromSnapshot";
import type { InteractionCatalog } from "@/features/mapInteraction";
import type { JobStatus } from "@/types";
import type { RankingPresentation } from "@/utils/mapLayer";

export function resultIsReady(status: JobStatus | null): boolean {
  return status === "complete" || status === "partial";
}

export function exploreMapState(input: {
  submitting: boolean;
  jobStatus: JobStatus | null;
  catalog: InteractionCatalog | null;
  rankingState: RankingPresentation["state"];
}): "idle" | "loading" | "sufficient" | "insufficient" {
  if (!input.catalog) {
    if (input.submitting || resultIsReady(input.jobStatus)) {
      return "loading";
    }
    return "idle";
  }
  if (input.catalog.kind === "selected_time_snapshot" && input.catalog.fill_authorized) {
    return "sufficient";
  }
  if (!resultIsReady(input.jobStatus)) {
    if (input.jobStatus === "failed" || input.jobStatus === "unknown_job") {
      return "insufficient";
    }
    return "loading";
  }
  return input.rankingState === "READY" ? "sufficient" : "insufficient";
}

/**
 * Primary judge map catalog: real Phoenix polygon geometry joined to cached
 * Signal B selected-time zone means. Ranking withheld does not block thermal fill.
 */
export function buildJudgeMapCatalog(input: {
  geometry: AreaGeometryPayload | null;
  areaId: string;
  result: AnalysisResultStub | null;
  jobStatus: JobStatus | null;
  analysisTime?: string | null;
}): InteractionCatalog | null {
  if (!input.geometry) {
    return null;
  }
  const snapshot = phoenixDemoCachedSelectedTime();
  return catalogFromSnapshot({
    zones: snapshot.zones.map((zone) => ({
      zone_id: zone.zone_id,
      mean_temperature_c: zone.mean_temperature_c,
      coverage_status: zone.coverage_status,
    })),
    geometry: input.geometry.collection,
    targetTimestamp: snapshot.target_timestamp,
    timezone: snapshot.timezone,
    source: snapshot.provenance_source,
    dataStatus: snapshot.data_status,
  });
}
