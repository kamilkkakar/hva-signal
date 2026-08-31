import { useState } from "react";
import { SECTION_NAV } from "./copy";

export function SectionNav() {
  const [index, setIndex] = useState(0);
  const current = SECTION_NAV[index] ?? SECTION_NAV[0]!;
  const total = SECTION_NAV.length;

  return (
    <nav className="hx-section-nav" aria-label="Evidence sections" data-testid="section-nav">
      <div className="hx-section-nav-compact" data-testid="section-nav-compact">
        <p className="hx-section-nav-index">
          <span className="hx-section-num">
            {current.num} / {String(total).padStart(2, "0")}
          </span>
          <a href={`#${current.id}`} className="hx-section-title">
            {current.title}
          </a>
        </p>
        <div className="hx-section-nav-controls">
          <button
            type="button"
            data-testid="section-nav-prev"
            disabled={index === 0}
            onClick={() => setIndex((value) => Math.max(0, value - 1))}
          >
            Previous
          </button>
          <button
            type="button"
            data-testid="section-nav-next"
            disabled={index >= total - 1}
            onClick={() => setIndex((value) => Math.min(total - 1, value + 1))}
          >
            Next
          </button>
        </div>
      </div>
      <ol className="hx-section-nav-list">
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
