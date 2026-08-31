import { useEffect, useMemo, useState } from "react";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { createGeometryLoader, type AreaGeometryPayload } from "@/api/areaGeometry";
import {
  MapModeTabs,
  bindMapModeCatalog,
  contextFillCount,
  type MapMode,
  type ZoneMapProperties,
} from "@/features/areaContext";
import { rankedFillCount } from "@/features/mapInteraction";
import type { JobStatus } from "@/types";
import type { MapLayerState, RankingPresentation } from "@/utils/mapLayer";
import { JudgeMap } from "./map/JudgeMap";
import { buildJudgeMapCatalog, exploreMapState } from "./mapCatalog";
import { MAP_ABOUT_BODY, MAP_ABOUT_LAYER } from "@/features/experience/copy";

type MapBandProps = {
  layer: MapLayerState;
  ranking: RankingPresentation;
  areaId: string | null;
  jobId: string | null;
  jobStatus: JobStatus | null;
  result: AnalysisResultStub | null;
  submitting: boolean;
  analysisTime?: string | null;
  mapMode?: MapMode;
  onMapModeChange?: (mode: MapMode) => void;
  contextZones?: ZoneMapProperties[];
  selectedZoneId?: string | null;
  onSelectedIdChange?: (geoid: string | null) => void;
};

export function MapBand(props: MapBandProps) {
  const [geometry, setGeometry] = useState<AreaGeometryPayload | null>(null);
  const mapMode = props.mapMode ?? "THERMAL";
  const areaId = props.areaId ?? "phoenix-demo";

  useEffect(() => {
    const loader = createGeometryLoader();
    let cancelled = false;
    void loader
      .load(areaId)
      .then((outcome) => {
        if (cancelled || outcome.stale) {
          return;
        }
        setGeometry(outcome.payload);
      })
      .catch(() => {
        if (!cancelled) {
          setGeometry(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [areaId]);

  const catalog = useMemo(
    () =>
      buildJudgeMapCatalog({
        geometry,
        areaId,
        result: props.result,
        jobStatus: props.jobStatus,
        analysisTime: props.analysisTime,
      }),
    [areaId, geometry, props.analysisTime, props.jobStatus, props.result],
  );

  const modeCatalog = useMemo(
    () =>
      bindMapModeCatalog({
        historical: catalog,
        mode: mapMode,
        zones: props.contextZones ?? [],
      }),
    [catalog, mapMode, props.contextZones],
  );

  const mapState = exploreMapState({
    submitting: props.submitting,
    jobStatus: props.jobStatus,
    catalog: modeCatalog,
    rankingState: props.ranking.state,
  });

  return (
    <section
      className="judge-map"
      aria-label={props.layer.label}
      data-testid="map-stage"
      data-layout="map-primary"
      data-map-state={mapState}
      data-map-mode={mapMode}
      data-ranked-feature-count={String(rankedFillCount(modeCatalog))}
      data-context-fill-count={String(contextFillCount(modeCatalog))}
      data-geometry-feature-count={String(modeCatalog?.collection.features.length ?? 0)}
      data-map-source-count={String(modeCatalog?.collection.features.length ?? 0)}
      data-layer-label={modeCatalog?.layer_title ?? props.layer.label}
    >
      <p className="judge-sr" data-testid="map-layer-label">
        {modeCatalog?.layer_title ?? props.layer.label}
      </p>
      {props.onMapModeChange ? (
        <MapModeTabs mode={mapMode} onModeChange={props.onMapModeChange} />
      ) : null}
      <JudgeMap
        lane="A"
        historical={modeCatalog}
        enabled
        selectedId={props.selectedZoneId ?? null}
        onSelectedIdChange={props.onSelectedIdChange}
      />
      <details className="hx-method hx-map-about" data-testid="map-about-layer">
        <summary>{MAP_ABOUT_LAYER}</summary>
        <p>{MAP_ABOUT_BODY}</p>
      </details>
    </section>
  );
}
