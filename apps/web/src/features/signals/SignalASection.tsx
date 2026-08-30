import { SIGNAL_A_FROZEN_HOUR } from "./types";
import type { HistoricalView } from "./types";

type SignalASectionProps = {
  view: HistoricalView;
};

export function SignalASection({ view }: SignalASectionProps) {
  return (
    <section
      className="signals-section"
      data-testid="signal-a"
      data-a-state={view.ux}
      data-a-tone={view.tone}
      aria-label="Signal A historical"
    >
      <p className="kicker">Signal A</p>
      <p
        className="signals-stamp evidence-stamp"
        data-testid="signal-a-availability"
        data-tone={view.tone}
      >
        {view.stamp}
      </p>
      {view.copy.map((paragraph) => (
        <p key={paragraph} className="decision-copy">
          {paragraph}
        </p>
      ))}
      <p className="job-id">
        Frozen hour {SIGNAL_A_FROZEN_HOUR} AOI-local. Not selected-time.
      </p>
    </section>
  );
}
