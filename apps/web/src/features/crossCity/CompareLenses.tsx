import { useState } from "react";
import type { ReactNode } from "react";

export type CompareLensId = "snapshot" | "context" | "time";

type CompareLensTabsProps = {
  lens: CompareLensId;
  onLensChange: (lens: CompareLensId) => void;
  timeEnabled: boolean;
};

const LENSES: { id: CompareLensId; label: string; testId: string }[] = [
  { id: "snapshot", label: "Snapshot", testId: "compare-lens-snapshot" },
  { id: "context", label: "Context", testId: "compare-lens-context" },
  { id: "time", label: "Time", testId: "compare-lens-time" },
];

export function CompareLensTabs({ lens, onLensChange, timeEnabled }: CompareLensTabsProps) {
  return (
    <div className="hx-cc-lens-tabs" role="tablist" aria-label="Compare lenses" data-testid="compare-lens-tabs">
      {LENSES.map((item) => {
        const disabled = item.id === "time" && !timeEnabled;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            data-testid={item.testId}
            aria-selected={lens === item.id}
            aria-disabled={disabled}
            disabled={disabled}
            className="hx-cc-lens-tab"
            onClick={() => {
              if (!disabled) onLensChange(item.id);
            }}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export function useCompareLens(initial: CompareLensId = "snapshot") {
  return useState<CompareLensId>(initial);
}

export function CompareLensPanel({
  lens,
  snapshot,
  context,
  time,
}: {
  lens: CompareLensId;
  snapshot: ReactNode;
  context: ReactNode;
  time: ReactNode;
}) {
  return (
    <div className="hx-cc-lens-panel" data-testid="compare-lens-panel" data-lens={lens}>
      {lens === "snapshot" ? snapshot : null}
      {lens === "context" ? context : null}
      {lens === "time" ? time : null}
    </div>
  );
}
