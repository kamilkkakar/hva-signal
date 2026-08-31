import {
  CHIP_CLOCK,
  CHIP_NOT_CITY,
  CHIP_NOT_LIVE,
  CHIP_SOURCE,
  CHIP_WINDOW,
  CHIP_WINDOW_ID,
  CONTEXT_ARIA,
} from "./copy";
import type { PublicSourceChip } from "./sourceChip";

type ContextBarProps = {
  source: PublicSourceChip;
  clockDate?: string | null;
  bannerLabel?: string;
  showChips?: boolean;
};

export function ContextBar({
  source,
  clockDate,
  bannerLabel,
  showChips = true,
}: ContextBarProps) {
  const clock = clockDate ? `${clockDate} ${CHIP_CLOCK}` : CHIP_CLOCK;

  return (
    <section className="judge-context" aria-label={CONTEXT_ARIA} data-testid="context-bar">
      <p className="judge-sr" data-testid="source-banner">
        {bannerLabel ?? "UNAVAILABLE"}
      </p>
      {showChips ? (
      <ul className="judge-chips">
        <li data-chip="window-id">{CHIP_WINDOW_ID}</li>
        <li data-chip="window">{CHIP_WINDOW}</li>
        <li data-chip="not-city">{CHIP_NOT_CITY}</li>
        <li data-chip="clock">{clock}</li>
        <li data-chip="source" data-testid="context-source">
          {source === "REPLAY" ? CHIP_SOURCE : source.toLowerCase()}
        </li>
        <li data-chip="not-live">{CHIP_NOT_LIVE}</li>
      </ul>
      ) : null}
    </section>
  );
}
