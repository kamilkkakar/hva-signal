import type { MapLayerState, RankingPresentation } from "@/utils/mapLayer";

type MapStageProps = {
  layer: MapLayerState;
  ranking: RankingPresentation;
};

export function MapStage({ layer, ranking }: MapStageProps) {
  const empty = ranking.state === "INSUFFICIENT_EVIDENCE";
  const thermalBlocked = !layer.allowPriorityChoropleth;

  return (
    <main className="map-stage" aria-label="Priority map">
      <div className="fiducial fiducial-nw" aria-hidden="true" />
      <div className="fiducial fiducial-ne" aria-hidden="true" />
      <div className="fiducial fiducial-sw" aria-hidden="true" />
      <div className="fiducial fiducial-se" aria-hidden="true" />

      <p className="map-label" data-testid="map-layer-label">
        Map layer: {layer.label}
      </p>

      {thermalBlocked && layer.message && (
        <p className="map-limitation" data-testid="thermal-diff-message">
          {layer.message}
        </p>
      )}

      {empty && (
        <p className="map-empty">
          {thermalBlocked
            ? "Neutral evidence state. No thermal ranking choropleth is shown."
            : "INSUFFICIENT_EVIDENCE. Submit a replay job when the backend is ready. Rankings will not be invented from an empty map."}
        </p>
      )}

      <p className="map-coords" aria-hidden="true">
        PLOTTER BED · NO TILESERVER · NO SYNTHETIC FIELD
      </p>
    </main>
  );
}
