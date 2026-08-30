import {
  EYEBROW,
  HERO_HONESTY,
  HERO_LINE,
  HERO_SUPPORT,
  HERO_TAGLINE,
  PRODUCT_EXPANSION,
  WORDMARK,
} from "./copy";

export function HeroHeader() {
  return (
    <header className="judge-hero" data-hero-variant="v1-decision">
      <p className="eyebrow">{EYEBROW}</p>
      <h1>{WORDMARK}</h1>
      <p className="judge-hero-line" data-testid="hero-line">
        {HERO_LINE}
      </p>
      <details className="judge-hero-more" data-testid="hero-more">
        <summary>About this demonstration</summary>
        <p className="product-expansion">{PRODUCT_EXPANSION}</p>
        <p className="judge-hero-support">{HERO_SUPPORT}</p>
        <p className="judge-hero-honesty">{HERO_HONESTY}</p>
        <p className="judge-hero-tagline">{HERO_TAGLINE}</p>
      </details>
    </header>
  );
}
