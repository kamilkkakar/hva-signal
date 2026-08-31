import { analysisAreaLabel, resolveIdentity } from "@/features/selectedAreaStory/identity";
import { formatDeltaC, formatTempC } from "./format";
import type { HistoricalPositionView, SpatialDifferentiationView } from "./historicalPosition";
import { AreaSelector } from "./AreaSelector";
import {
  GEOID_SECONDARY,
  HISTORY_CARD_TITLE,
  HISTORY_UNAVAILABLE_WHY,
  METRIC_CHANGE,
  METRIC_CHANGE_WINDOW,
  METRIC_TEMP,
  RANKING_WITHHELD_TITLE,
  RANKING_SUPPORTED_TITLE,
  SPATIAL_CARD_TITLE,
} from "./copy";

type ThermalHeroProps = {
  selectedZoneId: string | null;
  onSelect: (geoid: string) => void;
  temperatureC: number | null;
  observationStamp: string | null;
  observationDateLabel?: string | null;
  history: HistoricalPositionView;
  spatial: SpatialDifferentiationView;
  change2024vs2022: number | null;
};

export function ThermalHero({
  selectedZoneId,
  onSelect,
  temperatureC,
  observationStamp,
  observationDateLabel = null,
  history,
  spatial,
  change2024vs2022,
}: ThermalHeroProps) {
  const label = analysisAreaLabel(selectedZoneId) ?? "Select an analysis area";
  const secondary = selectedZoneId
    ? (resolveIdentity(selectedZoneId).secondaryLabel ?? null)
    : null;
  const localStamp = observationDateLabel ?? observationStamp ?? null;
  return (
    <section
      className="hx-hero"
      id="happening"
      data-testid="thermal-hero"
      aria-label="Selected analysis area summary"
    >
      <div className="hx-hero-identity">
        <p className="hx-kicker">02 · What did HVA-Signal find?</p>
        <h2 data-testid="selected-area-label">{label}</h2>
        {secondary ? (
          <p className="hx-note" data-testid="selected-area-secondary">
            {secondary}
          </p>
        ) : null}
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
          {localStamp ? (
            <span className="hx-metric-note" data-testid="hero-observation-stamp">
              {localStamp}
            </span>
          ) : null}
        </div>
        <div data-testid="hero-matched-change">
          <dd>{change2024vs2022 == null ? "—" : formatDeltaC(change2024vs2022)}</dd>
          <dt>{METRIC_CHANGE}</dt>
          <span className="hx-metric-note" data-testid="hero-matched-window">
            {METRIC_CHANGE_WINDOW}
          </span>
        </div>
      </dl>
      <div id="history" className="hx-compare-grid" data-testid="history-spatial-pair">
        <aside
          className={
            history.status === "unavailable" ? "hx-trust-note hx-history-unavailable" : "hx-trust-note"
          }
          data-testid="hero-history"
          data-status={history.status}
        >
          <p className="hx-kicker hx-kicker-sub">{HISTORY_CARD_TITLE}</p>
          {history.status === "unavailable" ? (
            <div className="hx-history-unavailable-body">
              <p data-testid="historical-position-sentence">{history.sentence}</p>
              {history.reason ? (
                <details className="hx-history-why" data-testid="historical-position-why">
                  <summary>{HISTORY_UNAVAILABLE_WHY}</summary>
                  <p data-testid="historical-position-reason">{history.reason}</p>
                </details>
              ) : null}
            </div>
          ) : (
            <>
              <p data-testid="historical-position-sentence">{history.sentence}</p>
              {history.reason ? (
                <p data-testid="historical-position-reason" className="hx-note">
                  {history.reason}
                </p>
              ) : null}
            </>
          )}
          <details className="hx-method">
            <summary>How this is calculated</summary>
            <p>
              Own-area historical position compares this selected 03:00 observation with comparable
              historical 03:00 observations for the same analysis area. It is not a cross-area rank.
            </p>
          </details>
        </aside>
        <aside
          className="hx-trust-note"
          data-testid="hero-spatial"
          data-status={spatial.status}
        >
          <p className="hx-kicker">{SPATIAL_CARD_TITLE}</p>
          <p className="hx-kicker hx-kicker-sub" data-testid="spatial-status-title">
            {spatial.status === "withheld"
              ? RANKING_WITHHELD_TITLE
              : spatial.status === "supported"
                ? RANKING_SUPPORTED_TITLE
                : "Status pending"}
          </p>
          <p data-testid="ranking-interpretation">{spatial.sentence}</p>
        </aside>
      </div>
    </section>
  );
}
