/**
 * Explore City outlook — no auto-fetch. Forecast only after audit SUPPORTS.
 */
export function OutlookPanel({ forecastSupported = false }: { forecastSupported?: boolean }) {
  return (
    <section
      className="ws-outlook-panel"
      data-testid="hva-outlook-panel"
      data-forecast={forecastSupported ? "supported" : "blocked"}
      aria-label="Thermal outlook"
    >
      <p className="ws-control-label">Outlook</p>
      {forecastSupported ? (
        <p>
          Forecast contract supported. Run an explicit outlook request when ready — nothing
          auto-fetches here.
        </p>
      ) : (
        <p data-testid="hva-outlook-blocked">
          Thermal Outlook unavailable until forecast contract is confirmed. No horizons are
          invented on this surface.
        </p>
      )}
      <p className="ws-gate-sentence">
        Outlook does not claim overnight recovery, 24-hour profiles, or intervention efficacy.
      </p>
    </section>
  );
}
