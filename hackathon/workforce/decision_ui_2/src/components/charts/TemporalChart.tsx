import type { AnalysisAreaId, TemporalChartModel } from "@/contracts";
import { isGroupedSeries, isReady } from "@/contracts";
import { TEMPORAL_PENDING } from "@/ia/copy";
import { analysisAreaLabel } from "@/contracts";
import { PendingState } from "@/components/pending/PendingState";
import { ChartFrame } from "./ChartFrame";
import { EmptyPlot } from "./EmptyPlot";
import { SeriesPlot } from "./SeriesPlot";

type TemporalChartProps = {
  readonly model: TemporalChartModel;
  readonly selectedAreaId: AnalysisAreaId | null;
};

export function TemporalChart({ model, selectedAreaId }: TemporalChartProps) {
  const areaNote = selectedAreaId
    ? analysisAreaLabel(Number(selectedAreaId.replace("area-", "")))
    : "No analysis area selected";

  if (isGroupedSeries(model)) {
    const groups = isReady(model.groups) ? model.groups.value : null;
    return (
      <ChartFrame chrome={model.chrome} testId={`chart-${model.kind}`}>
        <p className="area-once">{areaNote}. {model.chrome.title} follows the map selection.</p>
        {groups && groups[0] ? (
          <SeriesPlot points={groups[0].points} label={`${model.chrome.title}, ${model.chrome.unit}`} />
        ) : (
          <>
            <EmptyPlot label={`${model.chrome.title} awaiting temporal program`} />
            <PendingState message={TEMPORAL_PENDING} />
          </>
        )}
      </ChartFrame>
    );
  }

  const points = isReady(model.points) ? model.points.value : null;
  return (
    <ChartFrame chrome={model.chrome} testId={`chart-${model.kind}`}>
      <p className="area-once">{areaNote}. {model.chrome.title} follows the map selection.</p>
      {points ? (
        <SeriesPlot points={points} label={`${model.chrome.title}, ${model.chrome.unit}`} />
      ) : (
        <>
          <EmptyPlot label={`${model.chrome.title} awaiting temporal program`} />
          <PendingState message={TEMPORAL_PENDING} />
        </>
      )}
    </ChartFrame>
  );
}
