import type { SignalAView } from "./types";

type SigAMapLayerProps = {
  view: SignalAView;
};

export function SigAMapLayer({ view }: SigAMapLayerProps) {
  return (
    <section
      className="siga-map-layer"
      data-testid="siga-map-layer"
      data-outlines={view.outlineCount}
      data-fills={view.rankedFillCount}
      data-hover={view.hoverEnabled ? "on" : "off"}
      aria-label={view.assistiveMapName}
    >
      <p className="siga-map-title" data-testid="siga-map-title">
        {view.mapLayerTitle}
      </p>
      <p data-testid="siga-map-overlay">{view.mapOverlay}</p>
    </section>
  );
}
