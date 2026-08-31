import { outlineColorForCity, hueFamilyLabel } from "./colors";
import { CROSS_CITY_CITY_ALLOWLIST, type CrossCityId } from "./types";
import { ACTIVE_CROSS_CITY_CANOPY_DISPLAY_SCALE } from "./canopyDisplayScale";
import type { CrossCityFillKey } from "./types";
import { metricLabel } from "./types";

type CityLegendProps = {
  activeCityIds: readonly CrossCityId[];
  selectedCityId: CrossCityId;
  fillMetric: CrossCityFillKey;
  onToggle: (cityId: CrossCityId) => void;
  onIsolate: (cityId: CrossCityId) => void;
  onShowAll: () => void;
};

export function CityLegend({
  activeCityIds,
  selectedCityId,
  fillMetric,
  onToggle,
  onIsolate,
  onShowAll,
}: CityLegendProps) {
  const shadeLabel = fillMetric === "none" ? "none (medium city fill)" : metricLabel(fillMetric);
  const canopy = ACTIVE_CROSS_CITY_CANOPY_DISPLAY_SCALE;

  return (
    <div className="hx-cc-legend" data-testid="cross-city-legend">
      <div className="hx-cc-legend-head">
        <div>
          <p className="hx-kicker">Encoding legend</p>
          <p className="hx-note" data-testid="cross-city-legend-encoding">
            Color family = city · Shade = {shadeLabel}
          </p>
        </div>
        <button type="button" className="hx-cc-legend-show-all" onClick={onShowAll}>
          Show all
        </button>
      </div>

      {fillMetric === "treeCanopyPct" ? (
        <p className="hx-note" data-testid="cross-city-canopy-scale">
          Shared canopy scale ({canopy.version}): {canopy.domainMin}–{canopy.domainMax}
          {canopy.unit} · end-cap · not stretched to visible cities
        </p>
      ) : null}

      <ul className="hx-cc-legend-list">
        {CROSS_CITY_CITY_ALLOWLIST.map((city) => {
          const active = activeCityIds.includes(city.id);
          const selected = selectedCityId === city.id;
          return (
            <li
              key={city.id}
              data-active={active ? "true" : "false"}
              data-selected={selected ? "true" : "false"}
            >
              <button
                type="button"
                className="hx-cc-legend-toggle"
                aria-pressed={active}
                onClick={() => onToggle(city.id)}
              >
                <span
                  className="hx-cc-legend-swatch"
                  aria-hidden="true"
                  style={{ backgroundColor: outlineColorForCity(city.id) }}
                />
                <span>
                  {city.shortLabel}
                  <span className="hx-cc-legend-hue"> · {hueFamilyLabel(city.id)}</span>
                </span>
              </button>
              <button
                type="button"
                className="hx-cc-legend-only"
                onClick={() => onIsolate(city.id)}
                aria-label={`Only show ${city.label}`}
              >
                Only
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
