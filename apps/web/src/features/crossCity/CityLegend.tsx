import { outlineColorForCity } from "./colors";
import { CROSS_CITY_CITY_ALLOWLIST, type CrossCityId } from "./types";

type CityLegendProps = {
  activeCityIds: readonly CrossCityId[];
  selectedCityId: CrossCityId;
  onToggle: (cityId: CrossCityId) => void;
  onIsolate: (cityId: CrossCityId) => void;
  onShowAll: () => void;
};

export function CityLegend({
  activeCityIds,
  selectedCityId,
  onToggle,
  onIsolate,
  onShowAll,
}: CityLegendProps) {
  return (
    <div className="hx-cc-legend" data-testid="cross-city-legend">
      <div className="hx-cc-legend-head">
        <p className="hx-kicker">City legend</p>
        <button type="button" className="hx-cc-legend-show-all" onClick={onShowAll}>
          Show all
        </button>
      </div>
      <ul className="hx-cc-legend-list">
        {CROSS_CITY_CITY_ALLOWLIST.map((city) => {
          const active = activeCityIds.includes(city.id);
          const selected = selectedCityId === city.id;
          return (
            <li key={city.id} data-active={active ? "true" : "false"} data-selected={selected ? "true" : "false"}>
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
                <span>{city.shortLabel}</span>
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
