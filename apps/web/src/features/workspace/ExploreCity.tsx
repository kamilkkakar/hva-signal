import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useJobStore } from "@/stores/jobStore";
import { POLL_INTERVAL_MS } from "@/utils/jobPolling";
import { mapLayerFromLimitations, rankingPresentation } from "@/utils/mapLayer";
import {
  PHOENIX_DEMO_DEFAULT_DATETIME_LOCAL,
  phoenixAoiLocalAnalysisTime,
} from "@/utils/phoenixAoiLocalTime";
import {
  MapModeTabs,
  bindMapModeCatalog,
  type MapMode,
  type ZoneMapProperties,
} from "@/features/areaContext";
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
} from "@/features/experience";
import type { PreparednessEvidenceStatus, SpatialDiffStatus } from "@/features/experience/narrative";
import { judgeMapLayer } from "@/features/judgeShell/layer";
import { MapBand } from "@/features/judgeShell/MapBand";
import { JudgeMap } from "@/features/judgeShell/map/JudgeMap";
import { useAreaEvidence } from "@/features/experience/useAreaEvidence";
import { cachedRangeLabel } from "@/features/judgeShell/signalB/cachedPhoenix";
import { apiUrl } from "@/api/baseUrl";
import { rankedFillCount, type InteractionCatalog } from "@/features/mapInteraction";
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
import { CITIES, cityConfig, type CityId, type ObservationMode, type ZoneInfo } from "./types";
import {
  CityEvidenceSections,
  cityEvidenceCapabilities,
} from "./CityEvidenceSections";
import {
  assertPublishedMapContract,
  buildPublishedCityCatalog,
  cachedCityGeometry,
  contextZonesFromRecords,
  featureGeoid,
  putCityGeometryCache,
  type CityGeometry,
  type PublishedMapContract,
} from "./publishedCityMap";

const EMPTY_LIMITATIONS: readonly string[] = [];
const DEFAULT_PHOENIX_AREA = ANALYSIS_AREA_GEOIDS[0];

function spatialStatusFrom(
  status: ReturnType<typeof presentSpatialDifferentiation>["status"],
): SpatialDiffStatus {
  if (status === "withheld") return "INSUFFICIENT";
  if (status === "supported") return "SUFFICIENT";
  return "UNKNOWN";
}

function reportCityTiming(label: string, startedAt: number): void {
  if (!import.meta.env.DEV) return;
  // eslint-disable-next-line no-console
  console.info(`[city-perf] ${label}: ${(performance.now() - startedAt).toFixed(0)}ms`);
}

async function fetchCityGeometry(apiCityId: string): Promise<CityGeometry> {
  const resp = await fetch(apiUrl(`/api/v1/cross-city/cities/${apiCityId}/geometry`), {
    headers: { Accept: "application/geo+json" },
  });
  if (!resp.ok) throw new Error(`geometry ${resp.status}`);
  return (await resp.json()) as CityGeometry;
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
  const [cityGeometry, setCityGeometry] = useState<CityGeometry | null>(() =>
    isPhoenix ? null : cachedCityGeometry(cityId),
  );
  const [cityGeoIds, setCityGeoIds] = useState<string[]>([]);
  const [geometryLoading, setGeometryLoading] = useState(false);
  const [mapContract, setMapContract] = useState<PublishedMapContract | null>(null);
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(
    isPhoenix ? DEFAULT_PHOENIX_AREA : null,
  );
  const cityLoadStarted = useRef(performance.now());

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
    const started = performance.now();
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
        try {
          await submit(draft);
          reportCityTiming("phoenix-initial-submit", started);
          return;
        } catch {
          await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [submit, isPhoenix]);

  useEffect(() => {
    if (!isPhoenix || !polling || !jobId) return;
    void poll();
    const timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [jobId, poll, polling, isPhoenix]);

  useEffect(() => {
    let cancelled = false;
    const started = performance.now();
    void (async () => {
      try {
        const data = await fetchCrossCityMetrics();
        if (!cancelled) {
          setCrossCityData(data);
          reportCityTiming("cross-city-metrics", started);
        }
      } catch {
        /* silent — map contract will fail closed without invented temps */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    cityLoadStarted.current = performance.now();
    if (isPhoenix) {
      setCityGeometry(null);
      setCityGeoIds([]);
      setGeometryLoading(false);
      setMapContract(null);
      return;
    }

    const cached = cachedCityGeometry(cityId);
    if (cached) {
      setCityGeometry(cached);
      const ids = cached.features.map(featureGeoid).filter(Boolean);
      setCityGeoIds(ids);
      if (!ids.includes(selectedAreaId ?? "")) {
        setSelectedAreaId(ids[0] ?? null);
      }
      setGeometryLoading(false);
      reportCityTiming(`${cityId}-geometry-cache-hit`, cityLoadStarted.current);
      return;
    }

    // Clear stale sibling-city geometry so fills never join against the wrong AOI.
    setCityGeometry(null);
    setCityGeoIds([]);
    setGeometryLoading(true);
    let cancelled = false;
    void (async () => {
      try {
        const geojson = await fetchCityGeometry(city.apiCityId);
        if (cancelled) return;
        putCityGeometryCache(cityId, geojson);
        setCityGeometry(geojson);
        const ids = geojson.features.map(featureGeoid).filter(Boolean);
        setCityGeoIds(ids);
        if (!ids.includes(selectedAreaId ?? "")) {
          setSelectedAreaId(ids[0] ?? null);
        }
        reportCityTiming(`${cityId}-geometry-fetch`, cityLoadStarted.current);
      } catch {
        if (!cancelled) {
          setCityGeometry(null);
          setCityGeoIds([]);
        }
      } finally {
        if (!cancelled) setGeometryLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cityId, isPhoenix, city.apiCityId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Idle prefetch published geometry for the other three cities (replay/static only).
  useEffect(() => {
    if (!crossCityData) return;
    let cancelled = false;
    const idle = window.setTimeout(() => {
      const others = CITIES.filter((c) => c.id !== cityId && !c.hasLocalAnalysis);
      void Promise.all(
        others.map(async (c) => {
          if (cachedCityGeometry(c.id) || cancelled) return;
          try {
            const geo = await fetchCityGeometry(c.apiCityId);
            if (!cancelled) putCityGeometryCache(c.id, geo);
          } catch {
            /* prefetch is best-effort */
          }
        }),
      ).then(() => {
        if (!cancelled) reportCityTiming("prefetch-static-cities", cityLoadStarted.current);
      });
    }, 1200);
    return () => {
      cancelled = true;
      window.clearTimeout(idle);
    };
  }, [crossCityData, cityId]);

  const prevCity = useRef(cityId);
  useEffect(() => {
    if (prevCity.current !== cityId) {
      prevCity.current = cityId;
      if (isPhoenix) setSelectedAreaId(DEFAULT_PHOENIX_AREA);
      reportCityTiming(`switch-to-${cityId}`, cityLoadStarted.current);
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

  const cityRecords = useMemo(() => {
    if (!crossCityData) return [] as CrossCityAreaRecord[];
    return crossCityData.areas.filter((a) => a.cityId === cityId);
  }, [crossCityData, cityId]);

  const crossCityCatalog = useMemo<InteractionCatalog | null>(() => {
    if (isPhoenix || !cityGeometry || !crossCityData) return null;
    return buildPublishedCityCatalog(cityGeometry, cityRecords, {
      timezone: cityId === "los-angeles-ca" || cityId === "las-vegas-nv"
        ? "America/Los_Angeles"
        : "America/Phoenix",
    });
  }, [isPhoenix, cityGeometry, crossCityData, cityId, cityRecords]);

  useEffect(() => {
    if (!crossCityCatalog || !cityGeometry) {
      setMapContract(null);
      return;
    }
    setMapContract(assertPublishedMapContract(cityId, cityGeometry, cityRecords, crossCityCatalog));
  }, [crossCityCatalog, cityGeometry, cityId, cityRecords]);

  const crossCityContextZones = useMemo(
    () => contextZonesFromRecords(cityRecords),
    [cityRecords],
  );

  const zoneInfo = useMemo<ZoneInfo | null>(() => {
    if (!selectedAreaId) return null;
    const record = cityRecords.find((a) => a.areaId === selectedAreaId);
    if (isPhoenix) {
      return {
        geoid: selectedAreaId,
        label: analysisAreaLabel(selectedAreaId) ?? selectedAreaId,
        secondaryLabel: "Census Tract \u00b7 Phoenix, AZ",
        temperatureC: thermalB.temperatureC ?? record?.metrics.selectedTimeTemperatureC ?? null,
        canopyPct: record?.metrics.treeCanopyPct ?? null,
        incomeUsd: record?.metrics.medianHouseholdIncomeUsd ?? null,
        olderHousingPct: record?.metrics.olderHousingPct ?? null,
        population: record?.metrics.population ?? null,
      };
    }
    return zoneInfoFromCrossCity(record, selectedAreaId, cityId);
  }, [selectedAreaId, isPhoenix, thermalB.temperatureC, cityRecords, cityId]);

  const rangeLabel = useMemo(() => {
    if (isPhoenix) return cachedRangeLabel();
    const temps = cityRecords
      .map((r) => r.metrics.selectedTimeTemperatureC)
      .filter((t): t is number => t != null);
    if (temps.length === 0) return null;
    return `${Math.min(...temps).toFixed(1)}\u2013${Math.max(...temps).toFixed(1)} \u00b0C`;
  }, [isPhoenix, cityRecords]);

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
      ? "Published observation / 15 Jul 2025 · 03:00 local / FortyGuard TCM"
      : "Published observation / 8 Jul 2024 · 15:00 local / FortyGuard TCM"
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
                contextZones={crossCityContextZones}
                selectedZoneId={selectedAreaId}
                onSelectedIdChange={selectArea}
                loading={geometryLoading || (!!cityGeometry && !crossCityCatalog)}
                contract={mapContract}
              />
            )}
          </div>
          {isPhoenix ? (
            <CityEvidenceSections
              cityId={cityId}
              capabilities={cityEvidenceCapabilities(cityId, {
                matchedStatus: evidence.matched.status,
                observedCount: evidence.observed.instants.length,
                contextFactCount: comparisons.length,
                zoneCount: ANALYSIS_AREA_GEOIDS.length,
                hasInventory: true,
              })}
              storyStage={storyStage}
              selectedAreaId={selectedAreaId}
              areaLabel={analysisAreaLabel(selectedAreaId)}
              analysisAreaCount={ANALYSIS_AREA_GEOIDS.length}
              matched={evidence.matched}
              observed={evidence.observed}
              comparisons={comparisons}
              cityRecords={cityRecords}
              mapMode={mapMode}
              onSelectZone={selectArea}
              phoenixResult={snapshot?.result ?? null}
              onContextZones={setContextZones}
            />
          ) : (
            <CityEvidenceSections
              cityId={cityId}
              capabilities={cityEvidenceCapabilities(cityId, {
                matchedStatus: "UNKNOWN",
                observedCount: 0,
                contextFactCount: cityRecords.length > 0 ? 3 : 0,
                zoneCount: cityRecords.length,
                hasInventory: false,
              })}
              storyStage={storyStage}
              selectedAreaId={selectedAreaId}
              areaLabel={zoneInfo?.label ?? null}
              analysisAreaCount={cityRecords.length || 25}
              matched={evidence.matched}
              observed={evidence.observed}
              comparisons={comparisons}
              cityRecords={cityRecords}
              mapMode={mapMode}
              onSelectZone={selectArea}
            />
          )}
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
  contextZones,
  selectedZoneId,
  onSelectedIdChange,
  loading,
  contract,
}: {
  catalog: InteractionCatalog | null;
  mapMode: MapMode;
  onMapModeChange: (mode: MapMode) => void;
  contextZones: ZoneMapProperties[];
  selectedZoneId: string | null;
  onSelectedIdChange: (geoid: string | null) => void;
  loading: boolean;
  contract: PublishedMapContract | null;
}) {
  const modeCatalog = useMemo(
    () =>
      bindMapModeCatalog({
        historical: catalog,
        mode: mapMode,
        zones: contextZones,
      }),
    [catalog, mapMode, contextZones],
  );
  const geometryCount = modeCatalog?.collection.features.length ?? 0;
  const bindableCount = rankedFillCount(modeCatalog);

  return (
    <section
      className="judge-map"
      data-testid="map-stage"
      data-layout="map-primary"
      data-map-loading={loading ? "true" : "false"}
      data-geometry-feature-count={String(geometryCount)}
      data-bindable-temperature-values={String(
        mapMode === "THERMAL" ? bindableCount : geometryCount,
      )}
      data-map-contract={
        contract &&
        contract.geometry_count === 25 &&
        contract.bindable_temperature_values === 25
          ? "pass"
          : contract
            ? "fail"
            : "pending"
      }
    >
      <MapModeTabs mode={mapMode} onModeChange={onMapModeChange} />
      {loading && !modeCatalog ? (
        <p className="ws-map-loading" data-testid="map-loading">
          Loading published city geography…
        </p>
      ) : null}
      <JudgeMap
        lane="A"
        historical={modeCatalog}
        enabled
        selectedId={selectedZoneId}
        onSelectedIdChange={onSelectedIdChange}
      />
    </section>
  );
}
