import { useEffect, useReducer, useRef } from "react";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./mapInteraction.css";
import { featureCollectionBounds } from "./bounds";
import { mapInteractionIsEnabled } from "./flags";
import { highlightFillPaint, highlightLinePaint } from "./highlight";
import { MapInteractionChrome } from "./MapInteractionChrome";
import {
  INTERACTION_PAPER,
} from "./policy";
import { presentMapInteraction } from "./present";
import { initialInteractionState, reduceInteraction } from "./state";
import type { InteractionCatalog, InteractionEvent, InteractionState } from "./types";

const SOURCE_ID = "hva-map-interaction-zones";
const FILL_LAYER_ID = "hva-map-interaction-fill";
const LINE_LAYER_ID = "hva-map-interaction-line";
const EMPTY_COLLECTION = {
  type: "FeatureCollection" as const,
  features: [],
};

export type MapInteractionStageProps = {
  enabled?: boolean;
  catalog: InteractionCatalog | null;
};

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
  if (!map.getLayer(FILL_LAYER_ID)) {
    map.addLayer({
      id: FILL_LAYER_ID,
      type: "fill",
      source: SOURCE_ID,
      paint: {
        "fill-color": "#9aa392",
        "fill-opacity": 0,
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
  const line = highlightLinePaint(state);
  map.setPaintProperty(FILL_LAYER_ID, "fill-color", fill["fill-color"]);
  map.setPaintProperty(FILL_LAYER_ID, "fill-opacity", fill["fill-opacity"]);
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

export function MapInteractionStage({ enabled, catalog }: MapInteractionStageProps) {
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
      dispatch({ type: "hover", geoid: geoidFromEvent(event) });
    };
    const onLeave = () => {
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
      aria-label="Analysis map interaction"
      data-testid="map-interaction-stage"
      data-map-interaction-gate={gatedOn ? "on" : "off"}
      data-map-state={view.visualState}
      data-canvas-allowed={view.canvasAllowed ? "true" : "false"}
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
              <div ref={containerRef} className="mapi-canvas" data-testid="map-interaction-canvas" />
              <div className="mapi-overlay">
                <p className="mapi-label" data-testid="map-interaction-layer-label">
                  {view.layerTitle}
                </p>
                <p className="mapi-copy">{view.meaningCopy}</p>
                {view.hover && (
                  <p className="mapi-hover" data-testid="map-interaction-hover">
                    {view.hover.geoid}
                    {" · "}
                    {view.hover.label}
                    {" · "}
                    {view.hover.value_display}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="mapi-empty" data-testid="map-interaction-empty">
              {view.meaningCopy}
            </p>
          )}
          <MapInteractionChrome view={view} dispatch={dispatch} />
        </>
      )}
    </section>
  );
}
