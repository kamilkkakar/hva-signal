import { useEffect, useMemo, useState } from "react";
import { BubbleExplorer } from "./BubbleExplorer";
import { CityLegend } from "./CityLegend";
import { CitySelector } from "./CitySelector";
import { CompareLensPanel, CompareLensTabs, type CompareLensId } from "./CompareLenses";
import { fetchCrossCityMetrics } from "./fetchMetrics";
import { SnapshotLens } from "./SnapshotLens";
import { TimeLens } from "./TimeLens";
import {
  CROSS_CITY_AXIS_OPTIONS,
  CROSS_CITY_CITY_ALLOWLIST,
  CROSS_CITY_COMPARISON_CLOCK_LOCAL,
  CROSS_CITY_DEFAULT_ENCODINGS,
  CROSS_CITY_FILL_OPTIONS,
  cityMeta,
  type CrossCityFillKey,
  type CrossCityId,
  type CrossCityMetricKey,
  type CrossCityMetricsResponse,
} from "./types";
import "./crossCity.css";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: CrossCityMetricsResponse }
  | { status: "error"; message: string };

export const CROSS_CITY_SECTION_COPY = {
  kicker: "COMPARE ACROSS CITIES",
  title: "Cross-City Explorer",
  lead: "Observed pattern across cities at one comparison clock — descriptive, not causal.",
  missing:
    "Missing fill values use a hatched pattern. Areas missing X or Y stay off the plot.",
  guided: "Ask which cities share a warmer / lower-canopy pattern — then return to Explore City.",
} as const;

/** Matched-instants package id when Gate 8 evidence lands; null keeps Time lens blocked. */
export const CROSS_CITY_MATCHED_INSTANTS_PACKAGE_ID: string | null = null;

const ALL_CITY_IDS = CROSS_CITY_CITY_ALLOWLIST.map((city) => city.id);

function includesCity(
  cities: readonly CrossCityId[],
  cityId: CrossCityId,
): boolean {
  return cities.includes(cityId);
}

export function CrossCitySection() {
  const [selectedCityId, setSelectedCityId] = useState<CrossCityId>("phoenix-az");
  const [activeCityIds, setActiveCityIds] = useState<readonly CrossCityId[]>(ALL_CITY_IDS);
  const [xMetric, setXMetric] = useState<CrossCityMetricKey>(CROSS_CITY_DEFAULT_ENCODINGS.x);
  const [yMetric, setYMetric] = useState<CrossCityMetricKey>(CROSS_CITY_DEFAULT_ENCODINGS.y);
  const [fillMetric, setFillMetric] = useState<CrossCityFillKey>(CROSS_CITY_DEFAULT_ENCODINGS.fill);
  const [forceComparisonScale, setForceComparisonScale] = useState(false);
  const [lens, setLens] = useState<CompareLensId>("snapshot");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const timeEnabled = Boolean(CROSS_CITY_MATCHED_INSTANTS_PACKAGE_ID);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchCrossCityMetrics();
        if (!cancelled) {
          setState({ status: "ready", data });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            status: "error",
            message: error instanceof Error ? error.message : "Cross-city metrics are unavailable.",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selection = cityMeta(selectedCityId);
  const areaAnalysisHref =
    selection.localAreaAnalysis === "published" ? "#happening" : null;
  const comparisonClock =
    state.status === "ready"
      ? state.data.comparisonClockLocal || CROSS_CITY_COMPARISON_CLOCK_LOCAL
      : CROSS_CITY_COMPARISON_CLOCK_LOCAL;

  const summary = useMemo(() => {
    if (state.status !== "ready") {
      return { areas: 0, cities: 0, withTemp: 0 };
    }
    const visible = state.data.areas.filter((area) => includesCity(activeCityIds, area.cityId));
    return {
      areas: visible.length,
      cities: new Set(visible.map((area) => area.cityId)).size,
      withTemp: visible.filter((area) => area.metrics.selectedTimeTemperatureC != null).length,
    };
  }, [activeCityIds, state]);

  function showAll() {
    setActiveCityIds(ALL_CITY_IDS);
    setForceComparisonScale(false);
  }

  function toggleCity(cityId: CrossCityId) {
    setActiveCityIds((current) => {
      const next = includesCity(current, cityId)
        ? current.filter((value) => value !== cityId)
        : [...current, cityId];
      if (next.length !== 1) {
        setForceComparisonScale(false);
      }
      return next;
    });
  }

  function isolateCity(cityId: CrossCityId) {
    setSelectedCityId(cityId);
    setActiveCityIds([cityId]);
    setForceComparisonScale(false);
  }

  function selectCity(cityId: CrossCityId) {
    setSelectedCityId(cityId);
    setActiveCityIds((current) =>
      includesCity(current, cityId) ? current : [...current, cityId],
    );
  }

  return (
    <section
      className="hx-section hx-cc-section hx-level-1"
      id="cross-city"
      data-testid="cross-city-section"
      aria-labelledby="cross-city-title"
    >
      <p className="hx-kicker">{CROSS_CITY_SECTION_COPY.kicker}</p>
      <h2 id="cross-city-title">{CROSS_CITY_SECTION_COPY.title}</h2>
      <p className="hx-section-lead">{CROSS_CITY_SECTION_COPY.lead}</p>
      <p className="hx-note" data-testid="cross-city-guided">
        {CROSS_CITY_SECTION_COPY.guided}
      </p>
      <p className="hx-note" data-testid="cross-city-clock">
        Comparison clock: {comparisonClock} · FortyGuard Type-1 TCM
      </p>

      <CompareLensTabs lens={lens} onLensChange={setLens} timeEnabled={timeEnabled} />

      {state.status === "loading" ? (
        <div className="hx-cc-state" data-testid="cross-city-loading">
          <p>Loading published cross-city metrics.</p>
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="hx-cc-state" data-testid="cross-city-error">
          <p>Cross-city comparison is not available yet.</p>
          <p className="hx-note">{state.message}</p>
        </div>
      ) : null}

      {state.status === "ready" && state.data.areas.length === 0 ? (
        <div className="hx-cc-state" data-testid="cross-city-empty">
          <p>No published cross-city areas are available yet.</p>
        </div>
      ) : null}

      {state.status === "ready" && state.data.areas.length > 0 ? (
        <CompareLensPanel
          lens={lens}
          snapshot={
            <>
              <SnapshotLens
                areas={state.data.areas}
                activeCityIds={activeCityIds}
                comparisonClock={comparisonClock}
              />
              <div className="hx-cc-summary" data-testid="cross-city-summary">
                <p>
                  {summary.cities} cities · {summary.areas} areas · {comparisonClock} local · Type-1
                  TCM
                </p>
              </div>
              <CityLegend
                activeCityIds={activeCityIds}
                selectedCityId={selectedCityId}
                fillMetric="selectedTimeTemperatureC"
                onToggle={toggleCity}
                onIsolate={isolateCity}
                onShowAll={showAll}
              />
            </>
          }
          context={
            <>
              <div className="hx-cc-controls hx-cc-controls-compact">
                <CitySelector selectedCityId={selectedCityId} onSelect={selectCity} />
                <div className="hx-cc-open-panel">
                  <p className="hx-kicker">Area analysis</p>
                  {areaAnalysisHref ? (
                    <a className="hx-cc-open-link" href={areaAnalysisHref}>
                      Open Phoenix analysis
                    </a>
                  ) : (
                    <p className="hx-note">Level-1 comparison only for {selection.shortLabel}.</p>
                  )}
                </div>
                <div className="hx-cc-open-panel" data-testid="cross-city-axis-controls">
                  <p className="hx-kicker">Axes</p>
                  <label className="hx-cc-field">
                    <span>X</span>
                    <select
                      value={xMetric}
                      aria-label="X axis metric"
                      data-testid="cross-city-x-select"
                      onChange={(event) => setXMetric(event.target.value as CrossCityMetricKey)}
                    >
                      {CROSS_CITY_AXIS_OPTIONS.map((option) => (
                        <option key={option.key} value={option.key}>
                          {option.shortLabel}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="hx-cc-field">
                    <span>Y</span>
                    <select
                      value={yMetric}
                      aria-label="Y axis metric"
                      data-testid="cross-city-y-select"
                      onChange={(event) => setYMetric(event.target.value as CrossCityMetricKey)}
                    >
                      {CROSS_CITY_AXIS_OPTIONS.map((option) => (
                        <option key={option.key} value={option.key}>
                          {option.shortLabel}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="hx-cc-open-panel" data-testid="cross-city-fill-controls">
                  <p className="hx-kicker">Fill</p>
                  <div className="hx-cc-fill-buttons">
                    {CROSS_CITY_FILL_OPTIONS.map((option) => {
                      const testId =
                        option.key === "treeCanopyPct"
                          ? "cross-city-fill-canopy"
                          : option.key === "selectedTimeTemperatureC"
                            ? "cross-city-fill-temperature"
                            : option.key === "medianHouseholdIncomeUsd"
                              ? "cross-city-fill-income"
                              : option.key === "olderHousingPct"
                                ? "cross-city-fill-older-housing"
                                : "cross-city-fill-none";
                      return (
                        <button
                          key={option.key}
                          type="button"
                          className="hx-cc-open-link"
                          data-testid={testId}
                          aria-pressed={fillMetric === option.key}
                          onClick={() => setFillMetric(option.key)}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
              <p className="hx-note">{CROSS_CITY_SECTION_COPY.missing}</p>
              <div className="hx-cc-summary" data-testid="cross-city-summary">
                <p>
                  {summary.cities} cities · {summary.areas} areas · scatter preserved
                </p>
                <details className="hx-cc-methods">
                  <summary>Methods &amp; encoding</summary>
                  <p>
                    Default encodings: X = tree canopy (%), Y = selected-time temperature (°C), size
                    = population, city = hue family. Patterns are descriptive only.
                  </p>
                </details>
              </div>
              <CityLegend
                activeCityIds={activeCityIds}
                selectedCityId={selectedCityId}
                fillMetric={fillMetric}
                onToggle={toggleCity}
                onIsolate={isolateCity}
                onShowAll={showAll}
              />
              <BubbleExplorer
                records={state.data.areas}
                activeCityIds={activeCityIds}
                selectedCityId={selectedCityId}
                xMetric={xMetric}
                yMetric={yMetric}
                fillMetric={fillMetric}
                forceComparisonScale={forceComparisonScale}
                onRequestComparisonScale={() => setForceComparisonScale(true)}
                onRequestFocusedScale={() => setForceComparisonScale(false)}
              />
            </>
          }
          time={
            <TimeLens
              packageId={CROSS_CITY_MATCHED_INSTANTS_PACKAGE_ID}
              reason="Time lens waits for CROSS_CITY_MATCHED_INSTANTS_V1 evidence. Existing 15:00 snapshot stays on Snapshot/Context."
            />
          }
        />
      ) : null}
    </section>
  );
}
