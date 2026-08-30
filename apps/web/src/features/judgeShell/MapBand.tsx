import { useEffect, useState } from "react";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { createGeometryLoader } from "@/api/areaGeometry";
import { MapStage } from "@/features/map/MapStage";
import {
  catalogFromHistorical,
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
  resultAreaId: string | null;
  jobId: string | null;
  jobStatus: JobStatus | null;
  result: AnalysisResultStub | null;
  submitting: boolean;
  analysisTime?: string | null;
  onSelectedIdChange?: (geoid: string | null) => void;
};

function resultIsReady(status: JobStatus | null): boolean {
  return status === "complete" || status === "partial";
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

  return (
    <section className="judge-map" aria-label="25-zone analysis map">
      <MapStage
        layer={props.layer}
        ranking={props.ranking}
        areaId={props.areaId}
        resultAreaId={props.resultAreaId}
        jobId={props.jobId}
        jobStatus={props.jobStatus}
        result={props.result}
        submitting={props.submitting}
      />
      <JudgeMap
        lane="A"
        historical={catalog}
        enabled
        onSelectedIdChange={props.onSelectedIdChange}
      />
    </section>
  );
}
