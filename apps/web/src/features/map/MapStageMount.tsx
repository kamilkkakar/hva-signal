import { lazy, Suspense } from "react";
import type { MapStageProps } from "./MapStage";

const MapStage = lazy(() =>
  import("./MapStage").then((mod) => ({ default: mod.MapStage })),
);

function MapStageFallback() {
  return (
    <main
      className="map-stage"
      aria-label="Analysis map"
      data-testid="map-stage"
      data-map-state="idle"
      data-geometry-feature-count="0"
      data-ranked-feature-count="0"
    >
      <div className="map-canvas" data-testid="map-canvas" />
      <div className="fiducial fiducial-nw" aria-hidden="true" />
      <div className="fiducial fiducial-ne" aria-hidden="true" />
      <div className="fiducial fiducial-sw" aria-hidden="true" />
      <div className="fiducial fiducial-se" aria-hidden="true" />
      <div className="map-overlay">
        <p className="map-label" data-testid="map-layer-label">
          Map layer: loading plotter
        </p>
        <p className="map-empty">Loading plotter bed.</p>
        <p className="map-coords" aria-hidden="true">
          PLOTTER BED · NO TILESERVER · NO SYNTHETIC FIELD
        </p>
      </div>
    </main>
  );
}

/** Defers MapLibre (~1 MiB) until after command-center chrome can paint. */
export function MapStageMount(props: MapStageProps) {
  return (
    <Suspense fallback={<MapStageFallback />}>
      <MapStage {...props} />
    </Suspense>
  );
}
