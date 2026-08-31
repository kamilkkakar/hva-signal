type TimeLensProps = {
  packageId: string | null;
  reason: string;
};

/**
 * Compare Time lens — only meaningful after CROSS_CITY_MATCHED_INSTANTS_V1 exists.
 * Renders an honest blocked/pending state until evidence is acquired.
 */
export function TimeLens({ packageId, reason }: TimeLensProps) {
  const ready = Boolean(packageId);
  return (
    <div
      className="hx-cc-time-lens"
      data-testid="compare-time-lens"
      data-ready={ready ? "true" : "false"}
    >
      <p className="hx-kicker">Time</p>
      <h3>Matched observation clocks</h3>
      {ready ? (
        <p className="hx-note" data-testid="compare-time-package">
          Evidence package {packageId} is available for matched-instant comparison.
        </p>
      ) : (
        <p className="hx-note" data-testid="compare-time-blocked">
          {reason}
        </p>
      )}
      <p className="hx-note">
        No overnight recovery, 24-hour profile, or efficacy claim is shown here. Time comparison
        stays descriptive and evidence-gated.
      </p>
    </div>
  );
}
