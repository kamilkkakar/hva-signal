import {
  LIVE_DEMO_PRIMARY,
  LIVE_DEMO_SECONDARY,
  LIVE_DEMO_TITLE,
} from "./copy";
import type { SelectedTimeView } from "./types";

type SignalBSectionProps = {
  view: SelectedTimeView;
  onConfirmLiveDemo?: () => void;
  onDeclineLiveDemo?: () => void;
};

export function SignalBSection({
  view,
  onConfirmLiveDemo,
  onDeclineLiveDemo,
}: SignalBSectionProps) {
  return (
    <section
      className="signals-section"
      data-testid="signal-b"
      data-b-state={view.ux}
      aria-label="Signal B selected-time snapshot"
    >
      <p className="kicker">Signal B</p>
      <p className="job-id">{view.title}</p>
      <p
        className="signals-stamp evidence-stamp"
        data-testid="signal-b-availability"
        data-b-tone={view.ux}
      >
        {view.stamp}
      </p>
      {view.source && (
        <p className="job-id" data-testid="signal-b-source">
          Provenance {view.source}
          {view.source !== "UNAVAILABLE" && view.source !== "FETCHING"
            ? " · not live"
            : ""}
        </p>
      )}
      <p className="decision-copy" data-testid="signal-b-reuse">
        {view.reuse_only}
      </p>
      <p className="decision-copy">{view.copy}</p>
      {view.coverage_label && <p className="job-id">{view.coverage_label}</p>}
      {view.range_label && <p className="job-id">{view.range_label}</p>}
      {view.zones.length > 0 && (
        <ul className="signals-zone-list" data-testid="signal-b-zones">
          {view.zones.map((zone) => (
            <li key={zone.zone_id}>
              {zone.zone_id}{" "}
              {zone.mean_temperature_c == null ? (
                <span className="signals-zone-unknown">unknown</span>
              ) : (
                `${zone.mean_temperature_c} °C`
              )}
            </li>
          ))}
        </ul>
      )}
      {view.show_live_demo && (
        <div className="recovery" data-testid="live-demo-confirmation">
          <p>{LIVE_DEMO_TITLE}</p>
          <p>{view.copy}</p>
          <button type="button" className="submit-btn" onClick={onConfirmLiveDemo}>
            {LIVE_DEMO_PRIMARY}
          </button>
          <button type="button" className="text-btn" onClick={onDeclineLiveDemo}>
            {LIVE_DEMO_SECONDARY}
          </button>
        </div>
      )}
    </section>
  );
}
