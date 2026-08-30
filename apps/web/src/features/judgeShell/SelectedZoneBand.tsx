import { SELECTED_ZONE_EMPTY } from "./copy";

export function SelectedZoneBand() {
  return (
    <section
      className="judge-zone"
      aria-label="Selected zone"
      data-testid="selected-zone"
    >
      <p className="kicker">Selected zone</p>
      <p className="judge-card-fact">{SELECTED_ZONE_EMPTY}</p>
    </section>
  );
}
