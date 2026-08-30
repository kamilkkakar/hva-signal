import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { AreaGeometryPayload } from "@/api/areaGeometry";
import { catalogFromHistorical, type InteractionCatalog } from "@/features/mapInteraction";
import { bindGeometryToAnalysis } from "@/utils/geometryJoin";
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
  if (!resultIsReady(input.jobStatus)) {
    if (input.jobStatus === "failed" || input.jobStatus === "unknown_job") {
      return "insufficient";
    }
    return "loading";
  }
  return input.rankingState === "READY" ? "sufficient" : "insufficient";
}

export function buildJudgeMapCatalog(input: {
  geometry: AreaGeometryPayload | null;
  areaId: string;
  result: AnalysisResultStub | null;
  jobStatus: JobStatus | null;
  analysisTime?: string | null;
  fillAuthorized: boolean;
}): InteractionCatalog | null {
  if (!input.geometry) {
    return null;
  }
  if (resultIsReady(input.jobStatus) && input.result) {
    const bound = bindGeometryToAnalysis({
      geometry: input.geometry,
      requestAreaId: input.areaId,
      result: input.result,
    });
    if (bound.ok) {
      return catalogFromHistorical({
        features: bound.collection.features,
        analysisTime: input.analysisTime,
        dataMode: "replay",
        fillAuthorized: input.fillAuthorized,
      });
    }
  }
  return catalogFromHistorical({
    features: input.geometry.collection.features,
    analysisTime: input.analysisTime,
    dataMode: "replay",
    fillAuthorized: false,
  });
}
