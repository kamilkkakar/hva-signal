import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useJobStore } from "@/stores/jobStore";
import { POLL_INTERVAL_MS } from "@/utils/jobPolling";
import { mapLayerFromLimitations, rankingPresentation } from "@/utils/mapLayer";
import {
  PHOENIX_DEMO_DEFAULT_DATETIME_LOCAL,
  phoenixAoiLocalAnalysisTime,
} from "@/utils/phoenixAoiLocalTime";
import { AreaContextBand, MapModeTabs, type MapMode, type ZoneMapProperties } from "@/features/areaContext";
import { composeSelectedAreaStory } from "@/features/selectedAreaStory";
import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { ANALYSIS_AREA_GEOIDS } from "@/features/selectedAreaStory/types";
import { presentThermalB } from "@/features/selectedAreaStory/thermalB";
import { B_CLOCK, B_TIMEZONE } from "@/features/selectedAreaStory/copy";
import {
  synthesizeNarrative,
  presentHistoricalPosition,
  presentSpatialDifferentiation,
  contextComparisonsFromFacts,
  MatchedNightChart,
  ObservedInstantsChart,
} from "@/features/experience";
import { ContextPanel } from "@/features/experience/ContextPanel";
import type { PreparednessEvidenceStatus, SpatialDiffStatus } from "@/features/experience/narrative";
import { judgeMapLayer } from "@/features/judgeShell/layer";
import { MapBand } from "@/features/judgeShell/MapBand";
import { JudgeMap } from "@/features/judgeShell/map/JudgeMap";
import { useAreaEvidence } from "@/features/experience/useAreaEvidence";
import { cachedRangeLabel } from "@/features/judgeShell/signalB/cachedPhoenix";
import { apiUrl } from "@/api/baseUrl";
import type { InteractionCatalog } from "@/features/mapInteraction";
import { catalogFromSnapshot } from "@/features/mapInteraction/fromSnapshot";
import {
  crossCityDisplayName,
  crossCitySecondaryLabel,
} from "@/features/areaIdentity";
import { fetchCrossCityMetrics } from "@/features/crossCity/fetchMetrics";
import type { CrossCityMetricsResponse, CrossCityAreaRecord } from "@/features/crossCity/types";
import { CityControls } from "./CityControls";
import { ZonePanel } from "./ZonePanel";
import { buildStoryActions, contextHighlights } from "./actionEngine";
import { type HvaStage } from "./HvaStoryRail";
import { cityConfig, type CityId, type ObservationMode, type ZoneInfo } from "./types";

const EMPTY_LIMITATIONS: readonly string[] = [];
const DEFAULT_PHOENIX_AREA = ANALYSIS_AREA_GEOIDS[0];

type CityGeometry = {
  type: "FeatureCollection";
  features: Array<{ type: "Feature"; properties: Record<string, unknown>; geometry: unknown }>;
};

function spatialStatusFrom(
  status: ReturnType<typeof presentSpatialDifferentiation>["status"],
): SpatialDiffStatus {
  if (status === "withheld") return "INSUFFICIENT";
  if (status === "supported") return "SUFFICIENT";
  return "UNKNOWN";
}

function buildCrossCityCatalog(
  geometry: CityGeometry,
  records: CrossCityAreaRecord[],
): InteractionCatalog {
  const recordMap = new Map(records.map((r) => [r.areaId, r]));
  const zones = geometry.features.map((f) => {
    const geoid = String(f.properties.GEOID ?? "");
    const record = recordMap.get(geoid);
    return {
      zone_id: geoid,
      mean_temperature_c: record?.metrics.selectedTimeTemperatureC ?? null,
      coverage_status: record?.metrics.selectedTimeTemperatureC != null ? "valid" : "missing",
    };
  });
  return catalogFromSnapshot({
    zones,
    geometry,
    targetTimestamp: "2024-07-08T15:00:00",
    timezone: "America/Phoenix",
    source: "fortyguard_cached",
    dataStatus: "cached",
  });
}

function zoneInfoFromCrossCity(
  record: CrossCityAreaRecord | undefined,
  geoid: string,
  ccCityId: CityId,
): ZoneInfo {
  return {
    geoid,
    label: crossCityDisplayName(ccCityId, geoid),
    secondaryLabel: crossCitySecondaryLabel(ccCityId, geoid),
    temperatureC: record?.metrics.selectedTimeTemperatureC ?? null,
    canopyPct: record?.metrics.treeCanopyPct ?? null,
    incomeUsd: record?.metrics.medianHouseholdIncomeUsd ?? null,
    olderHousingPct: record?.metrics.olderHousingPct ?? null,
    population: record?.metrics.population ?? null,
  };
}

type ExploreCityProps = {
  cityId: CityId;
  onCityChange: (id: CityId) => void;
};

export function ExploreCity({ cityId, onCityChange }: ExploreCityProps) {
  const city = cityConfig(cityId);
  const isPhoenix = city.hasLocalAnalysis;

  const [observationMode, setObservationMode] = useState<ObservationMode>("published");
  const [liveDate, setLiveDate] = useState("2024-07-08");
  const [liveTime, setLiveTime] = useState("15:00");
  const [liveRunning, setLiveRunning] = useState(false);
  const [mapMode, setMapMode] = useState<MapMode>("THERMAL");
  const [storyStage, setStoryStage] = useState<HvaStage>("heat");
  const [contextZones, setContextZones] = useState<ZoneMapProperties[]>([]);
  const [crossCityData, setCrossCityData] = useState<CrossCityMetricsResponse | null>(null);
  const [cityGeometry, setCityGeometry] = useState<CityGeometry | null>(null);
  const [cityGeoIds, setCityGeoIds] = useState<string[]>([]);
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(
    isPhoenix ? DEFAULT_PHOENIX_AREA : null,
  );

  // Phoenix job store
  const snapshot = useJobStore((s) => s.snapshot);
  const lastRequest = useJobStore((s) => s.lastRequest);
  const submitting = useJobStore((s) => s.submitting);
  const polling = useJobStore((s) => s.polling);
  const jobId = useJobStore((s) => s.jobId);
  const poll = useJobStore((s) => s.poll);
  const submit = useJobStore((s) => s.submit);

  useEffect(() => {
    if (!isPhoenix) return;
    let cancelled = false;
    const draft = {
      area_id: "phoenix-demo",
      analysis_time: phoenixAoiLocalAnalysisTime(PHOENIX_DEMO_DEFAULT_DATETIME_LOCAL),
      analysis_mode: "retrospective" as const,
      horizon_hours: 12,
      granularity_m: 100,
      data_mode: "replay" as const,
    };
    void (async () => {
      for (let attempt = 0; attempt < 8 && !cancelled; attempt++) {
        try { await submit(draft); return; } catch { await new Promise((r) => setTimeout(r, 400 * (attempt + 1))); }
      }
    })();
    return () => { cancelled = true; };
  }, [submit, isPhoenix]);

  useEffect(() => {
    if (!isPhoenix || !polling || !jobId) return;
    void poll();
    const timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [jobId, poll, polling, isPhoenix]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchCrossCityMetrics();
        if (!cancelled) setCrossCityData(data);
      } catch { /* silent */ }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (isPhoenix) { setCityGeometry(null); setCityGeoIds([]); return; }
    let cancelled = false;
    void (async () => {
      try {
        const resp = await fetch(apiUrl(`/api/v1/cross-city/cities/${city.apiCityId}/geometry`), {
          headers: { Accept: "application/geo+json" },
        });
        if (!resp.ok) throw new Error(`${resp.status}`);
        const geojson = (await resp.json()) as CityGeometry;
        if (cancelled) return;
        setCityGeometry(geojson);
        const ids = geojson.features.map((f) => String(f.properties.GEOID ?? "")).filter(Boolean);
        setCityGeoIds(ids);
        if (!ids.includes(selectedAreaId ?? "")) {
          setSelectedAreaId(ids[0] ?? null);
        }
      } catch {
        if (!cancelled) { setCityGeometry(null); setCityGeoIds([]); }
      }
    })();
    return () => { cancelled = true; };
  }, [cityId, isPhoenix, city.apiCityId]); // eslint-disable-line react-hooks/exhaustive-deps

  const prevCity = useRef(cityId);
  useEffect(() => {
    if (prevCity.current !== cityId) {
      prevCity.current = cityId;
      if (isPhoenix) setSelectedAreaId(DEFAULT_PHOENIX_AREA);
    }
  }, [cityId, isPhoenix]);

  const selectArea = useCallback(
    (geoid: string | null) => {
      if (!geoid) return;
      if (isPhoenix) {
        if ((ANALYSIS_AREA_GEOIDS as readonly string[]).includes(geoid)) setSelectedAreaId(geoid);
      } else {
        if (cityGeoIds.includes(geoid)) setSelectedAreaId(geoid);
      }
    },
    [isPhoenix, cityGeoIds],
  );

  // Phoenix evidence
  const limitations = snapshot?.result?.system_limitations ?? EMPTY_LIMITATIONS;
  const ranking = useMemo(() => rankingPresentation(snapshot?.result?.zones), [snapshot?.result?.zones]);
  const layer = useMemo(
    () => judgeMapLayer(mapLayerFromLimitations(limitations), ranking, snapshot?.result != null),
    [limitations, ranking, snapshot?.result],
  );
  const evidence = useAreaEvidence(isPhoenix ? selectedAreaId : null);
  const thermalB = presentThermalB(isPhoenix ? selectedAreaId : null);
  const history = presentHistoricalPosition(snapshot?.result, isPhoenix ? selectedAreaId : null);
  const spatial = presentSpatialDifferentiation(snapshot?.result, isPhoenix ? selectedAreaId : null);
  const observationStamp = `${B_CLOCK} ${B_TIMEZONE}`;
  const story = composeSelectedAreaStory({
    selectedGeoid: isPhoenix ? selectedAreaId : null,
    result: snapshot?.result ?? null,
    context: evidence.context?.selected ?? null,
    document: evidence.context,
  });
  const comparisons = contextComparisonsFromFacts(story.questions.different.facts);

  // Narrative synthesis (Phoenix only)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const synthesis = useMemo(() => {
    if (!isPhoenix) return null;
    return synthesizeNarrative({
      areaLabel: analysisAreaLabel(selectedAreaId),
      analysisAreaCount: ANALYSIS_AREA_GEOIDS.length,
      selectedTemperatureC: thermalB.temperatureC,
      observationStamp: observationStamp.split(" ")[0] ?? "",
      spatialDiff: spatialStatusFrom(spatial.status),
      historicalPosition: {
        status: history.status === "available" ? "AVAILABLE" : "UNAVAILABLE",
        percent: history.percent,
        sentence: history.sentence,
      },
      matchedChangeC: evidence.matched.change2024vs2022,
      geographyMedianChangeC: evidence.matched.medianChange,
      matchedNightsTotal: evidence.matched.nightsTotal,
      observedHighC: null,
      observedHighLabel: null,
      contextComparisons: comparisons,
      preparedness: story.questions.support.status as PreparednessEvidenceStatus,
      thermalAvailable: thermalB.temperatureC != null,
    });
  }, [isPhoenix, selectedAreaId, thermalB.temperatureC, spatial.status, history, evidence.matched, comparisons, story.questions.support.status, observationStamp]);

  const crossCityCatalog = useMemo<InteractionCatalog | null>(() => {
    if (isPhoenix || !cityGeometry || !crossCityData) return null;
    const cityRecords = crossCityData.areas.filter((a) => a.cityId === cityId);
    return buildCrossCityCatalog(cityGeometry, cityRecords);
  }, [isPhoenix, cityGeometry, crossCityData, cityId]);

  const zoneInfo = useMemo<ZoneInfo | null>(() => {
    if (!selectedAreaId) return null;
    if (isPhoenix) {
      return {
        geoid: selectedAreaId,
        label: analysisAreaLabel(selectedAreaId) ?? selectedAreaId,
        secondaryLabel: "Census Tract \u00b7 Phoenix, AZ",
        temperatureC: thermalB.temperatureC,
        canopyPct: null,
        incomeUsd: null,
        olderHousingPct: null,
        population: null,
      };
    }
    const record = crossCityData?.areas.find((a) => a.cityId === cityId && a.areaId === selectedAreaId);
    return zoneInfoFromCrossCity(record, selectedAreaId, cityId);
  }, [selectedAreaId, isPhoenix, thermalB.temperatureC, crossCityData, cityId]);

  const rangeLabel = useMemo(() => {
    if (isPhoenix) return cachedRangeLabel();
    if (!crossCityData) return null;
    const temps = crossCityData.areas
      .filter((a) => a.cityId === cityId)
      .map((r) => r.metrics.selectedTimeTemperatureC)
      .filter((t): t is number => t != null);
    if (temps.length === 0) return null;
    return `${Math.min(...temps).toFixed(1)}\u2013${Math.max(...temps).toFixed(1)} \u00b0C`;
  }, [isPhoenix, crossCityData, cityId]);

  const spatialState = useMemo(() => {
    if (!isPhoenix) return { supported: false, label: "Comparison-level only", sentence: "Full spatial targeting requires the local published analysis." };
    if (spatial.status === "supported") return { supported: true, label: "Spatial targeting supported", sentence: "Thermal differences support a comparison for this observation." };
    if (spatial.status === "withheld") return { supported: false, label: "Spatial targeting not supported", sentence: "Differences are too small to support a defensible ordering." };
    if (snapshot?.result == null || submitting) {
      return { supported: false, label: "Loading\u2026", sentence: spatial.sentence, loading: true };
    }
    return {
      supported: false,
      label: "Spatial comparison status unavailable",
      sentence: spatial.sentence,
      loading: false,
    };
  }, [isPhoenix, snapshot?.result, spatial.sentence, spatial.status, submitting]);

  const preparedness = (isPhoenix
    ? (story.questions.support.status as PreparednessEvidenceStatus)
    : "UNAVAILABLE") as PreparednessEvidenceStatus;

  const storyActions = useMemo(
    () =>
      buildStoryActions({
        comparisons,
        preparedness,
        spatialSupported: isPhoenix && spatial.status === "supported",
        isPhoenix,
      }),
    [comparisons, preparedness, isPhoenix, spatial.status],
  );

  const highlights = useMemo(
    () => contextHighlights(comparisons, preparedness),
    [comparisons, preparedness],
  );

  const provenanceLine = observationMode === "published"
    ? isPhoenix
      ? "Published observation \u00b7 15 Jul 2025 \u00b7 03:00 MST \u00b7 FortyGuard TCM"
      : "Published observation \u00b7 8 Jul 2024 \u00b7 15:00 local \u00b7 FortyGuard TCM"
    : null;

  const handleRunLive = async () => {
    if (liveRunning) return;
    setLiveRunning(true);
    try {
      const resp = await fetch(apiUrl("/api/v1/live/selected-time"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ city_id: city.apiCityId, local_datetime: `${liveDate}T${liveTime}:00` }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        console.warn("Live observation failed:", resp.status, body);
      }
    } catch (err) {
      console.warn("Live observation error:", err);
    } finally {
      setLiveRunning(false);
    }
  };

  return (
    <div className="ws-explore" data-testid="explore-city" data-city={cityId} data-dominant-pattern={synthesis?.dominantPattern ?? ""}>
      <CityControls
        cityId={cityId}
        onCityChange={onCityChange}
        observationMode={observationMode}
        onObservationModeChange={setObservationMode}
        liveDate={liveDate}
        onLiveDateChange={setLiveDate}
        liveTime={liveTime}
        onLiveTimeChange={setLiveTime}
        onRunLive={handleRunLive}
        liveRunning={liveRunning}
        provenanceLine={provenanceLine}
      />
      <div className="ws-explore-main">
        <div className="ws-map-column">
          <div className="ws-map-pane">
            {isPhoenix ? (
              <MapBand
                layer={layer}
                ranking={ranking}
                areaId="phoenix-demo"
                jobId={jobId}
                jobStatus={snapshot?.status ?? null}
                result={snapshot?.result ?? null}
                submitting={submitting}
                analysisTime={lastRequest?.analysis_time ?? snapshot?.request?.analysis_time}
                mapMode={mapMode}
                onMapModeChange={setMapMode}
                contextZones={contextZones}
                selectedZoneId={selectedAreaId}
                onSelectedIdChange={selectArea}
              />
            ) : (
              <CrossCityMapBand
                catalog={crossCityCatalog}
                mapMode={mapMode}
                onMapModeChange={setMapMode}
                selectedZoneId={selectedAreaId}
                onSelectedIdChange={selectArea}
              />
            )}
          </div>
          {isPhoenix ? (
            <div className="ws-below-map">
              <details className="ws-analysis-section" data-testid="matched-night-section">
                <summary>Matched nighttime change</summary>
                <MatchedNightChart
                  view={evidence.matched}
                  areaLabel={analysisAreaLabel(selectedAreaId)}
                  analysisAreaCount={ANALYSIS_AREA_GEOIDS.length}
                />
              </details>
              <details className="ws-analysis-section" data-testid="observed-instants-section">
                <summary>Observed thermal instants</summary>
                <ObservedInstantsChart
                  view={evidence.observed}
                  areaLabel={analysisAreaLabel(selectedAreaId)}
                />
              </details>
              <details
                className="ws-analysis-section"
                data-testid="local-context-section"
                open={storyStage === "context"}
              >
                <summary>Local context</summary>
                <ContextPanel comparisons={comparisons} selectedZoneId={selectedAreaId} />
              </details>
              <details className="ws-analysis-section" data-testid="all-zones-section">
                <summary>View all zones</summary>
                <AreaContextBand
                  areaId="phoenix-demo"
                  selectedZoneId={selectedAreaId}
                  result={snapshot?.result ?? null}
                  mapMode={mapMode}
                  onSelectTract={selectArea}
                  onContextZones={setContextZones}
                />
              </details>
            </div>
          ) : null}
        </div>
        <ZonePanel
          zone={zoneInfo}
          rangeLabel={rangeLabel}
          spatialState={spatialState}
          actions={storyActions}
          highlights={highlights}
          stage={storyStage}
          onStageChange={setStoryStage}
          hasLocalAnalysis={isPhoenix}
          forecastSupported={false}
        />
      </div>
    </div>
  );
}

function CrossCityMapBand({
  catalog,
  mapMode,
  onMapModeChange,
  selectedZoneId,
  onSelectedIdChange,
}: {
  catalog: InteractionCatalog | null;
  mapMode: MapMode;
  onMapModeChange: (mode: MapMode) => void;
  selectedZoneId: string | null;
  onSelectedIdChange: (geoid: string | null) => void;
}) {
  return (
    <section className="judge-map" data-testid="map-stage" data-layout="map-primary">
      <MapModeTabs mode={mapMode} onModeChange={onMapModeChange} />
      <JudgeMap
        lane="A"
        historical={catalog}
        enabled
        selectedId={selectedZoneId}
        onSelectedIdChange={onSelectedIdChange}
      />
    </section>
  );
}
