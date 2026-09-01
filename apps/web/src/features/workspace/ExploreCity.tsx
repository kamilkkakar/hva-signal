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
import type {
  PreparednessEvidenceStatus,
  SpatialDiffStatus,
} from "@/features/experience/narrative";
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
import type {
  CrossCityMetricsResponse,
  CrossCityAreaRecord,
} from "@/features/crossCity/types";
import { CityControls } from "./CityControls";
import { ZonePanel } from "./ZonePanel";
import { buildStoryActions, contextHighlights } from "./actionEngine";
import { type HvaStage } from "./HvaStoryRail";
import {
  CITIES,
  cityConfig,
  type CityId,
  type ObservationMode,
  type ZoneInfo,
} from "./types";
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
  normalizeGeoid,
  putCityGeometryCache,
  type CityGeometry,
  type PublishedMapContract,
} from "./publishedCityMap";

const EMPTY_LIMITATIONS: readonly string[] = [];
const DEFAULT_PHOENIX_AREA = ANALYSIS_AREA_GEOIDS[0];

type LiveZoneRow = {
  zone_id: string;
  temperature_c: number | null;
  tile_count?: number;
  coverage_status?: string;
};

type LiveZoneAnalysis = {
  city?: string;
  local_datetime?: string;
  timezone?: string;
  aggregation_contract?: string;
  geometry_zone_count?: number;
  bindable_temperature_values?: number;
  source_tile_count?: number;
  zones?: LiveZoneRow[];
};

type LiveObservationResponse = {
  status?: string;
  message?: string;
  provenance?: {
    acquisition_language?: string;
    vendor_attempted?: boolean;
    cache_tier?: string | null;
    contract?: string;
  };
  analysis?: LiveZoneAnalysis;
};

type StoredLiveObservation = LiveObservationResponse & {
  cityId: CityId;
  requestedLocal: string;
};

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

function cityTimezone(cityId: CityId): string {
  return cityId === "los-angeles-ca" || cityId === "las-vegas-nv"
    ? "America/Los_Angeles"
    : "America/Phoenix";
}

function liveErrorMessage(status: number, payload: unknown): string {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const detail = record.detail;
    if (detail && typeof detail === "object") {
      const message = (detail as Record<string, unknown>).message;
      if (typeof message === "string") return message;
    }
    if (typeof record.message === "string") return record.message;
  }
  return `Live observation failed (${status}).`;
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
  const usePhoenixPublished = isPhoenix && observationMode === "published";

  const [liveDate, setLiveDate] = useState("2024-07-08");
  const [liveTime, setLiveTime] = useState("15:00");
  const [liveRunning, setLiveRunning] = useState(false);
  const [liveResult, setLiveResult] = useState<StoredLiveObservation | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<MapMode>("THERMAL");
  const [storyStage, setStoryStage] = useState<HvaStage>("heat");
  const [contextZones, setContextZones] = useState<ZoneMapProperties[]>([]);
  const [crossCityData, setCrossCityData] = useState<CrossCityMetricsResponse | null>(null);
  const [cityGeometry, setCityGeometry] = useState<CityGeometry | null>(() =>
    cachedCityGeometry(cityId),
  );
  const [cityGeoIds, setCityGeoIds] = useState<string[]>([]);
  const [geometryLoading, setGeometryLoading] = useState(false);
  const [mapContract, setMapContract] = useState<PublishedMapContract | null>(null);
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(
    isPhoenix ? DEFAULT_PHOENIX_AREA : null,
  );
  const cityLoadStarted = useRef(performance.now());

  // Phoenix historical job store. This remains replay-only and separate from
  // bounded selected-time Live.
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
        /* map contract fails closed without invented temperatures */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Cross-city geometry is static and safe to cache for every supported city,
  // including Phoenix. Published Phoenix still uses its separate local analysis
  // geography; the cross-city Phoenix geometry is used only for bounded Live.
  useEffect(() => {
    cityLoadStarted.current = performance.now();
    const cached = cachedCityGeometry(cityId);
    if (cached) {
      setCityGeometry(cached);
      setCityGeoIds(cached.features.map(featureGeoid).filter(Boolean));
      setGeometryLoading(false);
      reportCityTiming(`${cityId}-geometry-cache-hit`, cityLoadStarted.current);
      return;
    }

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
        setCityGeoIds(geojson.features.map(featureGeoid).filter(Boolean));
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
  }, [cityId, city.apiCityId]);

  // Idle prefetch is static geometry only; it never touches FortyGuard.
  useEffect(() => {
    if (!crossCityData) return;
    let cancelled = false;
    const idle = window.setTimeout(() => {
      const others = CITIES.filter((c) => c.id !== cityId);
      void Promise.all(
        others.map(async (c) => {
          if (cachedCityGeometry(c.id) || cancelled) return;
          try {
            const geo = await fetchCityGeometry(c.apiCityId);
            if (!cancelled) putCityGeometryCache(c.id, geo);
          } catch {
            /* best-effort static prefetch */
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
      setLiveResult(null);
      setLiveError(null);
      setMapContract(null);
      if (observationMode === "published" && city.hasLocalAnalysis) {
        setSelectedAreaId(DEFAULT_PHOENIX_AREA);
      }
      reportCityTiming(`switch-to-${cityId}`, cityLoadStarted.current);
    }
  }, [cityId, city.hasLocalAnalysis, observationMode]);

  useEffect(() => {
    if (observationMode === "live") {
      if (cityGeoIds.length > 0 && !cityGeoIds.includes(selectedAreaId ?? "")) {
        setSelectedAreaId(cityGeoIds[0] ?? null);
      }
      return;
    }
    if (isPhoenix && !(ANALYSIS_AREA_GEOIDS as readonly string[]).includes(selectedAreaId ?? "")) {
      setSelectedAreaId(DEFAULT_PHOENIX_AREA);
    } else if (!isPhoenix && cityGeoIds.length > 0 && !cityGeoIds.includes(selectedAreaId ?? "")) {
      setSelectedAreaId(cityGeoIds[0] ?? null);
    }
  }, [observationMode, isPhoenix, cityGeoIds, selectedAreaId]);

  const selectArea = useCallback(
    (geoid: string | null) => {
      if (!geoid) return;
      if (observationMode === "live" || !isPhoenix) {
        if (cityGeoIds.includes(geoid)) setSelectedAreaId(geoid);
        return;
      }
      if ((ANALYSIS_AREA_GEOIDS as readonly string[]).includes(geoid)) {
        setSelectedAreaId(geoid);
      }
    },
    [observationMode, isPhoenix, cityGeoIds],
  );

  // Phoenix historical evidence is intentionally not reused as the Live map.
  const limitations = snapshot?.result?.system_limitations ?? EMPTY_LIMITATIONS;
  const ranking = useMemo(
    () => rankingPresentation(snapshot?.result?.zones),
    [snapshot?.result?.zones],
  );
  const layer = useMemo(
    () => judgeMapLayer(mapLayerFromLimitations(limitations), ranking, snapshot?.result != null),
    [limitations, ranking, snapshot?.result],
  );
  const evidence = useAreaEvidence(usePhoenixPublished ? selectedAreaId : null);
  const thermalB = presentThermalB(usePhoenixPublished ? selectedAreaId : null);
  const history = presentHistoricalPosition(
    snapshot?.result,
    usePhoenixPublished ? selectedAreaId : null,
  );
  const spatial = presentSpatialDifferentiation(
    snapshot?.result,
    usePhoenixPublished ? selectedAreaId : null,
  );
  const observationStamp = `${B_CLOCK} ${B_TIMEZONE}`;
  const story = composeSelectedAreaStory({
    selectedGeoid: usePhoenixPublished ? selectedAreaId : null,
    result: usePhoenixPublished ? snapshot?.result ?? null : null,
    context: usePhoenixPublished ? evidence.context?.selected ?? null : null,
    document: usePhoenixPublished ? evidence.context : null,
  });
  const comparisons = contextComparisonsFromFacts(story.questions.different.facts);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const synthesis = useMemo(() => {
    if (!usePhoenixPublished) return null;
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
  }, [
    usePhoenixPublished,
    selectedAreaId,
    thermalB.temperatureC,
    spatial.status,
    history,
    evidence.matched,
    comparisons,
    story.questions.support.status,
    observationStamp,
  ]);

  const cityRecords = useMemo(() => {
    if (!crossCityData) return [] as CrossCityAreaRecord[];
    return crossCityData.areas.filter((a) => a.cityId === cityId);
  }, [crossCityData, cityId]);

  const liveCityRecords = useMemo(() => {
    if (!liveResult || liveResult.cityId !== cityId) return null;
    const rows = liveResult.analysis?.zones ?? [];
    const temperatures = new Map<string, number | null>();
    for (const row of rows) {
      temperatures.set(normalizeGeoid(row.zone_id), row.temperature_c);
    }
    return cityRecords.map((record) => {
      const geoid = normalizeGeoid(record.areaId);
      return {
        ...record,
        metrics: {
          ...record.metrics,
          selectedTimeTemperatureC: temperatures.has(geoid)
            ? temperatures.get(geoid) ?? null
            : null,
        },
      };
    });
  }, [liveResult, cityId, cityRecords]);

  const activeCityRecords =
    observationMode === "live" && liveCityRecords ? liveCityRecords : cityRecords;

  const publishedCrossCityCatalog = useMemo<InteractionCatalog | null>(() => {
    if (!cityGeometry || !crossCityData) return null;
    return buildPublishedCityCatalog(cityGeometry, cityRecords, {
      timezone: cityTimezone(cityId),
    });
  }, [cityGeometry, crossCityData, cityId, cityRecords]);

  const liveCatalog = useMemo<InteractionCatalog | null>(() => {
    if (!cityGeometry || !liveResult || liveResult.cityId !== cityId || !liveCityRecords) {
      return null;
    }
    return buildPublishedCityCatalog(cityGeometry, liveCityRecords, {
      timezone: liveResult.analysis?.timezone ?? cityTimezone(cityId),
      targetTimestamp: liveResult.analysis?.local_datetime ?? liveResult.requestedLocal,
      source:
        liveResult.status === "live_acquired" ? "fortyguard_live" : "fortyguard_cached",
      dataStatus: liveResult.status === "live_acquired" ? "live" : "cached",
    });
  }, [cityGeometry, liveResult, cityId, liveCityRecords]);

  const activeCrossCityCatalog =
    observationMode === "live" ? liveCatalog ?? publishedCrossCityCatalog : publishedCrossCityCatalog;

  useEffect(() => {
    if (!activeCrossCityCatalog || !cityGeometry) {
      setMapContract(null);
      return;
    }
    setMapContract(
      assertPublishedMapContract(
        cityId,
        cityGeometry,
        activeCityRecords,
        activeCrossCityCatalog,
      ),
    );
  }, [activeCrossCityCatalog, cityGeometry, cityId, activeCityRecords]);

  const crossCityContextZones = useMemo(
    () => contextZonesFromRecords(activeCityRecords),
    [activeCityRecords],
  );

  const zoneInfo = useMemo<ZoneInfo | null>(() => {
    if (!selectedAreaId) return null;
    const record = activeCityRecords.find(
      (a) => normalizeGeoid(a.areaId) === normalizeGeoid(selectedAreaId),
    );
    if (usePhoenixPublished) {
      const publishedRecord = cityRecords.find((a) => a.areaId === selectedAreaId);
      return {
        geoid: selectedAreaId,
        label: analysisAreaLabel(selectedAreaId) ?? selectedAreaId,
        secondaryLabel: "Census Tract · Phoenix, AZ",
        temperatureC:
          thermalB.temperatureC ?? publishedRecord?.metrics.selectedTimeTemperatureC ?? null,
        canopyPct: publishedRecord?.metrics.treeCanopyPct ?? null,
        incomeUsd: publishedRecord?.metrics.medianHouseholdIncomeUsd ?? null,
        olderHousingPct: publishedRecord?.metrics.olderHousingPct ?? null,
        population: publishedRecord?.metrics.population ?? null,
      };
    }
    return zoneInfoFromCrossCity(record, selectedAreaId, cityId);
  }, [selectedAreaId, usePhoenixPublished, thermalB.temperatureC, activeCityRecords, cityRecords, cityId]);

  const rangeLabel = useMemo(() => {
    if (usePhoenixPublished) return cachedRangeLabel();
    const temps = activeCityRecords
      .map((r) => r.metrics.selectedTimeTemperatureC)
      .filter((t): t is number => t != null && Number.isFinite(t));
    if (temps.length === 0) return null;
    return `${Math.min(...temps).toFixed(1)}–${Math.max(...temps).toFixed(1)} °C`;
  }, [usePhoenixPublished, activeCityRecords]);

  const spatialState = useMemo(() => {
    if (observationMode === "live") {
      if (!liveResult) {
        return {
          supported: false,
          label: "Live observation pending",
          sentence: "Choose a supported city and local hour, then run a bounded selected-time observation.",
        };
      }
      return {
        supported: false,
        label: "Live selected-time observation",
        sentence: "Absolute °C is shown. A single selected-time snapshot does not by itself authorize a priority ranking.",
      };
    }
    if (!isPhoenix) {
      return {
        supported: false,
        label: "Comparison-level only",
        sentence: "Full spatial targeting requires the local published analysis.",
      };
    }
    if (spatial.status === "supported") {
      return {
        supported: true,
        label: "Spatial targeting supported",
        sentence: "Thermal differences support a comparison for this observation.",
      };
    }
    if (spatial.status === "withheld") {
      return {
        supported: false,
        label: "Spatial targeting not supported",
        sentence: "Differences are too small to support a defensible ordering.",
      };
    }
    if (snapshot?.result == null || submitting) {
      return {
        supported: false,
        label: "Loading…",
        sentence: spatial.sentence,
        loading: true,
      };
    }
    return {
      supported: false,
      label: "Spatial comparison status unavailable",
      sentence: spatial.sentence,
      loading: false,
    };
  }, [observationMode, liveResult, isPhoenix, snapshot?.result, spatial.sentence, spatial.status, submitting]);

  const preparedness = (usePhoenixPublished
    ? (story.questions.support.status as PreparednessEvidenceStatus)
    : "UNAVAILABLE") as PreparednessEvidenceStatus;

  const storyActions = useMemo(
    () =>
      buildStoryActions({
        comparisons,
        preparedness,
        spatialSupported: usePhoenixPublished && spatial.status === "supported",
        isPhoenix: usePhoenixPublished,
      }),
    [comparisons, preparedness, usePhoenixPublished, spatial.status],
  );

  const highlights = useMemo(
    () => contextHighlights(comparisons, preparedness),
    [comparisons, preparedness],
  );

  const provenanceLine = useMemo(() => {
    if (observationMode === "published") {
      return isPhoenix
        ? "Published observation / 15 Jul 2025 · 03:00 local / FortyGuard TCM"
        : "Published observation / 8 Jul 2024 · 15:00 local / FortyGuard TCM";
    }
    if (!liveResult) {
      return "Bounded Live / supported city + selected local hour / FortyGuard Type-1 TCM";
    }
    const source = liveResult.status === "cache_hit" ? "Cached live result" : "Live acquisition";
    return `${source} / ${liveDate} · ${liveTime} local / FortyGuard Type-1 TCM`;
  }, [observationMode, isPhoenix, liveResult, liveDate, liveTime]);

  const handleRunLive = async () => {
    if (liveRunning) return;
    setLiveRunning(true);
    setLiveError(null);
    const requestedLocal = `${liveDate}T${liveTime}:00`;
    try {
      const resp = await fetch(apiUrl("/api/v1/live/selected-time"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ city_id: city.apiCityId, local_datetime: requestedLocal }),
      });
      const body = (await resp.json().catch(() => ({}))) as LiveObservationResponse;
      if (!resp.ok) throw new Error(liveErrorMessage(resp.status, body));
      if (body.status !== "cache_hit" && body.status !== "live_acquired") {
        throw new Error(body.message ?? "Live acquisition is unavailable for this request.");
      }
      const bindable = Number(body.analysis?.bindable_temperature_values ?? 0);
      const zones = body.analysis?.zones ?? [];
      if (zones.length === 0 || bindable <= 0) {
        throw new Error(
          body.message ?? "Live observation returned without bindable zone temperatures.",
        );
      }
      setLiveResult({ ...body, cityId, requestedLocal });
      setMapMode("THERMAL");
      const firstBindable = zones.find(
        (row) => row.temperature_c != null && Number.isFinite(row.temperature_c),
      );
      if (firstBindable && !cityGeoIds.includes(selectedAreaId ?? "")) {
        setSelectedAreaId(normalizeGeoid(firstBindable.zone_id));
      }
    } catch (err) {
      setLiveError(err instanceof Error ? err.message : "Live observation failed.");
    } finally {
      setLiveRunning(false);
    }
  };

  const liveStatusMessage =
    observationMode !== "live"
      ? null
      : liveError
        ? liveError
        : liveRunning
          ? "Running the bounded selected-time observation. The existing map stays visible until a result returns."
          : liveResult
            ? liveResult.message ?? "Selected-time observation loaded."
            : "Choose a supported city, date and local hour. The map remains on the published observation until Live returns.";

  return (
    <div
      className="ws-explore"
      data-testid="explore-city"
      data-city={cityId}
      data-dominant-pattern={synthesis?.dominantPattern ?? ""}
    >
      <CityControls
        cityId={cityId}
        onCityChange={onCityChange}
        observationMode={observationMode}
        onObservationModeChange={(mode) => {
          setObservationMode(mode);
          setLiveError(null);
        }}
        liveDate={liveDate}
        onLiveDateChange={setLiveDate}
        liveTime={liveTime}
        onLiveTimeChange={setLiveTime}
        onRunLive={handleRunLive}
        liveRunning={liveRunning}
        provenanceLine={provenanceLine}
        liveAvailable
      />
      {liveStatusMessage ? (
        <p
          className="ws-live-status"
          data-testid="live-status"
          data-state={liveError ? "error" : liveResult ? "success" : "pending"}
        >
          {liveStatusMessage}
        </p>
      ) : null}
      <div className="ws-explore-main">
        <div className="ws-map-column">
          <div className="ws-map-pane">
            {usePhoenixPublished ? (
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
                catalog={activeCrossCityCatalog}
                mapMode={mapMode}
                onMapModeChange={setMapMode}
                contextZones={crossCityContextZones}
                selectedZoneId={selectedAreaId}
                onSelectedIdChange={selectArea}
                loading={geometryLoading || (!!cityGeometry && !activeCrossCityCatalog)}
                contract={mapContract}
              />
            )}
          </div>
          {usePhoenixPublished ? (
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
                contextFactCount: activeCityRecords.length > 0 ? 3 : 0,
                zoneCount: activeCityRecords.length,
                hasInventory: false,
              })}
              storyStage={storyStage}
              selectedAreaId={selectedAreaId}
              areaLabel={zoneInfo?.label ?? null}
              analysisAreaCount={activeCityRecords.length || 25}
              matched={evidence.matched}
              observed={evidence.observed}
              comparisons={comparisons}
              cityRecords={activeCityRecords}
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
          hasLocalAnalysis={usePhoenixPublished}
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
