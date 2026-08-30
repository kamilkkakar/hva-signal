import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { ActionFraming, ActionSupportsBand } from "./ActionSupportsBand";
import {
  ACTION_V0_STATUS,
  DOES_NOT_COLUMN_LABEL,
  FORBIDDEN_ACTION_PHRASES,
  INSUFFICIENT_STAMP,
  SUFFICIENT_STAMP,
  SUPPORTS_COLUMN_LABEL,
} from "./copy";

const here = path.dirname(fileURLToPath(import.meta.url));

function sufficientResult(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "SUFFICIENT",
    hazard_spread: { differentiation_state: "SUFFICIENT" },
    zones: [{ zone_id: "1", thermal_ordering_permitted: true }],
  };
}

function insufficientResult(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    hazard_spread: { differentiation_state: "INSUFFICIENT" },
    zones: [{ zone_id: "1", thermal_ordering_permitted: false }],
  };
}

describe("ActionSupportsBand", () => {
  it("renders the Hybrid supports / does-not columns for a sufficient night", () => {
    const html = renderToStaticMarkup(
      createElement(ActionSupportsBand, {
        status: "complete",
        result: sufficientResult(),
      }),
    );
    expect(html).toContain('data-testid="action-v0"');
    expect(html).toContain('data-hybrid-slot="supports-does-not"');
    expect(html).toContain('data-action-kind="sufficient"');
    expect(html).toContain(SUFFICIENT_STAMP);
    expect(html).toContain(ACTION_V0_STATUS);
    expect(html).toContain(SUPPORTS_COLUMN_LABEL);
    expect(html).toContain(DOES_NOT_COLUMN_LABEL);
    expect(html).toContain("one input");
    expect(html).toContain("does not authorize automatic deployment");
    expect(html).toContain("Vulnerability");
  });

  it("renders withhold copy when Decision 8 is insufficient", () => {
    const html = renderToStaticMarkup(
      createElement(ActionSupportsBand, {
        status: "complete",
        result: insufficientResult(),
      }),
    );
    expect(html).toContain('data-action-kind="insufficient"');
    expect(html).toContain(INSUFFICIENT_STAMP);
    expect(html).toContain("Do not use thermal ranking alone");
    expect(html).toContain("not a safety clearance");
  });

  it("keeps ActionFraming as the same Hybrid band", () => {
    const band = renderToStaticMarkup(
      createElement(ActionSupportsBand, {
        status: "complete",
        result: sufficientResult(),
      }),
    );
    const alias = renderToStaticMarkup(
      createElement(ActionFraming, {
        status: "complete",
        result: sufficientResult(),
      }),
    );
    expect(alias).toBe(band);
  });

  it("keeps published markup free of efficacy and dispatch claims", () => {
    const html = [
      renderToStaticMarkup(
        createElement(ActionSupportsBand, {
          status: "complete",
          result: sufficientResult(),
        }),
      ),
      renderToStaticMarkup(
        createElement(ActionSupportsBand, {
          status: "complete",
          result: insufficientResult(),
        }),
      ),
    ]
      .join("\n")
      .toLowerCase();
    for (const phrase of FORBIDDEN_ACTION_PHRASES) {
      expect(html.includes(phrase)).toBe(false);
    }
    expect(html).not.toMatch(/%/);
  });
});

describe("Hybrid relocation", () => {
  it("lives under judgeShell/action and stays off the Decision rail", () => {
    const rail = readFileSync(
      path.join(here, "../../command-center/DecisionRail.tsx"),
      "utf8",
    );
    const shell = readFileSync(
      path.join(here, "../../command-center/CommandCenterShell.tsx"),
      "utf8",
    );
    const band = readFileSync(path.join(here, "ActionSupportsBand.tsx"), "utf8");
    expect(rail).not.toContain("ActionFraming");
    expect(rail).not.toContain("ActionSupportsBand");
    expect(rail).not.toContain("judgeShell/action");
    expect(rail).not.toContain("@/features/action");
    expect(shell).not.toContain("ActionFraming");
    expect(shell).not.toContain("ActionSupportsBand");
    expect(band).toContain('data-hybrid-slot="supports-does-not"');
  });
});
