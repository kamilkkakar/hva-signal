import type { OutlookPlan } from "./outlookEngine";

type OutlookPanelProps = {
  plan: OutlookPlan;
  forecastSupported?: boolean;
};

/** Evidence-aware outlook. It plans observations; it never auto-fetches. */
export function OutlookPanel({ plan, forecastSupported = false }: OutlookPanelProps) {
  return (
    <section
      className="ws-outlook-panel"
      data-testid="hva-outlook-panel"
      data-forecast={forecastSupported ? "supported" : "blocked"}
      data-outlook-state={plan.state}
      aria-label="Thermal outlook"
    >
      <p className="ws-control-label">Outlook</p>
      {forecastSupported ? (
        <p>
          Forecast contract supported. Run an explicit outlook request when ready — nothing
          auto-fetches here.
        </p>
      ) : (
        <div data-testid="hva-outlook-blocked">
          <p className="ws-outlook-summary" data-testid="hva-outlook-summary">
            {plan.summary}
          </p>
          <ol className="ws-outlook-steps" data-testid="hva-outlook-steps">
            {plan.steps.map((step) => (
              <li key={step.id} data-outlook-step={step.id}>
                <span>{step.label}</span>
                <span className="ws-outlook-why">{step.whyShown}</span>
              </li>
            ))}
          </ol>
          <p className="ws-outlook-basis" data-testid="hva-outlook-basis">
            Decision basis: {plan.basis}.
          </p>
          <p data-testid="hva-outlook-forecast-blocked">
            Forecast remains blocked until a documented horizon exists. No predicted temperatures
            are shown here.
          </p>
        </div>
      )}
      <p className="ws-gate-sentence">
        No automatic request is made. Outlook does not claim overnight recovery, continuous
        conditions, or intervention efficacy.
      </p>
    </section>
  );
}
