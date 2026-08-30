import type { AnalysisResultStub } from "@/api/analysisJobs";
import { SELECTED_ZONE_EMPTY } from "./copy";
import {
  bindHistoricalPositions,
  presentHistoricalPosition,
  SelectedZonePosition,
} from "./charts";

export type SelectedZoneBandProps = {
  result?: AnalysisResultStub | null;
  selectedZoneId?: string | null;
};

export function SelectedZoneBand({
  result = null,
  selectedZoneId = null,
}: SelectedZoneBandProps) {
  const view = presentHistoricalPosition(
    bindHistoricalPositions({ result, selectedZoneId }),
  );
  return (
    <section
      className="judge-zone"
      aria-label="Selected zone"
      data-testid="selected-zone"
    >
      <p className="kicker">Selected zone</p>
      <SelectedZonePosition
        view={view}
        selectedZoneId={selectedZoneId}
        emptyCopy={SELECTED_ZONE_EMPTY}
      />
    </section>
  );
}
