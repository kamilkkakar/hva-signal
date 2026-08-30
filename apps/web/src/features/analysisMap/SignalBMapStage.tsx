import { useEffect, useRef, useState } from "react";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./signalBMap.css";
import { signalBHoverFromProperties } from "./signalBHover";
import { featureCollectionBounds } from "./signalBGeometry";
import { signalBMapIsEnabled } from "./signalBMapGate";
import {
  SIGNAL_B_FILL_LAYER_ID,
  SIGNAL_B_FOOTNOTE_COPY,
  SIGNAL_B_LAYER_TITLE,
  SIGNAL_B_LINE_LAYER_ID,
  SIGNAL_B_LINE_WIDTH,
  SIGNAL_B_NEUTRAL_FILL,
  SIGNAL_B_NEUTRAL_LINE,
  SIGNAL_B_PAPER,
  SIGNAL_B_SOURCE_ID,
} from "./signalBPolicy";
import { presentSignalBMap } from "./signalBPresentation";
import type {
  SignalBGeometryCollection,
  SignalBHover,
  SignalBMapAvailability,
  SignalBMapPresentation,
  SignalBSnapshot,
} from "./signalBTypes";

const EMPTY_COLLECTION = {
  type: "FeatureCollection" as const,
  features: [],
};

export type SignalBMapStageProps = {
  enabled?: boolean;
  snapshot: SignalBSnapshot | null;
  geometry: SignalBGeometryCollection | null;
  availability?: SignalBMapAvailability;
  showZoneTable?: boolean;
};

function ensureSignalBLayers(map: maplibregl.Map): GeoJSONSource | null {
  if (!map.isStyleLoaded()) {
    return null;
  }
  if (!map.getSource(SIGNAL_B_SOURCE_ID)) {
    map.addSource(SIGNAL_B_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_COLLECTION,
    });
  }
  if (!map.getLayer(SIGNAL_B_FILL_LAYER_ID)) {
    map.addLayer({
      id: SIGNAL_B_FILL_LAYER_ID,
      type: "fill",
      source: SIGNAL_B_SOURCE_ID,
      paint: {
        "fill-color": SIGNAL_B_NEUTRAL_FILL,
        "fill-opacity": 0,
      },
    });
  }
  if (!map.getLayer(SIGNAL_B_LINE_LAYER_ID)) {
    map.addLayer({
      id: SIGNAL_B_LINE_LAYER_ID,
      type: "line",
      source: SIGNAL_B_SOURCE_ID,
      paint: {
        "line-color": SIGNAL_B_NEUTRAL_LINE,
        "line-width": SIGNAL_B_LINE_WIDTH,
      },
    });
  }
  return (map.getSource(SIGNAL_B_SOURCE_ID) as GeoJSONSource | undefined) ?? null;
}

export function applySignalBPresentation(
  map: maplibregl.Map,
  presentation: SignalBMapPresentation,
): boolean {
  const source = ensureSignalBLayers(map);
  if (!source) {
    return false;
  }
  const showGeometry =
    presentation.visualState === "ready" || presentation.visualState === "partial";
  const payload = showGeometry ? presentation.collection : EMPTY_COLLECTION;
  source.setData(payload as GeoJSON.FeatureCollection);
  map.setPaintProperty(
    SIGNAL_B_FILL_LAYER_ID,
    "fill-color",
    presentation.fillPaint["fill-color"],
  );
  map.setPaintProperty(
    SIGNAL_B_FILL_LAYER_ID,
    "fill-opacity",
    presentation.fillPaint["fill-opacity"],
  );
  map.setPaintProperty(
    SIGNAL_B_LINE_LAYER_ID,
    "line-color",
    presentation.linePaint["line-color"],
  );
  map.setPaintProperty(
    SIGNAL_B_LINE_LAYER_ID,
    "line-width",
    presentation.linePaint["line-width"],
  );
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

export function SignalBMapStage({
  enabled,
  snapshot,
  geometry,
  availability,
  showZoneTable = false,
}: SignalBMapStageProps) {
  const gatedOn = signalBMapIsEnabled(enabled);
  const presentation = presentSignalBMap({
    enabled,
    snapshot,
    geometry,
    availability,
  });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const presentationRef = useRef(presentation);
  const [hover, setHover] = useState<SignalBHover | null>(null);

  presentationRef.current = presentation;

  useEffect(() => {
    if (!gatedOn) {
      return;
    }
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
            id: "hva-signal-b-paper",
            type: "background",
            paint: { "background-color": SIGNAL_B_PAPER },
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
      applySignalBPresentation(map, presentationRef.current);
    };
    const onMove = (event: maplibregl.MapLayerMouseEvent) => {
      const state = presentationRef.current.visualState;
      if (state !== "ready" && state !== "partial") {
        setHover(null);
        return;
      }
      setHover(signalBHoverFromProperties(event.features?.[0]?.properties));
    };
    const onLeave = () => {
      setHover(null);
    };
    if (map.loaded()) {
      onReady();
    } else {
      map.on("load", onReady);
    }
    map.on("mousemove", SIGNAL_B_FILL_LAYER_ID, onMove);
    map.on("mouseleave", SIGNAL_B_FILL_LAYER_ID, onLeave);
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
  }, [gatedOn]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !gatedOn) {
      return;
    }
    let attempts = 0;
    let frame = 0;
    const tryApply = () => {
      if (applySignalBPresentation(map, presentation)) {
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
  }, [gatedOn, presentation]);

  return (
    <section
      className="sbmap"
      aria-label="Selected-time thermal snapshot map"
      data-testid="signal-b-map-stage"
      data-signal-b-gate={gatedOn ? "on" : "off"}
      data-autostretch="no"
      data-percentile-stretch="no"
      data-rank="no"
      data-map-state={presentation.visualState}
      data-layer-title={presentation.layerTitle}
    >
      {!gatedOn ? (
        <p className="sbmap-gated" data-testid="signal-b-map-gated">
          Signal B map is gated. The production Phoenix A map is unchanged.
        </p>
      ) : (
        <>
          <div className="sbmap-stage">
            <div ref={containerRef} className="sbmap-canvas" data-testid="signal-b-map-canvas" />
            <div className="sbmap-overlay">
              <p className="sbmap-label" data-testid="signal-b-layer-label">
                {SIGNAL_B_LAYER_TITLE}
              </p>
              {presentation.message && (
                <p className="sbmap-message" data-testid="signal-b-map-message">
                  {presentation.message}
                </p>
              )}
              {hover && (
                <p className="sbmap-hover" data-testid="signal-b-map-hover">
                  {hover.zone_id}
                  {" · "}
                  {hover.display_temperature}
                  {" · "}
                  {hover.coverage_status}
                  {" · "}
                  {hover.units}
                  {" · "}
                  {hover.aggregation_method}
                </p>
              )}
            </div>
          </div>
          <div className="sbmap-chrome">
            {presentation.snapshotFacts.factText && (
              <p className="sbmap-facts" data-testid="signal-b-snapshot-facts">
                {presentation.snapshotFacts.factText}
              </p>
            )}
            <details className="sbmap-notes" data-testid="signal-b-map-notes">
              <summary>Snapshot notes</summary>
              <p className="sbmap-copy">{presentation.meaningCopy}</p>
              <p className="sbmap-copy">{presentation.stretchCopy}</p>
              <p className="sbmap-copy">{presentation.methodologyCopy}</p>
              <p className="sbmap-footnote" data-testid="signal-b-map-footnote">
                {SIGNAL_B_FOOTNOTE_COPY}
              </p>
              {showZoneTable ? (
                <table className="sbmap-table" data-testid="signal-b-zone-table">
                  <thead>
                    <tr>
                      <th>zone_id</th>
                      <th>mean °C</th>
                      <th>coverage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {presentation.tableRows.map((row) => (
                      <tr key={row.zone_id} data-zone-id={row.zone_id}>
                        <td>{row.zone_id}</td>
                        <td>{row.display_temperature}</td>
                        <td>{row.coverage_status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </details>
          </div>
        </>
      )}
    </section>
  );
}
