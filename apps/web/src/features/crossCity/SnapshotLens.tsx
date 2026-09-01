import { computeSharedTempScale, cityHue, rangePosition } from "./sharedTempScale";
import type { CrossCityAreaRecord, CrossCityId } from "./types";

type SnapshotLensProps = {
  areas: readonly CrossCityAreaRecord[];
  activeCityIds: readonly CrossCityId[];
  comparisonClock: string;
};

export function SnapshotLens({ areas, activeCityIds, comparisonClock }: SnapshotLensProps) {
  const scale = computeSharedTempScale(areas, activeCityIds);
  if (!scale) {
    return (
      <div className="hx-cc-snapshot" data-testid="compare-snapshot-lens">
        <p className="hx-note">No published temperatures for the shared snapshot scale.</p>
      </div>
    );
  }

  const span = Math.max(0.1, scale.maxC - scale.minC);

  return (
    <div className="hx-cc-snapshot" data-testid="compare-snapshot-lens">
      <header className="hx-cc-snapshot-header">
        <p className="hx-kicker">Snapshot</p>
        <h3>Shared temperature range</h3>
        <p className="hx-note" data-testid="compare-snapshot-clock">
          Comparison clock {comparisonClock}. Same °C scale for every city — descriptive only, not
          a city-wide ranking.
        </p>
      </header>

      <div
        className="hx-cc-shared-scale"
        data-testid="compare-shared-scale"
        data-min={scale.minC.toFixed(1)}
        data-max={scale.maxC.toFixed(1)}
      >
        <div className="hx-cc-shared-scale-bar" aria-hidden="true" />
        <div className="hx-cc-shared-scale-labels">
          <span>{scale.minC.toFixed(1)} °C</span>
          <span>shared span ≈ {span.toFixed(1)} °C</span>
          <span>{scale.maxC.toFixed(1)} °C</span>
        </div>
      </div>

      <ul className="hx-cc-city-ranges" data-testid="compare-city-ranges">
        {scale.cities.map((city) => {
          if (city.minC == null || city.maxC == null) {
            return (
              <li key={city.cityId} data-city={city.cityId} data-missing="true">
                <span className="hx-cc-city-swatch" style={{ background: cityHue(city.cityId) }} />
                <div>
                  <strong>{city.shortLabel}</strong>
                  <p className="hx-note">Temperature not published</p>
                </div>
              </li>
            );
          }
          const left = rangePosition(city.minC, scale.minC, scale.maxC);
          const right = rangePosition(city.maxC, scale.minC, scale.maxC);
          const mid = (left + right) / 2;
          return (
            <li key={city.cityId} data-city={city.cityId}>
              <span className="hx-cc-city-swatch" style={{ background: cityHue(city.cityId) }} />
              <div className="hx-cc-city-range-body">
                <div className="hx-cc-city-range-title">
                  <strong>{city.shortLabel}</strong>
                  <span data-testid={`compare-range-${city.cityId}`}>
                    {city.minC.toFixed(1)}–{city.maxC.toFixed(1)} °C · {city.count} zones
                  </span>
                </div>
                <div className="hx-cc-city-range-track" aria-hidden="true">
                  <span
                    className="hx-cc-city-range-fill"
                    style={{
                      left: `${left * 100}%`,
                      width: `${Math.max(2, (right - left) * 100)}%`,
                      background: cityHue(city.cityId),
                    }}
                  />
                  <span
                    className="hx-cc-city-range-marker"
                    style={{ left: `${mid * 100}%`, background: cityHue(city.cityId) }}
                    title="Midpoint of city range"
                  />
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="hx-note">
        Bars sit on one shared scale. Zone means inside a city are not generalized to the whole
        municipality.
      </p>
    </div>
  );
}
