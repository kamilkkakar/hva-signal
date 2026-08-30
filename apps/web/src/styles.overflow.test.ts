import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const css = readFileSync(path.join(here, "styles.css"), "utf8");

describe("result layout overflow contracts", () => {
  it("zeros grid min-content so 1fr and rails cannot blow the page", () => {
    expect(css).toContain(
      "grid-template-columns: minmax(0, 16.25rem) minmax(0, 1fr) minmax(0, 18.75rem);",
    );
    expect(css).toMatch(/\.shell-grid\s*>\s*\*\s*\{[^}]*min-width:\s*0/);
    expect(css).not.toMatch(/\.shell-grid\s*\{[^}]*grid-template-columns:\s*260px\s+1fr\s+300px/);
  });

  it("wraps analysis prose instead of relying on overflow-x:auto", () => {
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("word-break: break-word");
    expect(css).toContain("overflow-x: hidden");
    expect(css).toContain("overflow-y: auto");
    expect(css).not.toMatch(/\.decision \{[^}]*overflow: auto/);
    expect(css).not.toMatch(/html,\s*\nbody,\s*\n#root \{[^}]*overflow-x: hidden/s);
  });

  it("keeps limitation boxes inside the column and long analysis full-width", () => {
    expect(css).toMatch(/\.decision-limitation\s*\{[^}]*max-width:\s*100%/s);
    expect(css).toContain("grid-column: 1 / -1");
    expect(css).toContain(".analysis-detail");
    expect(css).toContain(".copyable-token");
    expect(css).toContain("text-overflow: ellipsis");
  });
});
