import { useEffect, useState } from "react";
import { CITIES, type CityId, type ObservationMode } from "./types";

type CityControlsProps = {
  cityId: CityId;
  onCityChange: (id: CityId) => void;
  observationMode: ObservationMode;
  onObservationModeChange: (mode: ObservationMode) => void;
  liveDate?: string;
  onLiveDateChange?: (date: string) => void;
  liveTime?: string;
  onLiveTimeChange?: (time: string) => void;
  onRunLive?: () => void;
  liveRunning?: boolean;
  provenanceLine?: string | null;
  /** Public Live is limited to the existing server-owned four-city geography. */
  liveAvailable?: boolean;
};

function cityDisplay(id: CityId): string {
  const city = CITIES.find((item) => item.id === id) ?? CITIES[0];
  return `${city.label}, ${city.state}`;
}

export function CityControls({
  cityId,
  onCityChange,
  observationMode,
  onObservationModeChange,
  liveDate,
  onLiveDateChange,
  liveTime,
  onLiveTimeChange,
  onRunLive,
  liveRunning,
  provenanceLine,
  liveAvailable = false,
}: CityControlsProps) {
  const [liveCityQuery, setLiveCityQuery] = useState(cityDisplay(cityId));

  useEffect(() => {
    setLiveCityQuery(cityDisplay(cityId));
  }, [cityId]);

  const updateLiveCity = (value: string) => {
    setLiveCityQuery(value);
    const normalized = value.trim().toLowerCase();
    const match = CITIES.find(
      (item) =>
        `${item.label}, ${item.state}`.toLowerCase() === normalized ||
        item.label.toLowerCase() === normalized,
    );
    if (match) onCityChange(match.id);
  };

  return (
    <div className="ws-city-controls" data-testid="city-controls">
      <div className="ws-controls-row">
        <label className="ws-control-field" data-testid="city-selector">
          <span className="ws-control-label">City</span>
          <select
            value={cityId}
            aria-label="Select city"
            onChange={(e) => onCityChange(e.target.value as CityId)}
          >
            {CITIES.map((city) => (
              <option key={city.id} value={city.id}>
                {city.label}, {city.state}
              </option>
            ))}
          </select>
        </label>

        {liveAvailable ? (
          <div
            className="ws-obs-toggle"
            role="radiogroup"
            aria-label="Observation type"
            data-testid="observation-toggle"
          >
            <span className="ws-control-label">Observation</span>
            <div className="ws-obs-buttons">
              <button
                type="button"
                role="radio"
                aria-checked={observationMode === "published"}
                className="ws-obs-btn"
                data-testid="obs-published"
                onClick={() => onObservationModeChange("published")}
              >
                Published
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={observationMode === "live"}
                className="ws-obs-btn"
                data-testid="obs-live"
                onClick={() => onObservationModeChange("live")}
              >
                Live
              </button>
            </div>
          </div>
        ) : (
          <div className="ws-obs-toggle" data-testid="observation-published-only">
            <span className="ws-control-label">Observation</span>
            <span className="ws-published-badge">Published</span>
          </div>
        )}

        {liveAvailable && observationMode === "live" ? (
          <div className="ws-live-controls" data-testid="live-controls">
            <label className="ws-control-field ws-live-city-search">
              <span className="ws-control-label">Search supported city</span>
              <input
                type="search"
                list="hva-live-supported-cities"
                value={liveCityQuery}
                onChange={(e) => updateLiveCity(e.target.value)}
                aria-label="Search supported live city"
                data-testid="live-city-search"
              />
              <datalist id="hva-live-supported-cities">
                {CITIES.map((item) => (
                  <option key={item.id} value={`${item.label}, ${item.state}`} />
                ))}
              </datalist>
            </label>
            <label className="ws-control-field">
              <span className="ws-control-label">Date</span>
              <input
                type="date"
                value={liveDate ?? ""}
                onChange={(e) => onLiveDateChange?.(e.target.value)}
                aria-label="Observation date"
              />
            </label>
            <label className="ws-control-field">
              <span className="ws-control-label">Local time</span>
              <input
                type="time"
                value={liveTime ?? ""}
                step="3600"
                onChange={(e) => onLiveTimeChange?.(e.target.value)}
                aria-label="Observation time"
              />
            </label>
            <button
              type="button"
              className="ws-run-btn"
              data-testid="run-live"
              onClick={onRunLive}
              disabled={liveRunning}
            >
              {liveRunning ? "Running…" : "Run observation"}
            </button>
            <p className="ws-live-scope" data-testid="live-scope-note">
              Live is bounded to the four published city geographies. The server owns the AOI,
              100 m TCM request and provider credentials.
            </p>
          </div>
        ) : null}
      </div>
      {provenanceLine ? (
        <p className="ws-provenance" data-testid="observation-provenance">
          {provenanceLine}
        </p>
      ) : null}
    </div>
  );
}
