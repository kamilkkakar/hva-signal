import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const css = readFileSync(path.join(here, "judgeShell.css"), "utf8");
const storyCss = readFileSync(
  path.join(here, "resultStory/resultStory.css"),
  "utf8",
);

describe("laptop first-read map visibility", () => {
  it("compacts hero and story at ≤1440 so the map can enter the first viewport", () => {
    expect(css).toContain("@media (max-width: 1440px)");
    expect(css).toContain("calc(100vh - 13.5rem)");
    expect(css).toMatch(/\.judge-hero-support[\s\S]*display:\s*none/);
    expect(css).toMatch(/\.judge-happening-line[\s\S]*display:\s*none/);
    expect(storyCss).toContain("@media (max-width: 1440px)");
    expect(storyCss).toMatch(/\.result-story-supports-grid[\s\S]*display:\s*none/);
    expect(storyCss).toMatch(/\.result-story-how[\s\S]*display:\s*none/);
  });

  it("does not restore a 3-column rail or hide page overflow", () => {
    expect(css).not.toMatch(/260px\s+1fr\s+300px/);
    expect(css).not.toContain("minmax(0, 16.25rem) minmax(0, 1fr) minmax(0, 18.75rem)");
    expect(css).not.toMatch(/\.judge-shell\s*\{[^}]*overflow-x:\s*hidden/s);
    expect(css).not.toMatch(/overflow-x:\s*auto/);
  });
});
