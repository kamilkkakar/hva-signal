import type { QuestionDef } from "@/contracts";
import type { AnalysisArea, AnalysisAreaId, MapModeId, MapModeModel } from "@/contracts";
import { AREA_EXPLAIN_ONCE } from "@/ia/copy";
import { DataStoryGrid } from "@/components/story/DataStoryGrid";
import { ChartSet } from "@/components/charts";
import { SpatialMap } from "@/components/map/SpatialMap";
import { SelectedArea } from "@/components/area/SelectedArea";
import { ComparisonPanel } from "@/components/comparison/ComparisonPanel";
import { InterventionPanel } from "@/components/intervention/InterventionPanel";
import { VulnerabilityPanel } from "@/components/vulnerability/VulnerabilityPanel";

type QuestionViewProps = {
  readonly question: QuestionDef;
  readonly areas: readonly AnalysisArea[];
  readonly mapMode: MapModeModel;
  readonly selectedAreaId: AnalysisAreaId | null;
  readonly compareAreaId: AnalysisAreaId | null;
  readonly onSelectArea: (id: AnalysisAreaId) => void;
  readonly onSelectMode: (id: MapModeId) => void;
  readonly onCompare: (id: AnalysisAreaId | null) => void;
};

export function QuestionView({
  question,
  areas,
  mapMode,
  selectedAreaId,
  compareAreaId,
  onSelectArea,
  onSelectMode,
  onCompare,
}: QuestionViewProps) {
  return (
    <div className="canvas" id="decision-main" data-testid="question-view">
      <header className="question-head">
        <p>Question {String(question.index).padStart(2, "0")}</p>
        <h2>{question.prompt}</h2>
        {question.index === 1 ? <p className="area-once">{AREA_EXPLAIN_ONCE}</p> : null}
      </header>
      <DataStoryGrid ids={question.storyCardIds} />
      <SpatialMap
        mode={mapMode}
        selectedAreaId={selectedAreaId}
        onSelectArea={onSelectArea}
        onSelectMode={onSelectMode}
      />
      <SelectedArea areas={areas} selectedAreaId={selectedAreaId} />
      {question.id === "unusual-for-place" || question.id === "years-direction" ? (
        <ComparisonPanel
          areas={areas}
          selectedAreaId={selectedAreaId}
          compareAreaId={compareAreaId}
          onCompare={onCompare}
        />
      ) : null}
      {question.id === "after-intervention" ? (
        <InterventionPanel selectedAreaId={selectedAreaId} />
      ) : null}
      {question.id === "capacity-to-cope" ? <VulnerabilityPanel /> : null}
      <ChartSet kinds={question.chartIds} selectedAreaId={selectedAreaId} />
    </div>
  );
}
