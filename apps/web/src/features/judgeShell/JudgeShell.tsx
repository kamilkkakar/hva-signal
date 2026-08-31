import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useJobStore } from "@/stores/jobStore";
import { POLL_INTERVAL_MS } from "@/utils/jobPolling";
import { mapLayerFromLimitations, rankingPresentation } from "@/utils/mapLayer";
import { sourceBannerLabel } from "@/utils/sourceBanner";
import {
  PHOENIX_DEMO_DEFAULT_DATETIME_LOCAL,
  phoenixAoiLocalAnalysisTime,
} from "@/utils/phoenixAoiLocalTime";
import { AreaContextBand, type MapMode, type ZoneMapProperties } from "@/features/areaContext";
import { composeSelectedAreaStory } from "@/features/selectedAreaStory";
import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { ANALYSIS_AREA_GEOIDS } from "@/features/selectedAreaStory/types";
import { presentThermalB } from "@/features/selectedAreaStory/thermalB";
import { B_CLOCK, B_TIMEZONE } from "@/features/selectedAreaStory/copy";
import {
  AppShell,
  DecisionDirection,
  EvidenceDisclosure,
  MatchedNightChart,
  ObservedInstantsChart,
  SectionNav,
  ThermalHero,
  contextComparisonsFromFacts,
  presentHistoricalPosition,
  presentSpatialDifferentiation,
  synthesizeNarrative,
} from "@/features/experience";
import { DEMO_CONTROLS } from "@/features/experience/copy";
import { ContextPanel } from "@/features/experience/ContextPanel";
import { PreparednessPanel } from "@/features/experience/PreparednessPanel";
import type { PreparednessEvidenceStatus, SpatialDiffStatus } from "@/features/experience/narrative";
import "@/features/experience/experience.css";
import { CapabilityBand } from "./CapabilityBand";
import { ContextBar } from "./ContextBar";
import { happeningView } from "./happening";
import { HappeningBand } from "./HappeningBand";
import { judgeMapLayer } from "./layer";
import { MapBand } from "./MapBand";
import { ProvenanceBand } from "./ProvenanceBand";
import { ResultStoryBand } from "./ResultStoryBand";
import { RunBand } from "./RunBand";
import { SelectedZoneBand } from "./SelectedZoneBand";
import { contextSourceChip } from "./sourceChip";
import { SupportsBand } from "./SupportsBand";
import { ThermalBand } from "./ThermalBand";
import { useAreaEvidence } from "../experience/useAreaEvidence";
import { CrossCitySection } from "../crossCity";
import "./judgeShell.css";

const EMPTY_LIMITATIONS: readonly string[] = [];
/** Authoritative default only when no valid selection exists. */
const DEFAULT_AREA = ANALYSIS_AREA_GEOIDS[0];

function clockDateFromAnalysisTime(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(value);
  return match?.[1] ?? null;
}

function observationDateLabel(clock: string): string {
  // B_CLOCK is "2025-07-15 03:00" → "15 Jul 2025 · 03:00"
  const match = /^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}:\d{2})/.exec(clock);
  if (!match) {
    return clock;
  }
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const month = months[Number(match[2]) - 1] ?? match[2];
  return `${Number(match[3])} ${month} ${match[1]} · ${match[4]}`;
}

function spatialStatusFrom(
  status: ReturnType<typeof presentSpatialDifferentiation>["status"],
): SpatialDiffStatus {
  if (status === "withheld") return "INSUFFICIENT";
  if (status === "supported") return "SUFFICIENT";
  return "UNKNOWN";
}

function isCatalogGeoid(geoid: string | null | undefined): geoid is string {
  return Boolean(geoid && (ANALYSIS_AREA_GEOIDS as readonly string[]).includes(geoid));
}

export function JudgeShell() {
  const snapshot = useJobStore((state) => state.snapshot);
  const lastRequest = useJobStore((state) => state.lastRequest);
  const submitting = useJobStore((state) => state.submitting);
  const polling = useJobStore((state) => state.polling);
  const jobId = useJobStore((state) => state.jobId);
  const poll = useJobStore((state) => state.poll);
  const submit = useJobStore((state) => state.submit);
  const busy = useJobStore((state) => state.busy);
  const stalled = useJobStore((state) => state.stalled);
  const canResubmit = useJobStore((state) => state.canResubmit);
  const resubmit = useJobStore((state) => state.resubmit);

  useEffect(() => {
    if (!polling || !jobId) {
      return;
    }
    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [jobId, poll, polling]);

  useEffect(() => {
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
      for (let attempt = 0; attempt < 8 && !cancelled; attempt += 1) {
        try {
          await submit(draft);
          return;
        } catch {
          await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [submit]);

  const limitations = snapshot?.result?.system_limitations ?? EMPTY_LIMITATIONS;
  const ranking = useMemo(
    () => rankingPresentation(snapshot?.result?.zones),
    [snapshot?.result?.zones],
  );
  const layer = useMemo(
    () =>
      judgeMapLayer(
        mapLayerFromLimitations(limitations),
        ranking,
        snapshot?.result != null,
      ),
    [limitations, ranking, snapshot?.result],
  );
  const happening = happeningView({
    status: snapshot?.status ?? null,
    busy: busy || snapshot == null,
    stalled,
    rankingState: ranking.state,
    limitations,
  });
  const banner = sourceBannerLabel({
    status: snapshot?.status ?? null,
    thermalSource: snapshot?.result?.thermal_source,
    dataStatus: snapshot?.result?.data_status,
    dataMode: lastRequest?.data_mode ?? snapshot?.request?.data_mode ?? "replay",
  });
  const source = contextSourceChip(banner, snapshot != null);
  const clockDate = clockDateFromAnalysisTime(
    lastRequest?.analysis_time ?? snapshot?.request?.analysis_time,
  );
  const showRecovery = snapshot?.status === "unknown_job" || stalled;

  // Single source of truth for the selected analysis area.
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(DEFAULT_AREA);
  const defaultInitDone = useRef(false);
  useEffect(() => {
    if (defaultInitDone.current) {
      return;
    }
    defaultInitDone.current = true;
    if (!isCatalogGeoid(selectedAreaId)) {
      setSelectedAreaId(DEFAULT_AREA);
    }
  }, [selectedAreaId]);

  const selectArea = useCallback((geoid: string | null) => {
    if (isCatalogGeoid(geoid)) {
      setSelectedAreaId(geoid);
    }
  }, []);

  const [mapMode, setMapMode] = useState<MapMode>("THERMAL");
  const [contextZones, setContextZones] = useState<ZoneMapProperties[]>([]);
  const evidence = useAreaEvidence(selectedAreaId);
  const thermalB = presentThermalB(selectedAreaId);
  const history = presentHistoricalPosition(snapshot?.result, selectedAreaId);
  const spatial = presentSpatialDifferentiation(snapshot?.result, selectedAreaId);
  const observationStamp = `${B_CLOCK} ${B_TIMEZONE}`;
  const observationDate = observationDateLabel(B_CLOCK);
  const story = composeSelectedAreaStory({
    selectedGeoid: selectedAreaId,
    result: snapshot?.result ?? null,
    context: evidence.context?.selected ?? null,
    document: evidence.context,
  });
  const comparisons = contextComparisonsFromFacts(story.questions.different.facts);
  const prepStatus = story.questions.support.status as PreparednessEvidenceStatus;
  const observedHigh = useMemo(() => {
    if (evidence.observed.status !== "AVAILABLE" || evidence.observed.instants.length === 0) {
      return { value: null as number | null, label: null as string | null };
    }
    const high = evidence.observed.instants.reduce((best, item) =>
      item.temperatureC > best.temperatureC ? item : best,
    );
    return { value: high.temperatureC, label: high.label };
  }, [evidence.observed]);
  const analysisAreaCount = ANALYSIS_AREA_GEOIDS.length;
  const synthesis = useMemo(
    () =>
      synthesizeNarrative({
        areaLabel: analysisAreaLabel(selectedAreaId),
        analysisAreaCount,
        selectedTemperatureC: thermalB.temperatureC,
        observationStamp: observationDate,
        spatialDiff: spatialStatusFrom(spatial.status),
        historicalPosition: {
          status: history.status === "available" ? "AVAILABLE" : "UNAVAILABLE",
          percent: history.percent,
          sentence: history.sentence,
        },
        matchedChangeC: evidence.matched.change2024vs2022,
        geographyMedianChangeC: evidence.matched.medianChange,
        matchedNightsTotal: evidence.matched.nightsTotal,
        observedHighC: observedHigh.value,
        observedHighLabel: observedHigh.label,
        contextComparisons: comparisons,
        preparedness: prepStatus,
        thermalAvailable: thermalB.temperatureC != null,
      }),
    [
      analysisAreaCount,
      comparisons,
      evidence.matched.change2024vs2022,
      evidence.matched.medianChange,
      evidence.matched.nightsTotal,
      history.percent,
      history.sentence,
      history.status,
      observationDate,
      observedHigh.label,
      observedHigh.value,
      prepStatus,
      selectedAreaId,
      spatial.status,
      thermalB.temperatureC,
    ],
  );

  return (
    <div
      className="judge-shell hx-app"
      data-testid="judge-shell"
      data-has-result={snapshot?.result != null ? "true" : "false"}
      data-dominant-pattern={synthesis.dominantPattern}
      data-selected-area-id={selectedAreaId ?? ""}
    >
      <AppShell observationStamp={observationStamp} />
      <SectionNav />
      <ContextBar
        source={source}
        clockDate={clockDate}
        bannerLabel={source}
        showChips={false}
      />
      <ThermalHero
        selectedZoneId={selectedAreaId}
        onSelect={selectArea}
        temperatureC={thermalB.temperatureC}
        observationStamp={observationStamp}
        observationDateLabel={observationDate}
        history={history}
        spatial={spatial}
        change2024vs2022={evidence.matched.change2024vs2022}
        patternTitle={synthesis.patternTitle}
        patternSummary={synthesis.patternSummary}
        evidenceSignals={synthesis.evidenceSummary}
      />
      <div
        className="judge-explore"
        data-testid="judge-explore"
        data-layout="map-primary"
      >
        <div className="hx-map-stack hx-level-1">
          <MapBand
            layer={layer}
            ranking={ranking}
            areaId={lastRequest?.area_id ?? snapshot?.request?.area_id ?? "phoenix-demo"}
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
          <p className="hx-temporal-cue">
            <a href="#matched-night-title">How nighttime conditions changed</a>
          </p>
        </div>
      </div>
      <details className="hx-demo-controls" data-testid="demo-controls">
        <summary>{DEMO_CONTROLS}</summary>
        <RunBand />
      </details>
      <div className="hx-temporal-pair" data-testid="temporal-pair">
        <MatchedNightChart
          view={evidence.matched}
          areaLabel={analysisAreaLabel(selectedAreaId)}
          analysisAreaCount={analysisAreaCount}
        />
        <ObservedInstantsChart
          view={evidence.observed}
          areaLabel={analysisAreaLabel(selectedAreaId)}
        />
      </div>
      <div data-testid="selected-area-story">
        <ContextPanel comparisons={comparisons} selectedZoneId={selectedAreaId} />
        <PreparednessPanel
          status={prepStatus}
          sentences={story.questions.support.sentences}
          sourceLines={story.sources.mag}
        />
      </div>
      <DecisionDirection
        synthesis={synthesis}
        areaLabel={analysisAreaLabel(selectedAreaId)}
      />
      <CrossCitySection />
      <HappeningBand
        happening={happening}
        busy={busy}
        showRecovery={showRecovery}
        canResubmit={canResubmit}
        onResubmit={() => void resubmit()}
      />
      <div id="area-different">
        <AreaContextBand
          areaId={lastRequest?.area_id ?? snapshot?.request?.area_id ?? "phoenix-demo"}
          selectedZoneId={selectedAreaId}
          result={snapshot?.result ?? null}
          mapMode={mapMode}
          onSelectTract={selectArea}
          onContextZones={setContextZones}
        />
      </div>
      <EvidenceDisclosure>
        <ProvenanceBand snapshot={snapshot} />
        <ResultStoryBand snapshot={snapshot} busy={busy} />
        <div id="thermal-conditions">
          <ThermalBand
            snapshot={snapshot}
            status={snapshot?.status ?? null}
            result={snapshot?.result ?? null}
            selectedZoneId={selectedAreaId}
          />
        </div>
        <div id="own-history">
          <SelectedZoneBand
            result={snapshot?.result ?? null}
            selectedZoneId={selectedAreaId}
          />
        </div>
        <div id="nearby-support">
          <SupportsBand status={snapshot?.status ?? null} result={snapshot?.result ?? null} />
        </div>
        <CapabilityBand />
      </EvidenceDisclosure>
    </div>
  );
}
