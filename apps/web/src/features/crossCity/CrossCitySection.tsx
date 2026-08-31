import { useEffect, useMemo, useState } from "react";
import { BubbleExplorer } from "./BubbleExplorer";
import { CityLegend } from "./CityLegend";
import { CitySelector } from "./CitySelector";
import { fetchCrossCityMetrics } from "./fetchMetrics";
import {
  CROSS_CITY_CITY_ALLOWLIST,
  CROSS_CITY_COMPARISON_CLOCK_LOCAL,
  cityMeta,
  type CrossCityId,
  type CrossCityMetricsResponse,
} from "./types";
import "./crossCity.css";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; data: CrossCityMetricsResponse }
  | { status: "error"; message: string };

export const CROSS_CITY_SECTION_COPY = {
  kicker: "06 · Cross-city explorer",
  title: "How do published areas compare across cities?",
  lead:
    "Compare selected-time temperature, household income, population, and tree canopy across published analysis areas at the same local date and time.",
  caution:
    "This section is descriptive. It does not score cities, rank need, or prescribe an intervention.",
  missing:
    "Missing tree canopy is shown with a hatched fill. Areas missing temperature or income stay off the plot and are counted below.",
} as const;

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
  const [state, setState] = useState<LoadState>({ status: "loading" });

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
      return { areas: 0, cities: 0 };
    }
    const visible = state.data.areas.filter((area) => includesCity(activeCityIds, area.cityId));
    return {
      areas: visible.length,
      cities: new Set(visible.map((area) => area.cityId)).size,
    };
  }, [activeCityIds, state]);

  function showAll() {
    setActiveCityIds(ALL_CITY_IDS);
  }

  function toggleCity(cityId: CrossCityId) {
    setActiveCityIds((current) =>
      includesCity(current, cityId)
        ? current.filter((value) => value !== cityId)
        : [...current, cityId],
    );
  }

  function isolateCity(cityId: CrossCityId) {
    setSelectedCityId(cityId);
    setActiveCityIds([cityId]);
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
      <p className="hx-note">{CROSS_CITY_SECTION_COPY.caution}</p>
      <p className="hx-note" data-testid="cross-city-clock">
        Comparison clock: same local date and time across cities, {comparisonClock}.
      </p>

      <div className="hx-cc-controls">
        <CitySelector selectedCityId={selectedCityId} onSelect={selectCity} />
        <div className="hx-cc-open-panel">
          <p className="hx-kicker">Area analysis</p>
          {areaAnalysisHref ? (
            <>
              <a className="hx-cc-open-link" href={areaAnalysisHref}>
                Open area analysis
              </a>
              <p className="hx-note">Phoenix links back to the published local analysis above.</p>
            </>
          ) : (
            <>
              <button type="button" className="hx-cc-open-link" disabled>
                Open area analysis
              </button>
              <p className="hx-note">
                Level-1 comparison only for {selection.shortLabel}. Local area analysis is not
                published on this surface.
              </p>
            </>
          )}
        </div>
      </div>

      <p className="hx-note">{CROSS_CITY_SECTION_COPY.missing}</p>

      {state.status === "loading" ? (
        <div className="hx-cc-state" data-testid="cross-city-loading">
          <p>Loading published cross-city metrics.</p>
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="hx-cc-state" data-testid="cross-city-error">
          <p>Cross-city comparison is not available yet. Phoenix remains the local published baseline above.</p>
          <p className="hx-note">{state.message}</p>
        </div>
      ) : null}

      {state.status === "ready" && state.data.areas.length === 0 ? (
        <div className="hx-cc-state" data-testid="cross-city-empty">
          <p>No published cross-city areas are available from the current API response yet.</p>
        </div>
      ) : null}

      {state.status === "ready" && state.data.areas.length > 0 ? (
        <>
          <div className="hx-cc-summary" data-testid="cross-city-summary">
            <p>
              Showing {summary.areas} published areas across {summary.cities}{" "}
              {summary.cities === 1 ? "city" : "cities"} in the current filter.
            </p>
          </div>
          <CityLegend
            activeCityIds={activeCityIds}
            selectedCityId={selectedCityId}
            onToggle={toggleCity}
            onIsolate={isolateCity}
            onShowAll={showAll}
          />
          <BubbleExplorer
            records={state.data.areas}
            activeCityIds={activeCityIds}
            selectedCityId={selectedCityId}
          />
        </>
      ) : null}
    </section>
  );
}
