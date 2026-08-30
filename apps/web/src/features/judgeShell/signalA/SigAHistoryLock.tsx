import type { SignalAView } from "./types";

type SigAHistoryLockProps = {
  view: SignalAView;
};

export function SigAHistoryLock({ view }: SigAHistoryLockProps) {
  if (view.kind !== "history_not_prepared" && view.kind !== "history_too_thin") {
    return null;
  }
  return (
    <p className="siga-history-lock" data-testid="siga-history-lock">
      {view.body}
    </p>
  );
}
