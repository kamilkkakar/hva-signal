import type { WorkspaceMode } from "./types";

type WorkspaceHeaderProps = {
  mode: WorkspaceMode;
  onModeChange: (mode: WorkspaceMode) => void;
};

export function WorkspaceHeader({ mode, onModeChange }: WorkspaceHeaderProps) {
  return (
    <header className="ws-header" data-testid="workspace-header">
      <div className="ws-brand">
        <span className="ws-lab">3K LABS</span>
        <h1 className="ws-wordmark">HVA-SIGNAL</h1>
        <span className="ws-subtitle">Heat, Vulnerability &amp; Action Signal</span>
      </div>
      <nav className="ws-modes" role="tablist" aria-label="Workspace mode" data-testid="workspace-modes">
        <button
          type="button"
          role="tab"
          className="ws-mode-tab"
          aria-selected={mode === "explore"}
          data-testid="mode-explore"
          onClick={() => onModeChange("explore")}
        >
          Explore City
        </button>
        <button
          type="button"
          role="tab"
          className="ws-mode-tab"
          aria-selected={mode === "compare"}
          data-testid="mode-compare"
          onClick={() => onModeChange("compare")}
        >
          Compare Cities
        </button>
      </nav>
    </header>
  );
}
