import { describe, expect, it } from "vitest";
import { presentMatched } from "@/features/judgeShell/decision/present";

/**
 * Stale-response safety: when selection advances A→B, docs bound to A must not
 * present as B. Sequence tokens / boundZoneId gate presentation.
 */
describe("stale area evidence safety", () => {
  it("does not present prior-area matched docs under a new selection id", () => {
    const docA = {
      selected_area: {
        mean_by_year: { "2022": 30, "2023": 31, "2024": 32 },
        change_2024_vs_2022: 2,
        matched_nights_warmer: 10,
        matched_nights: 12,
      },
      analysis_geography: { median_change_2024_vs_2022: 1.5 },
    };
    // Product gate: boundZoneId !== selectedZoneId ⇒ present with null active id.
    const activeZoneId = null;
    const gated = presentMatched(activeZoneId, docA as never, null);
    expect(gated.status).not.toBe("AVAILABLE");
  });

  it("rapid selection final id wins over intermediate sequence tokens", () => {
    let sequence = 0;
    let applied: string | null = null;
    const select = (id: string) => {
      const token = ++sequence;
      const apply = (responseFor: string, tokenAtStart: number) => {
        if (tokenAtStart === sequence) {
          applied = responseFor;
        }
      };
      return { token, apply };
    };
    const a = select("A");
    const b = select("B");
    const c = select("C");
    const d = select("D");
    const e = select("E");
    a.apply("A", a.token);
    c.apply("C", c.token);
    b.apply("B", b.token);
    d.apply("D", d.token);
    e.apply("E", e.token);
    expect(applied).toBe("E");
    expect(sequence).toBe(5);
  });
});

describe("default area init rule", () => {
  it("initializes default only once when selection is missing", () => {
    const DEFAULT = "04013107401";
    let selected: string | null = null;
    let initDone = false;
    const init = () => {
      if (initDone) {
        return;
      }
      initDone = true;
      if (!selected) {
        selected = DEFAULT;
      }
    };
    init();
    expect(selected).toBe(DEFAULT);
    selected = "04013107500";
    // metrics reload / map mode / capability load must not re-init
    init();
    init();
    expect(selected).toBe("04013107500");
    expect(initDone).toBe(true);
  });
});
