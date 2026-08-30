import type { AnalysisAreaId, MapModeId, MapModeModel } from "@/contracts";
import { MAP_MODE_IDS } from "@/contracts";
import { MAP_CLICK, MAP_MODE_TITLES, MAP_OUTLINE_ONLY } from "@/ia/copy";
import { areaCells, MAP_VIEWBOX } from "./areaLayout";
import { MapLegend } from "./MapLegend";

type SpatialMapProps = {
  readonly mode: MapModeModel;
  readonly selectedAreaId: AnalysisAreaId | null;
  readonly onSelectArea: (id: AnalysisAreaId) => void;
  readonly onSelectMode: (id: MapModeId) => void;
};

const CELLS = areaCells();

export function SpatialMap({
  mode,
  selectedAreaId,
  onSelectArea,
  onSelectMode,
}: SpatialMapProps) {
  return (
    <section className="map-stage" aria-label="Spatial map" data-testid="spatial-map">
      <div className="map-board">
        <div className="map-toolbar">
          <label>
            Map mode
            <select
              value={mode.id}
              onChange={(event) => onSelectMode(event.target.value as MapModeId)}
              data-testid="map-mode"
            >
              {MAP_MODE_IDS.map((id) => (
                <option key={id} value={id}>
                  {MAP_MODE_TITLES[id]}
                </option>
              ))}
            </select>
          </label>
          <p className="chip">{MAP_OUTLINE_ONLY}</p>
        </div>
        <svg
          className="map-svg"
          viewBox={MAP_VIEWBOX}
          role="group"
          aria-label="Twenty-five analysis areas"
          data-testid="map-svg"
        >
          {CELLS.map((cell) => (
            <g key={cell.id}>
              <rect
                className="map-cell"
                role="button"
                tabIndex={0}
                x={cell.x}
                y={cell.y}
                width={cell.w}
                height={cell.h}
                data-area-id={cell.id}
                data-selected={selectedAreaId === cell.id}
                aria-pressed={selectedAreaId === cell.id}
                aria-label={`Analysis area ${cell.ordinal}`}
                onClick={() => onSelectArea(cell.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectArea(cell.id);
                  }
                }}
              />
              <text
                className="map-label"
                x={cell.x + cell.w / 2}
                y={cell.y + cell.h / 2 + 3}
                textAnchor="middle"
              >
                {cell.ordinal}
              </text>
            </g>
          ))}
        </svg>
        <p className="area-once">{MAP_CLICK}</p>
      </div>
      <MapLegend mode={mode} />
    </section>
  );
}
