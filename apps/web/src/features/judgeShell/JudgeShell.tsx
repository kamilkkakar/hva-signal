import { useEffect, useMemo } from "react";
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
import { MapBand } from "./MapBand";
import { ProvenanceBand } from "./ProvenanceBand";
import { RunBand } from "./RunBand";
import { SelectedZoneBand } from "./SelectedZoneBand";
import { contextSourceChip } from "./sourceChip";
import { SupportsBand } from "./SupportsBand";
import { ThermalBand } from "./ThermalBand";
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

  return (
    <div className="judge-shell" data-testid="judge-shell">
      <HeroHeader />
      <ContextBar
        source={source}
        clockDate={clockDate}
        bannerLabel={source}
      />
      <HappeningBand
        happening={happening}
        busy={busy}
        showRecovery={showRecovery}
        canResubmit={canResubmit}
        onResubmit={() => void resubmit()}
      />
      <MapBand
        layer={layer}
        ranking={ranking}
        areaId={lastRequest?.area_id ?? snapshot?.request?.area_id ?? "phoenix-demo"}
        resultAreaId={snapshot?.request?.area_id ?? null}
        jobId={jobId}
        jobStatus={snapshot?.status ?? null}
        result={snapshot?.result ?? null}
        submitting={submitting}
        analysisTime={lastRequest?.analysis_time ?? snapshot?.request?.analysis_time}
      />
      <ThermalBand
        snapshot={snapshot}
        rankingState={ranking.state}
        busy={busy}
        status={snapshot?.status ?? null}
        result={snapshot?.result ?? null}
      />
      <SelectedZoneBand />
      <SupportsBand status={snapshot?.status ?? null} result={snapshot?.result ?? null} />
      <CapabilityBand />
      <ProvenanceBand snapshot={snapshot} />
      <RunBand />
    </div>
  );
}
