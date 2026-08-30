import { NO_COMBINED_SCORE_COPY } from "./copy";
import { resolveSignalFeatureFlags, type SignalFeatureFlags } from "./flags";
import { presentTwoSignals } from "./presentation";
import { SignalASection } from "./SignalASection";
import { SignalBSection } from "./SignalBSection";
import "./signals.css";
import type { HistoricalSection, SelectedTimeSection } from "./types";

export type SignalRailProps = {
  historical: HistoricalSection;
  selectedTime: SelectedTimeSection;
  flags?: Partial<SignalFeatureFlags>;
  onConfirmLiveDemo?: () => void;
  onDeclineLiveDemo?: () => void;
};

export function SignalRail({
  historical,
  selectedTime,
  flags,
  onConfirmLiveDemo,
  onDeclineLiveDemo,
}: SignalRailProps) {
  const resolved = resolveSignalFeatureFlags(flags);
  const view = presentTwoSignals({
    historical,
    selectedTime,
    flags: resolved,
  });

  if (!view.mounted) {
    return null;
  }

  return (
    <aside
      className="decision signals-rail"
      aria-label="Independent signals"
      data-testid="signal-rail"
      data-combined-score-authorized="false"
      data-overall-complete="false"
    >
      <header className="rail-head">
        <p className="kicker">Signals</p>
        <h2>Independent A / B</h2>
      </header>
      <p className="copilot-note" data-testid="no-account">
        {NO_COMBINED_SCORE_COPY} This surface does not require an account.
      </p>
      <SignalASection view={view.historical} />
      <SignalBSection
        view={view.selected_time}
        onConfirmLiveDemo={onConfirmLiveDemo}
        onDeclineLiveDemo={onDeclineLiveDemo}
      />
    </aside>
  );
}
