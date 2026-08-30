import { useEffect, useMemo, useState } from "react";
import { useJobStore } from "@/stores/jobStore";
import { POLL_INTERVAL_MS } from "@/utils/jobPolling";
import { mapLayerFromLimitations, rankingPresentation } from "@/utils/mapLayer";
import { sourceBannerLabel } from "@/utils/sourceBanner";
import { CapabilityBand } from "./CapabilityBand";
import { ContextBar } from "./ContextBar";
import { happeningView } from "./happening";
import { HappeningBand } from "./HappeningBand";
import { HeroHeader } from "./HeroHeader";
import { judgeMapLayer } from "./layer";
import { AreaContextBand, type MapMode, type ZoneMapProperties } from "@/features/areaContext";
import { MapBand } from "./MapBand";
import { ProvenanceBand } from "./ProvenanceBand";
import { ResultStoryBand } from "./ResultStoryBand";
import { RunBand } from "./RunBand";
import { SelectedZoneBand } from "./SelectedZoneBand";
import { contextSourceChip } from "./sourceChip";
import { SupportsBand } from "./SupportsBand";
import { ThermalBand } from "./ThermalBand";
import { DecisionStoriesBand } from "./decision";
import "./judgeShell.css";

const EMPTY_LIMITATIONS: readonly string[] = [];

function clockDateFromAnalysisTime(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(value);
  return match?.[1] ?? null;
}

export function JudgeShell() {
  const snapshot = useJobStore((state) => state.snapshot);
  const lastRequest = useJobStore((state) => state.lastRequest);
  const submitting = useJobStore((state) => state.submitting);
  const polling = useJobStore((state) => state.polling);
  const jobId = useJobStore((state) => state.jobId);
  const poll = useJobStore((state) => state.poll);
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
    busy,
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
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<MapMode>("THERMAL");
  const [contextZones, setContextZones] = useState<ZoneMapProperties[]>([]);

  useEffect(() => {
    setSelectedZoneId(null);
  }, [jobId]);

  return (
    <div
      className="judge-shell"
      data-testid="judge-shell"
      data-has-result={snapshot?.result != null ? "true" : "false"}
    >
      <HeroHeader />
      <ContextBar
        source={source}
        clockDate={clockDate}
        bannerLabel={source}
      />
      <div
        className="judge-explore"
        data-testid="judge-explore"
        data-layout="map-primary"
      >
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
          selectedZoneId={selectedZoneId}
          onSelectedIdChange={setSelectedZoneId}
        />
        <RunBand />
      </div>
      <HappeningBand
        happening={happening}
        busy={busy}
        showRecovery={showRecovery}
        canResubmit={canResubmit}
        onResubmit={() => void resubmit()}
      />
      <ResultStoryBand snapshot={snapshot} busy={busy} />
      <div id="thermal-conditions">
        <ThermalBand
          snapshot={snapshot}
          status={snapshot?.status ?? null}
          result={snapshot?.result ?? null}
          selectedZoneId={selectedZoneId}
        />
      </div>
      <div id="own-history">
        <SelectedZoneBand
          result={snapshot?.result ?? null}
          selectedZoneId={selectedZoneId}
        />
      </div>
      <DecisionStoriesBand selectedZoneId={selectedZoneId} />
      <div id="area-different">
      <AreaContextBand
        areaId={lastRequest?.area_id ?? snapshot?.request?.area_id ?? "phoenix-demo"}
        selectedZoneId={selectedZoneId}
        result={snapshot?.result ?? null}
        mapMode={mapMode}
        onSelectTract={setSelectedZoneId}
        onContextZones={setContextZones}
      />
      </div>
      <div id="nearby-support">
        <SupportsBand status={snapshot?.status ?? null} result={snapshot?.result ?? null} />
      </div>
      <CapabilityBand />
      <ProvenanceBand snapshot={snapshot} />
    </div>
  );
}
