export type HvaStage = "heat" | "context" | "action" | "outlook";

type HvaStoryRailProps = {
  stage: HvaStage;
  onStageChange: (stage: HvaStage) => void;
};

const STAGES: { id: HvaStage; label: string; testId: string }[] = [
  { id: "heat", label: "Heat", testId: "hva-stage-heat" },
  { id: "context", label: "Context", testId: "hva-stage-context" },
  { id: "action", label: "Action", testId: "hva-stage-action" },
  { id: "outlook", label: "Outlook", testId: "hva-stage-outlook" },
];

export function HvaStoryRail({ stage, onStageChange }: HvaStoryRailProps) {
  return (
    <nav
      className="ws-hva-rail"
      data-testid="hva-story-rail"
      aria-label="HVA story stages"
    >
      {STAGES.map((item) => (
        <button
          key={item.id}
          type="button"
          className="ws-hva-rail-btn"
          data-testid={item.testId}
          data-active={stage === item.id ? "true" : "false"}
          aria-pressed={stage === item.id}
          onClick={() => onStageChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
