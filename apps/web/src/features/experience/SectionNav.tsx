import { SECTION_NAV } from "./copy";

export function SectionNav() {
  return (
    <nav className="hx-section-nav" aria-label="Evidence sections" data-testid="section-nav">
      <ol>
        {SECTION_NAV.map((item) => (
          <li key={item.id}>
            <a href={`#${item.id}`}>
              <span className="hx-section-num">{item.num}</span>
              <span className="hx-section-title">{item.title}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
