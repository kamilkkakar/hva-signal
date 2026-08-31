import { useEffect, useReducer, useRef } from "react";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./mapInteraction.css";
import { allHatchImages, signalAFillPaint, signalAHatchPaint } from "@/features/mapEncoding";
import { featureCollectionBounds } from "./bounds";
import { mapInteractionIsEnabled } from "./flags";
import { highlightFillPaint, highlightHatchPaint, highlightLinePaint } from "./highlight";
import { MapInteractionChrome } from "./MapInteractionChrome";
import {
  INTERACTION_PAPER,
} from "./policy";
import { observedThermalSpan } from "./thermalSpan";
import { presentMapInteraction } from "./present";
import { initialInteractionState, reduceInteraction } from "./state";
import type { InteractionCatalog, InteractionEvent, InteractionState } from "./types";

const SOURCE_ID = "hva-map-interaction-zones";
const FILL_LAYER_ID = "hva-map-interaction-fill";
const HATCH_LAYER_ID = "hva-map-interaction-hatch";
const LINE_LAYER_ID = "hva-map-interaction-line";
const EMPTY_COLLECTION = {
  type: "FeatureCollection" as const,
  features: [],
};

export type MapInteractionStageProps = {
  enabled?: boolean;
  catalog: InteractionCatalog | null;
  selectedId?: string | null;
  onSelectedIdChange?: (geoid: string | null) => void;
};

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

function ensureLayers(map: maplibregl.Map): GeoJSONSource | null {
  if (!map.isStyleLoaded()) {
    return null;
  }
  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: "geojson",
      data: EMPTY_COLLECTION,
      promoteId: "GEOID",
    });
  }
  ensureHatchImages(map);
  const idleFill = signalAFillPaint({ authorized: false, maxOrder: 1 });
  const idleHatch = signalAHatchPaint({ authorized: false, maxOrder: 1 });
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
  if (!map.getLayer(LINE_LAYER_ID)) {
    map.addLayer({
      id: LINE_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      paint: {
        "line-color": "#4e5748",
        "line-width": 1.15,
      },
    });
  }
  return (map.getSource(SOURCE_ID) as GeoJSONSource | undefined) ?? null;
}

function applyCatalog(
  map: maplibregl.Map,
  catalog: InteractionCatalog | null,
  state: InteractionState,
  canvasAllowed: boolean,
): boolean {
  const source = ensureLayers(map);
  if (!source) {
    return false;
  }
  const payload = canvasAllowed && catalog ? catalog.collection : EMPTY_COLLECTION;
  source.setData(payload as GeoJSON.FeatureCollection);
  const fill = highlightFillPaint(catalog, state);
  const hatch = highlightHatchPaint(catalog, state);
  const line = highlightLinePaint(catalog, state);
  map.setPaintProperty(FILL_LAYER_ID, "fill-color", fill["fill-color"]);
  map.setPaintProperty(FILL_LAYER_ID, "fill-opacity", fill["fill-opacity"]);
  if (map.getLayer(HATCH_LAYER_ID)) {
    map.setPaintProperty(HATCH_LAYER_ID, "fill-pattern", hatch["fill-pattern"]);
    map.setPaintProperty(HATCH_LAYER_ID, "fill-opacity", hatch["fill-opacity"]);
  }
  map.setPaintProperty(LINE_LAYER_ID, "line-color", line["line-color"]);
  map.setPaintProperty(LINE_LAYER_ID, "line-width", line["line-width"]);
  if (canvasAllowed && catalog) {
    for (const zone of catalog.zones) {
      map.setFeatureState(
        { source: SOURCE_ID, id: zone.geoid },
        {
          hover: state.layerActive && state.hoverId === zone.geoid,
          selected: state.layerActive && state.selectedId === zone.geoid,
        },
      );
    }
  }
  return true;
}

function fitCatalog(map: maplibregl.Map, catalog: InteractionCatalog | null): void {
  if (!catalog) {
    return;
  }
  const bounds = featureCollectionBounds(catalog.collection);
  if (!bounds) {
    return;
  }
  map.resize();
  map.fitBounds(bounds, { padding: 36, duration: 0 });
}

export function MapInteractionStage({
  enabled,
  catalog,
  selectedId = null,
  onSelectedIdChange,
}: MapInteractionStageProps) {
  const gatedOn = mapInteractionIsEnabled(enabled);
  const [state, dispatch] = useReducer(
    (current: InteractionState, event: InteractionEvent) =>
      reduceInteraction(current, event, catalog),
    undefined,
    initialInteractionState,
  );
  const view = presentMapInteraction({ enabled, catalog, state });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const catalogRef = useRef(catalog);
  const stateRef = useRef(state);
  const viewRef = useRef(view);
  const lastFit = useRef(0);

  catalogRef.current = catalog;
  stateRef.current = state;
  viewRef.current = view;

  const selectedOut = state.layerActive ? state.selectedId : null;
  useEffect(() => {
    onSelectedIdChange?.(selectedOut);
  }, [onSelectedIdChange, selectedOut]);

  useEffect(() => {
    dispatch({ type: "set_selected", geoid: selectedId });
  }, [selectedId]);

  useEffect(() => {
    if (!gatedOn || !view.canvasAllowed) {
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
            id: "hva-map-interaction-paper",
            type: "background",
            paint: { "background-color": INTERACTION_PAPER },
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
    const geoidFromEvent = (event: maplibregl.MapLayerMouseEvent): string | null => {
      const props = event.features?.[0]?.properties;
      if (!props || props.GEOID == null) {
        return null;
      }
      return String(props.GEOID);
    };
    const onReady = () => {
      applyCatalog(map, catalogRef.current, stateRef.current, viewRef.current.canvasAllowed);
      fitCatalog(map, catalogRef.current);
    };
    const onMove = (event: maplibregl.MapLayerMouseEvent) => {
      const geoid = geoidFromEvent(event);
      map.getCanvas().style.cursor = geoid ? "pointer" : "";
      dispatch({ type: "hover", geoid });
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = "";
      dispatch({ type: "hover", geoid: null });
    };
    const onClick = (event: maplibregl.MapLayerMouseEvent) => {
      const geoid = geoidFromEvent(event);
      if (geoid) {
        dispatch({ type: "select", geoid });
      }
    };
    if (map.loaded()) {
      onReady();
    } else {
      map.on("load", onReady);
    }
    map.on("mousemove", FILL_LAYER_ID, onMove);
    map.on("mouseleave", FILL_LAYER_ID, onLeave);
    map.on("click", FILL_LAYER_ID, onClick);
    map.on("mousemove", HATCH_LAYER_ID, onMove);
    map.on("mouseleave", HATCH_LAYER_ID, onLeave);
    map.on("click", HATCH_LAYER_ID, onClick);
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
  }, [gatedOn, view.canvasAllowed]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !gatedOn) {
      return;
    }
    let attempts = 0;
    let frame = 0;
    const tryApply = () => {
      if (applyCatalog(map, catalog, state, view.canvasAllowed)) {
        if (state.fitGeneration !== lastFit.current) {
          lastFit.current = state.fitGeneration;
          fitCatalog(map, catalog);
        }
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
  }, [catalog, gatedOn, state, view.canvasAllowed]);

  return (
    <section
      className="mapi"
      aria-label={
        catalog?.kind === "selected_time_snapshot"
          ? "Selected-time thermal snapshot"
          : "Nighttime historical thermal pattern"
      }
      data-testid="map-interaction-stage"
      data-layout="map-primary"
      data-map-interaction-gate={gatedOn ? "on" : "off"}
      data-map-state={view.visualState}
      data-order-shown={
        catalog?.kind === "historical_ordering" && catalog.fill_authorized ? "true" : "false"
      }
      data-canvas-allowed={view.canvasAllowed ? "true" : "false"}
      data-hatch-layer="hva-map-interaction-hatch"
      data-position-legend={view.positionLegendMode ?? "none"}
      data-decorative="false"
    >
      {!gatedOn ? (
        <p className="mapi-gated" data-testid="map-interaction-gated">
          {view.meaningCopy}
        </p>
      ) : (
        <>
          {view.canvasAllowed ? (
            <div className="mapi-stage">
              <div ref={containerRef} id="judge-map-canvas" className="mapi-canvas" data-testid="map-interaction-canvas" />
              <div className="mapi-overlay">
                <p className="mapi-label" data-testid="map-interaction-layer-label">
                  {view.layerTitle}
                </p>
                <p className="mapi-copy">{view.meaningCopy}</p>
                {view.hover && (
                  <p className="mapi-hover" data-testid="map-interaction-hover">
                    {view.hover.line}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="mapi-empty" data-testid="map-interaction-empty">
              {view.meaningCopy}
            </p>
          )}
          <MapInteractionChrome
            view={view}
            dispatch={dispatch}
            catalogKind={catalog?.kind}
            fillKind={catalog?.fill_kind}
            observedMinC={observedThermalSpan(catalog)?.minC ?? null}
            observedMaxC={observedThermalSpan(catalog)?.maxC ?? null}
          />
        </>
      )}
    </section>
  );
}
