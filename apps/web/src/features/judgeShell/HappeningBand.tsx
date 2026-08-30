import type { HappeningView } from "./happening";

type HappeningBandProps = {
  happening: HappeningView;
  busy: boolean;
  showRecovery: boolean;
  canResubmit: boolean;
  onResubmit: () => void;
};

export function HappeningBand({
  happening,
  busy,
  showRecovery,
  canResubmit,
  onResubmit,
}: HappeningBandProps) {
  return (
    <section
      className="judge-happening"
      aria-label="What is happening"
      aria-live="polite"
      aria-busy={busy}
      data-testid="happening-band"
    >
      <p className="kicker">What is happening</p>
      <p
        className="judge-stamp"
        data-testid="happening-stamp"
        data-ranking-state={happening.rankingState}
      >
        {happening.stamp}
      </p>
      <p className="judge-sr" data-testid="evidence-state">
        {happening.rankingState}
      </p>
      <p className="judge-happening-line" data-testid="happening-line">
        {happening.line}
      </p>
      {showRecovery && (
        <p className="judge-recovery">
          <button
            type="button"
            className="submit-btn"
            data-testid="resubmit-job"
            disabled={!canResubmit}
            onClick={onResubmit}
          >
            Resubmit
          </button>
        </p>
      )}
    </section>
  );
}
