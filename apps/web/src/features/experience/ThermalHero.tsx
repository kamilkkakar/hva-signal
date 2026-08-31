import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { formatDeltaC, formatTempC } from "./format";
import type { HistoricalPositionView } from "./historicalPosition";
import { AreaSelector } from "./AreaSelector";
import {
  GEOID_SECONDARY,
  HISTORY_WITHHELD_TRUST,
  METRIC_CHANGE,
  METRIC_TEMP,
  RANKING_WITHHELD_TITLE,
} from "./copy";

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
  const localStamp = observationStamp ?? null;
  return (
    <section
      className="hx-hero"
      id="happening"
      data-testid="thermal-hero"
      aria-label="Selected analysis area summary"
    >
      <div className="hx-hero-identity">
        <p className="hx-kicker">01 · What's happening here?</p>
        <h2 data-testid="selected-area-label">{label}</h2>
        <AreaSelector selectedZoneId={selectedZoneId} onSelect={onSelect} />
        {selectedZoneId ? (
          <details className="hx-geoid">
            <summary>{GEOID_SECONDARY}</summary>
            <p data-testid="selected-area-geoid">{selectedZoneId}</p>
          </details>
        ) : null}
      </div>
      <dl className="hx-metrics">
        <div data-testid="hero-temperature" className="hx-metric-primary">
          <dd>{temperatureC == null ? "—" : formatTempC(temperatureC)}</dd>
          <dt>{METRIC_TEMP}</dt>
          {localStamp ? <span className="hx-metric-note">{localStamp}</span> : null}
        </div>
        <div data-testid="hero-matched-change">
          <dd>{change2024vs2022 == null ? "—" : formatDeltaC(change2024vs2022)}</dd>
          <dt>{METRIC_CHANGE}</dt>
        </div>
      </dl>
      <div id="history" data-testid="evidence-summary">
        <aside
          className="hx-trust-note"
          data-testid="hero-history"
          data-withheld={history.withheld ? "true" : "false"}
        >
          <p className="hx-kicker">02 · How does this compare with history?</p>
          {history.withheld ? (
            <>
              <p className="hx-kicker hx-kicker-sub">{RANKING_WITHHELD_TITLE}</p>
              <p data-testid="ranking-interpretation">{history.sentence}</p>
              <p data-testid="ranking-next" className="hx-note">
                {HISTORY_WITHHELD_TRUST}
              </p>
            </>
          ) : (
            <p data-testid="ranking-interpretation">{history.sentence}</p>
          )}
        </aside>
      </div>
    </section>
  );
}
