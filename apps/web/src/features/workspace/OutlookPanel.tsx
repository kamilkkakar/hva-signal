/**
 * Explore City outlook — no auto-fetch. Forecast only after audit SUPPORTS.
 * Blocked state is guidance ("what to watch next"), not a fake forecast.
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
        <div data-testid="hva-outlook-blocked">
          <p>What to watch next</p>
          <ul>
            <li>Run live — use an explicit selected-time request when the bounded live path is enabled.</li>
            <li>Compare observed times — review published 15:00 snapshots on Compare → Snapshot.</li>
            <li>Open Compare → Time — available after matched-instant evidence lands (not yet).</li>
          </ul>
          <p data-testid="hva-outlook-forecast-blocked">
            Forecast remains blocked until a documented horizon exists. No predicted temperatures
            are shown here.
          </p>
        </div>
      )}
      <p className="ws-gate-sentence">
        Outlook does not claim overnight recovery, 24-hour profiles, or intervention efficacy.
      </p>
    </section>
  );
}
