import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { GEOID_DETAILS_SUMMARY } from "@/features/selectedAreaStory/copy";
import {
  SELECTED_DETAILS_SUMMARY,
  SELECTED_POSITION_EMPTY,
  SELECTED_POSITION_KICKER,
  SELECTED_POSITION_UNAVAILABLE,
} from "./copy";
import { PositionAxis } from "./PositionAxis";
import "./charts.css";
import type { HistoricalPositionView } from "./types";

export type SelectedZonePositionProps = {
  view: HistoricalPositionView;
  selectedZoneId?: string | null;
  emptyCopy?: string;
};

export function SelectedZonePosition({
  view,
  selectedZoneId = null,
  emptyCopy = SELECTED_POSITION_EMPTY,
}: SelectedZonePositionProps) {
  if (!selectedZoneId) {
    return (
      <p className="judge-card-fact" data-testid="selected-zone-empty">
        {emptyCopy}
      </p>
    );
  }

  if (!view.selected || view.selectedExact == null) {
    return (
      <div data-testid="selected-zone-position" data-has-position="false">
        <p className="judge-card-fact">{analysisAreaLabel(selectedZoneId) ?? "Selected analysis area"}</p>
        <details data-testid="selected-zone-geoid">
          <summary>{GEOID_DETAILS_SUMMARY}</summary>
          <p>{selectedZoneId}</p>
        </details>
        <p className="judge-card-fact">{SELECTED_POSITION_UNAVAILABLE}</p>
      </div>
    );
  }

  return (
    <div
      className="hva-pos-selected"
      data-testid="selected-zone-position"
      data-has-position="true"
    >
      <p className="judge-card-fact" data-testid="selected-zone-id">
        {analysisAreaLabel(view.selected.zoneId) ?? "Selected analysis area"}
      </p>
      <p className="kicker">{SELECTED_POSITION_KICKER}</p>
      <PositionAxis
        marks={[view.selected]}
        selectedZoneId={view.selected.zoneId}
        assistive={view.selectedAssistive ?? SELECTED_POSITION_KICKER}
        testId="selected-zone-position-axis"
      />
      <p className="hva-pos-axis-labels">
        <span>{view.axisLow}</span>
        <span>{view.axisHigh}</span>
      </p>
      <details className="hva-pos-details" data-testid="selected-zone-geoid">
        <summary>{GEOID_DETAILS_SUMMARY}</summary>
        <p>{view.selected.zoneId}</p>
      </details>
      <details className="hva-pos-details" data-testid="selected-zone-qa-details">
        <summary>{SELECTED_DETAILS_SUMMARY}</summary>
        <p data-testid="selected-zone-qa-exact">q_A {view.selectedExact}</p>
      </details>
    </div>
  );
}
