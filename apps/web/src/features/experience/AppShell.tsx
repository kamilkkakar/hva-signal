import { BADGE_KICKER, BADGE_MODE, BADGE_PROVIDER, HERO_LINE, HERO_SUPPORT, MODE_LINE, PLACE_LINE, PRODUCT_EXPANSION, WORDMARK } from "./copy";

type AppShellProps = {
  observationStamp?: string | null;
};

export function AppShell({ observationStamp = null }: AppShellProps) {
  return (
    <header className="hx-shell" data-testid="hx-app-shell">
      <div className="hx-shell-brand">
        <p className="hx-kicker">3K Labs</p>
        <h1>{WORDMARK}</h1>
        <p className="hx-expansion">{PRODUCT_EXPANSION}</p>
      </div>
      <p className="hx-hero-line">{HERO_LINE}</p>
      <p className="hx-hero-support">{HERO_SUPPORT}</p>
      <div className="hx-shell-meta">
        <p className="hx-place">{PLACE_LINE}</p>
        <p className="hx-mode" data-testid="source-mode">
          {MODE_LINE}
        </p>
        <p className="hx-badge" data-testid="fortyguard-badge">
          <span>{BADGE_KICKER}</span>
          <strong>{BADGE_PROVIDER}</strong>
          <span>
            {BADGE_MODE}
            {observationStamp ? ` · ${observationStamp}` : ""}
          </span>
        </p>
      </div>
    </header>
  );
}
