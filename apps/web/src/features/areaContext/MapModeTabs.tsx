import { useRef } from "react";
import { MAP_MODE_META, mapModeMeta } from "@/features/selectedAreaStory/copy";
import { MAP_MODES } from "./mapModes";
import type { MapMode } from "./types";

export const MAP_CANVAS_ID = "judge-map-canvas";

export type MapModeTabsProps = {
  mode: MapMode;
  onModeChange: (mode: MapMode) => void;
};

export function MapModeTabs({ mode, onModeChange }: MapModeTabsProps) {
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const meta = mapModeMeta(mode);

  const move = (index: number, delta: number) => {
    const next = (index + delta + MAP_MODES.length) % MAP_MODES.length;
    const target = MAP_MODES[next];
    if (!target) {
      return;
    }
    onModeChange(target);
    buttons.current[next]?.focus();
  };

  return (
    <div className="judge-map-modes">
      <div
        className="area-context-modes"
        role="tablist"
        aria-label="Context map modes"
        data-testid="map-mode-tabs"
      >
        {MAP_MODES.map((item, index) => (
          <button
            key={item}
            type="button"
            role="tab"
            id={`map-mode-tab-${item}`}
            aria-selected={mode === item}
            aria-controls={MAP_CANVAS_ID}
            tabIndex={mode === item ? 0 : -1}
            data-mode={item}
            ref={(node) => {
              buttons.current[index] = node;
            }}
            onClick={() => onModeChange(item)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight") {
                event.preventDefault();
                move(index, 1);
              }
              if (event.key === "ArrowLeft") {
                event.preventDefault();
                move(index, -1);
              }
            }}
          >
            {MAP_MODE_META.find((row) => row.mode === item)?.label ?? item}
          </button>
        ))}
      </div>
      <p
        className="judge-map-legend"
        data-testid="map-mode-legend"
        data-mode={mode}
        data-source-family={mode === "THERMAL" ? "fortyguard" : "context"}
      >
        {meta.source} · {meta.year} · {meta.unit}. {meta.meaning}
      </p>
    </div>
  );
}
