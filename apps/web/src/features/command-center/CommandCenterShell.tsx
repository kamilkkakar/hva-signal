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
        <MapStage layer={layer} ranking={ranking} />
        <DecisionRail ranking={ranking} />
      </div>
      <TimelineBar />
    </div>
  );
}
