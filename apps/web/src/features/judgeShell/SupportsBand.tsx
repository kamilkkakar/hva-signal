import {
  DOES_NOT_BULLETS,
  DOES_NOT_TITLE,
  SUPPORTS_BULLETS,
  SUPPORTS_CONTEXT,
  SUPPORTS_TITLE,
} from "./copy";

export function SupportsBand() {
  return (
    <section
      className="judge-supports"
      aria-label="What evidence supports and does not"
      data-testid="supports-band"
    >
      <div>
        <p className="kicker">{SUPPORTS_TITLE}</p>
        <ul>
          {SUPPORTS_BULLETS.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div>
        <p className="kicker">{DOES_NOT_TITLE}</p>
        <ul>
          {DOES_NOT_BULLETS.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <p className="judge-supports-context">{SUPPORTS_CONTEXT}</p>
    </section>
  );
}
