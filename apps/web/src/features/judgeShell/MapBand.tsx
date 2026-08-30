import { useEffect, useState } from "react";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { createGeometryLoader } from "@/api/areaGeometry";
import {
  catalogFromHistorical,
  rankedFillCount,
  type InteractionCatalog,
} from "@/features/mapInteraction";
import type { JobStatus } from "@/types";
import { bindGeometryToAnalysis } from "@/utils/geometryJoin";
import type { MapLayerState, RankingPresentation } from "@/utils/mapLayer";
import { JudgeMap } from "./map/JudgeMap";

type MapBandProps = {
  layer: MapLayerState;
  ranking: RankingPresentation;
  areaId: string | null;
  jobId: string | null;
  jobStatus: JobStatus | null;
  result: AnalysisResultStub | null;
  submitting: boolean;
  analysisTime?: string | null;
};

function resultIsReady(status: JobStatus | null): boolean {
  return status === "complete" || status === "partial";
}

function exploreMapState(input: {
  submitting: boolean;
  jobStatus: JobStatus | null;
  catalog: InteractionCatalog | null;
  rankingState: RankingPresentation["state"];
}): "idle" | "loading" | "sufficient" | "insufficient" {
  if (input.submitting) {
    return "loading";
  }
  if (!resultIsReady(input.jobStatus)) {
    return "idle";
  }
  if (!input.catalog) {
    return "loading";
  }
  return input.rankingState === "READY" ? "sufficient" : "insufficient";
}

export function MapBand(props: MapBandProps) {
  const [catalog, setCatalog] = useState<InteractionCatalog | null>(null);

  useEffect(() => {
    const areaId = props.areaId;
    const result = props.result;
    if (
      !areaId ||
      !props.jobId ||
      !resultIsReady(props.jobStatus) ||
      !result
    ) {
      setCatalog(null);
      return;
    }
    const loader = createGeometryLoader();
    let cancelled = false;
    void loader
      .load(areaId)
      .then((outcome) => {
        if (cancelled || outcome.stale) {
          return;
        }
        const bound = bindGeometryToAnalysis({
          geometry: outcome.payload,
          requestAreaId: areaId,
          result,
        });
        if (!bound.ok) {
          setCatalog(null);
          return;
        }
        setCatalog(
          catalogFromHistorical({
            features: bound.collection.features,
            analysisTime: props.analysisTime,
            dataMode: "replay",
            fillAuthorized: props.ranking.state === "READY",
          }),
        );
      })
      .catch(() => {
        if (!cancelled) {
          setCatalog(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [
    props.areaId,
    props.analysisTime,
    props.jobId,
    props.jobStatus,
    props.ranking.state,
    props.result,
  ]);

  const mapState = exploreMapState({
    submitting: props.submitting,
    jobStatus: props.jobStatus,
    catalog,
    rankingState: props.ranking.state,
  });

  return (
    <section
      className="judge-map"
      aria-label={props.layer.label}
      data-testid="map-stage"
      data-layout="map-primary"
      data-map-state={mapState}
      data-ranked-feature-count={String(rankedFillCount(catalog))}
      data-layer-label={props.layer.label}
    >
      <JudgeMap lane="A" historical={catalog} enabled />
    </section>
  );
}
