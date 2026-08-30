import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { GEOID_SECONDARY, METRIC_CHANGE, METRIC_HISTORY, METRIC_TEMP } from "./copy";
import { formatDeltaC, formatTempC } from "./format";
import type { HistoricalPositionView } from "./historicalPosition";
import { AreaSelector } from "./AreaSelector";

type ThermalHeroProps = {
  selectedZoneId: string | null;
  onSelect: (geoid: string) => void;
  temperatureC: number | null;
  observationStamp: string | null;
  history: HistoricalPositionView;
  change2024vs2022: number | null;
};

export function ThermalHero({
  selectedZoneId,
  onSelect,
  temperatureC,
  observationStamp,
  history,
  change2024vs2022,
}: ThermalHeroProps) {
  const label = analysisAreaLabel(selectedZoneId) ?? "Select an analysis area";
  return (
    <section className="hx-hero" data-testid="thermal-hero" aria-label="Selected analysis area summary">
      <div className="hx-hero-identity">
        <AreaSelector selectedZoneId={selectedZoneId} onSelect={onSelect} />
        <div>
          <p className="hx-kicker">Selected area</p>
          <h2 data-testid="selected-area-label">{label}</h2>
          {selectedZoneId ? (
            <details className="hx-geoid">
              <summary>{GEOID_SECONDARY}</summary>
              <p data-testid="selected-area-geoid">{selectedZoneId}</p>
            </details>
          ) : null}
        </div>
      </div>
      <dl className="hx-metrics">
        <div data-testid="hero-temperature">
          <dt>{METRIC_TEMP}</dt>
          <dd>
            {temperatureC == null ? "—" : formatTempC(temperatureC)}
            {observationStamp ? <span className="hx-metric-note">{observationStamp}</span> : null}
          </dd>
        </div>
        <div data-testid="hero-history">
          <dt>{METRIC_HISTORY}</dt>
          <dd data-withheld={history.withheld ? "true" : "false"}>{history.sentence}</dd>
        </div>
        <div data-testid="hero-matched-change">
          <dt>{METRIC_CHANGE}</dt>
          <dd>{change2024vs2022 == null ? "—" : formatDeltaC(change2024vs2022)}</dd>
        </div>
      </dl>
    </section>
  );
}
