import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const css = readFileSync(path.join(here, "judgeShell.css"), "utf8");

describe("judge shell overflow architecture", () => {
  it("is a contained map-primary stack, not a 3-column rail", () => {
    expect(css).toContain("flex-direction: column");
    expect(css).toContain("min-width: 0");
    expect(css).toContain("max-width: 100%");
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("word-break: break-word");
    expect(css).toContain("flex-wrap: wrap");
    expect(css).not.toMatch(/260px\s+1fr\s+300px/);
    expect(css).not.toContain("minmax(0, 16.25rem) minmax(0, 1fr) minmax(0, 18.75rem)");
    expect(css).not.toContain("shell-grid");
  });

  it("does not hide page overflow and does not invite a panel scrollbar", () => {
    expect(css).not.toMatch(/\.judge-shell\s*\{[^}]*overflow-x:\s*hidden/s);
    expect(css).not.toMatch(/overflow-x:\s*auto/);
    expect(css).toMatch(/\.judge-stamp\s*\{[^}]*max-width:\s*100%/s);
    expect(css).toMatch(/\.judge-stamp\s*\{[^}]*overflow-wrap:\s*anywhere/s);
    expect(css).toMatch(/\.judge-map\s*\{[^}]*min-width:\s*0/s);
    expect(css).toMatch(/\.judge-map\s*\{[^}]*max-width:\s*100%/s);
  });
});
