import { MapStage } from "@/features/map/MapStage";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import type { MapLayerState, RankingPresentation } from "@/utils/mapLayer";

type MapBandProps = {
  layer: MapLayerState;
  ranking: RankingPresentation;
  areaId: string | null;
  resultAreaId: string | null;
  jobId: string | null;
  jobStatus: JobStatus | null;
  result: AnalysisResultStub | null;
  submitting: boolean;
};

export function MapBand(props: MapBandProps) {
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
    </section>
  );
}
