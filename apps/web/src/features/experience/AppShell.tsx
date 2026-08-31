import {
  BADGE_KICKER,
  BADGE_PROVIDER,
  HERO_LINE,
  HERO_SUPPORT,
  PLACE_LINE,
  PRODUCT_BADGE,
  PRODUCT_EXPANSION,
  WORDMARK,
} from "./copy";

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
        <p className="hx-hero-line">{HERO_LINE}</p>
        <p className="hx-hero-support">{HERO_SUPPORT}</p>
      </div>
      <div className="hx-shell-meta">
        <p className="hx-product-badge" data-testid="product-badge">
          {PRODUCT_BADGE}
        </p>
        <p className="hx-place">{PLACE_LINE}</p>
        <p className="hx-mode" data-testid="source-mode">
          {BADGE_KICKER}
        </p>
        <p className="hx-badge" data-testid="fortyguard-badge">
          <strong>{BADGE_PROVIDER}</strong>
          {observationStamp ? <span>{observationStamp}</span> : null}
        </p>
      </div>
    </header>
  );
}
