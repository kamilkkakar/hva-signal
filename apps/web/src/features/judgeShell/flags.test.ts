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

  it("mounts JudgeShell from App unless VITE_HVA_JUDGE_SHELL is 0", () => {
    const app = readFileSync(path.resolve(here, "../../app/App.tsx"), "utf8");
    const lines = app.trim().split(/\r?\n/);
    expect(lines).toHaveLength(5);
    expect(app).toContain("JudgeShell");
    expect(app).toContain("CommandCenterShell");
    expect(app).toContain('VITE_HVA_JUDGE_SHELL === "0"');
    expect(app.toLowerCase()).not.toMatch(/log in|login|sign up|signup|oauth/);
  });
});
