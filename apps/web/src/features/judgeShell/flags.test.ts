import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { isJudgeShellEnabled } from "./flags";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("judge shell flag", () => {
  it("defaults ON so this branch lands the Hybrid IA product", () => {
    expect(isJudgeShellEnabled()).toBe(true);
  });

  it("mounts Workspace from App (dynamic city workspace)", () => {
    const app = readFileSync(path.resolve(here, "../../app/App.tsx"), "utf8");
    expect(app).toContain("Workspace");
    expect(app.toLowerCase()).not.toMatch(/log in|login|sign up|signup|oauth/);
  });
});
