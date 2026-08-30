import { memo, useEffect, useRef, useState } from "react";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { createGeometryLoader } from "@/api/areaGeometry";
import type { JobStatus } from "@/types";
import {
  bindGeometryToAnalysis,
  featureCollectionBounds,
} from "@/utils/geometryJoin";
import {
  HistoricalPositionLegend,
  allHatchImages,
  legendModeFromMap,
  signalAFillPaint,
  signalAHaloPaint,
  signalAHatchPaint,
  signalALinePaint,
} from "@/features/mapEncoding";
import type { MapLayerState, RankingPresentation } from "@/utils/mapLayer";
import {
  emptyMapPresentation,
  mapPresentationFromBind,
  type MapPresentation,
} from "@/utils/mapPresentation";

const SOURCE_ID = "hva-area-geometry";
const FILL_LAYER_ID = "hva-tract-fill";
const HATCH_LAYER_ID = "hva-tract-hatch";
const HALO_LAYER_ID = "hva-tract-halo";
const LINE_LAYER_ID = "hva-tract-outline";
const EMPTY_COLLECTION = {
  type: "FeatureCollection" as const,
  features: [],
};

export type MapStageProps = {
  layer: MapLayerState;
  ranking: RankingPresentation;
  areaId: string | null;
  resultAreaId: string | null;
  jobId: string | null;
  jobStatus: JobStatus | null;
  result: AnalysisResultStub | null;
  submitting: boolean;
};

type HoverCard = {
  geoid: string;
  backendOrder: number;
  historicalQuantile: number | null;
};

function errorPresentation(message: string): MapPresentation {
  return {
    visualState: "error",
    outlineCount: 0,
    rankedFillCount: 0,
    thermalOrderingVisible: false,
    fallback: null,
    message,
    observedSpread: null,
    collection: EMPTY_COLLECTION,
  };
}

function resultIsReady(status: JobStatus | null): boolean {
  return status === "complete" || status === "partial";
}

function ensureHatchImages(map: maplibregl.Map): void {
  for (const image of allHatchImages()) {
    if (map.hasImage(image.id)) {
      continue;
    }
    map.addImage(image.id, {
      width: image.width,
      height: image.height,
      data: image.data,
    });
  }
}

function ensureMapLayers(map: maplibregl.Map): GeoJSONSource | null {
  if (!map.isStyleLoaded()) {
    return null;
  }
  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: EMPTY_COLLECTION,
    });
  }
  ensureHatchImages(map);
  const idleFill = signalAFillPaint({ authorized: false, maxOrder: 1 });
  const idleHatch = signalAHatchPaint({ authorized: false, maxOrder: 1 });
  const idleHalo = signalAHaloPaint(false);
  const idleLine = signalALinePaint(false);
  if (!map.getLayer(FILL_LAYER_ID)) {
    map.addLayer({
      id: FILL_LAYER_ID,
      type: "fill",
      source: SOURCE_ID,
      paint: {
        "fill-color": idleFill["fill-color"] as string,
        "fill-opacity": idleFill["fill-opacity"],
      },
    });
  }
  if (!map.getLayer(HATCH_LAYER_ID)) {
    map.addLayer({
      id: HATCH_LAYER_ID,
      type: "fill",
      source: SOURCE_ID,
      paint: {
        "fill-pattern": idleHatch["fill-pattern"] as string,
        "fill-opacity": idleHatch["fill-opacity"],
      },
    });
  }
  if (!map.getLayer(HALO_LAYER_ID)) {
    map.addLayer({
      id: HALO_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": idleHalo["line-color"],
        "line-width": idleHalo["line-width"],
        "line-opacity": idleHalo["line-opacity"],
      },
    });
  }
  if (!map.getLayer(LINE_LAYER_ID)) {
    map.addLayer({
      id: LINE_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": idleLine["line-color"],
        "line-width": idleLine["line-width"],
        "line-opacity": idleLine["line-opacity"],
      },
    });
  }
  return (map.getSource(SOURCE_ID) as GeoJSONSource | undefined) ?? null;
}

function applyPresentation(map: maplibregl.Map, presentation: MapPresentation): boolean {
  const source = ensureMapLayers(map);
  if (!source) {
    return false;
  }
  const showGeometry =
    presentation.visualState === "insufficient" ||
    presentation.visualState === "sufficient";
  const payload = showGeometry
    ? {
        type: "FeatureCollection" as const,
        features: presentation.collection.features.map((feature) => ({
          type: "Feature" as const,
          properties: { ...feature.properties },
          geometry: feature.geometry,
        })),
      }
    : EMPTY_COLLECTION;
  source.setData(payload as GeoJSON.FeatureCollection);
  const stage = map.getContainer().closest("[data-testid='map-stage']");
  if (stage instanceof HTMLElement) {
    stage.setAttribute("data-map-source-count", String(payload.features.length));
  }
  const orders = presentation.collection.features.map(
    (feature) => Number(feature.properties.backend_order) || 0,
  );
  const maxOrder = Math.max(1, ...orders);
  const authorized = presentation.thermalOrderingVisible;
  const fill = signalAFillPaint({ authorized, maxOrder });
  const hatch = signalAHatchPaint({ authorized, maxOrder });
  const halo = signalAHaloPaint(authorized);
  const line = signalALinePaint(authorized);
  map.setPaintProperty(FILL_LAYER_ID, "fill-color", fill["fill-color"]);
  map.setPaintProperty(FILL_LAYER_ID, "fill-opacity", fill["fill-opacity"]);
  if (map.getLayer(HATCH_LAYER_ID)) {
    map.setPaintProperty(HATCH_LAYER_ID, "fill-pattern", hatch["fill-pattern"]);
    map.setPaintProperty(HATCH_LAYER_ID, "fill-opacity", hatch["fill-opacity"]);
  }
  if (map.getLayer(HALO_LAYER_ID)) {
    map.setPaintProperty(HALO_LAYER_ID, "line-color", halo["line-color"]);
    map.setPaintProperty(HALO_LAYER_ID, "line-width", halo["line-width"]);
    map.setPaintProperty(HALO_LAYER_ID, "line-opacity", halo["line-opacity"]);
  }
  if (map.getLayer(LINE_LAYER_ID)) {
    map.setPaintProperty(LINE_LAYER_ID, "line-color", line["line-color"]);
    map.setPaintProperty(LINE_LAYER_ID, "line-width", line["line-width"]);
    map.setPaintProperty(LINE_LAYER_ID, "line-opacity", line["line-opacity"]);
  }
  if (!showGeometry) {
    return true;
  }
  const bounds = featureCollectionBounds(presentation.collection);
  if (!bounds) {
    return true;
  }
  map.resize();
  map.fitBounds(bounds, { padding: 36, duration: 0 });
  return true;
}

function MapStageInner({
  layer,
  ranking,
  areaId,
  resultAreaId,
  jobId,
  jobStatus,
  result,
  submitting,
}: MapStageProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loaderRef = useRef(createGeometryLoader());
  const resultRef = useRef(result);
  const presentationRef = useRef<MapPresentation>(emptyMapPresentation("idle"));
  const [presentation, setPresentation] = useState<MapPresentation>(
    emptyMapPresentation("idle"),
  );
  const [hover, setHover] = useState<HoverCard | null>(null);

  resultRef.current = result;
  presentationRef.current = presentation;

  const areaAligned = Boolean(areaId && resultAreaId && areaId === resultAreaId);
  const empty = ranking.state === "INSUFFICIENT_EVIDENCE";
  const thermalBlocked = !layer.allowPriorityChoropleth;
  const legendMode = legendModeFromMap({
    visualState: presentation.visualState,
    thermalOrderingVisible: presentation.thermalOrderingVisible,
  });

  useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }
    const map = new maplibregl.Map({
      container: node,
      style: {
        version: 8,
        sources: {},
        layers: [
          {
            id: "hva-paper",
            type: "background",
            paint: { "background-color": "#c2c8b4" },
          },
        ],
      },
      attributionControl: false,
      fadeDuration: 0,
      renderWorldCopies: false,
    });
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    const onReady = () => {
      applyPresentation(map, presentationRef.current);
    };
    const onMove = (event: maplibregl.MapLayerMouseEvent) => {
      if (presentationRef.current.visualState !== "sufficient") {
        setHover(null);
        return;
      }
      const properties = event.features?.[0]?.properties;
      if (!properties || properties.GEOID == null) {
        setHover(null);
        return;
      }
      const rawQuantile = properties.q_A;
      setHover({
        geoid: String(properties.GEOID),
        backendOrder: Number(properties.backend_order) || 0,
        historicalQuantile:
          typeof rawQuantile === "number"
            ? rawQuantile
            : rawQuantile == null
              ? null
              : Number(rawQuantile),
      });
    };
    const onLeave = () => {
      setHover(null);
    };
    if (map.loaded()) {
      onReady();
    } else {
      map.on("load", onReady);
    }
    map.on("mousemove", FILL_LAYER_ID, onMove);
    map.on("mouseleave", FILL_LAYER_ID, onLeave);
    mapRef.current = map;
    const observer = new ResizeObserver(() => {
      map.resize();
    });
    observer.observe(node);
    return () => {
      observer.disconnect();
      map.off("load", onReady);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    let attempts = 0;
    let frame = 0;
    const tryApply = () => {
      if (applyPresentation(map, presentation)) {
        return;
      }
      if (attempts >= 180) {
        return;
      }
      attempts += 1;
      frame = window.requestAnimationFrame(tryApply);
    };
    tryApply();
    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [presentation]);

  useEffect(() => {
    const loader = loaderRef.current;
    loader.invalidate();
    setHover(null);
    if (submitting) {
      setPresentation(emptyMapPresentation("loading"));
      return;
    }
    const currentResult = resultRef.current;
    if (
      !areaId ||
      !jobId ||
      !resultIsReady(jobStatus) ||
      !currentResult ||
      !areaAligned
    ) {
      setPresentation(emptyMapPresentation("idle"));
      return;
    }
    let cancelled = false;
    setPresentation(emptyMapPresentation("loading"));
    void loader
      .load(areaId)
      .then((outcome) => {
        if (cancelled || outcome.stale) {
          return;
        }
        const bound = bindGeometryToAnalysis({
          geometry: outcome.payload,
          requestAreaId: areaId,
          result: currentResult,
        });
        setPresentation(mapPresentationFromBind(bound, currentResult));
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setPresentation(
          errorPresentation(
            error instanceof Error
              ? error.message
              : "Area geometry could not be loaded.",
          ),
        );
      });
    return () => {
      cancelled = true;
    };
  }, [areaAligned, areaId, jobId, jobStatus, submitting]);

  return (
    <main
      className="map-stage"
      aria-label="Analysis map"
      data-testid="map-stage"
      data-map-state={presentation.visualState}
      data-geometry-feature-count={String(presentation.outlineCount)}
      data-ranked-feature-count={String(presentation.rankedFillCount)}
      data-encoding="historical-position"
      data-legend-mode={legendMode}
      data-b-public="no"
    >
      <div ref={containerRef} className="map-canvas" data-testid="map-canvas" />
      <div className="fiducial fiducial-nw" aria-hidden="true" />
      <div className="fiducial fiducial-ne" aria-hidden="true" />
      <div className="fiducial fiducial-sw" aria-hidden="true" />
      <div className="fiducial fiducial-se" aria-hidden="true" />

      <div className="map-overlay">
        <p className="map-label" data-testid="map-layer-label">
          Map layer: {layer.label}
        </p>

        {thermalBlocked && layer.message && (
          <p className="map-limitation" data-testid="thermal-diff-message">
            {layer.message}
          </p>
        )}

        {presentation.visualState === "error" && presentation.message && (
          <p className="map-limitation" data-testid="map-geometry-error">
            {presentation.message}
          </p>
        )}

        {presentation.visualState === "loading" && (
          <p className="map-empty">Loading versioned area geometry.</p>
        )}

        {presentation.visualState === "sufficient" && presentation.message && (
          <p className="map-empty">{presentation.message}</p>
        )}

        {presentation.visualState === "idle" && empty && (
          <p className="map-empty">
            {thermalBlocked
              ? "Neutral evidence state. No thermal ranking choropleth is shown."
              : "INSUFFICIENT_EVIDENCE. Submit a replay job when the backend is ready. Rankings will not be invented from an empty map."}
          </p>
        )}

        {hover && presentation.visualState === "sufficient" && (
          <p className="map-hover" data-testid="map-hover">
            GEOID {hover.geoid}
            {" · "}
            backend order {hover.backendOrder}
            {hover.historicalQuantile != null &&
              ` · historical quantile position ${hover.historicalQuantile}`}
          </p>
        )}

        <p className="map-coords" aria-hidden="true">
          PLOTTER BED · NO TILESERVER · NO SYNTHETIC FIELD
        </p>
      </div>
      <div className="map-encoding-slot">
        <HistoricalPositionLegend mode={legendMode} />
      </div>
    </main>
  );
}

export const MapStage = memo(MapStageInner);
