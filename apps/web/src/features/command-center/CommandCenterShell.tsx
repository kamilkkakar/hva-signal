import { useEffect } from "react";
import { MapStage } from "@/features/map/MapStage";
import { TimelineBar } from "@/features/timeline/TimelineBar";
import { useJobStore } from "@/stores/jobStore";
import { mapLayerFromLimitations, rankingPresentation } from "@/utils/mapLayer";
import { sourceBannerLabel } from "@/utils/sourceBanner";
import { DecisionRail } from "./DecisionRail";
import { QueryRail } from "./QueryRail";
import { SourceTape } from "./SourceTape";

export function CommandCenterShell() {
  const snapshot = useJobStore((state) => state.snapshot);
  const lastRequest = useJobStore((state) => state.lastRequest);
  const submitting = useJobStore((state) => state.submitting);
  const polling = useJobStore((state) => state.polling);
  const jobId = useJobStore((state) => state.jobId);
  const poll = useJobStore((state) => state.poll);

  useEffect(() => {
    if (!polling || !jobId) {
      return;
    }
    const timer = window.setInterval(() => {
      void poll();
    }, 1500);
    return () => window.clearInterval(timer);
  }, [jobId, poll, polling]);

  const limitations = snapshot?.result?.system_limitations ?? [];
  const layer = mapLayerFromLimitations(limitations);
  const ranking = rankingPresentation(snapshot?.result?.zones);
  const banner = sourceBannerLabel({
    status: snapshot?.status ?? null,
    thermalSource: snapshot?.result?.thermal_source,
    dataStatus: snapshot?.result?.data_status,
    dataMode: lastRequest?.data_mode ?? snapshot?.request?.data_mode,
  });

  return (
    <div className="shell">
      <header className="shell-banner">
        <div>
          <p className="eyebrow">3K Labs</p>
          <h1>HVA-Signal</h1>
          <p className="product-expansion">Heat, Vulnerability &amp; Action Signal</p>
        </div>
        <SourceTape active={banner} />
      </header>
      <div className="shell-grid">
        <QueryRail />
        <MapStage
          layer={layer}
          ranking={ranking}
          areaId={lastRequest?.area_id ?? snapshot?.request?.area_id ?? null}
          resultAreaId={snapshot?.request?.area_id ?? null}
          jobId={jobId}
          jobStatus={snapshot?.status ?? null}
          result={snapshot?.result ?? null}
          submitting={submitting}
        />
        <DecisionRail ranking={ranking} />
      </div>
      <TimelineBar />
    </div>
  );
}
