import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SourceTape } from "@/features/command-center/SourceTape";
import type { DataMode, JobStatus, ThermalDataSource } from "@/types";
import { sourceBannerLabel } from "./sourceBanner";

/**
 * PRE-FIX NON-REPLAY PROVENANCE MATRIX
 * Captured from sourceBannerLabel before the replay-precedence edit.
 * Expected labels are frozen here; do not recompute them from a later mapper.
 */
const PRE_FIX_NON_REPLAY_PROVENANCE_MATRIX: ReadonlyArray<{
  name: string;
  status: JobStatus | null;
  dataStatus?: string | null;
  thermalSource?: ThermalDataSource | null;
  expected: "FORTYGUARD LIVE" | "FORTYGUARD CACHED" | "PARTIAL" | "UNAVAILABLE";
}> = [
  {
    name: "no job",
    status: null,
    expected: "UNAVAILABLE",
  },
  {
    name: "queued job",
    status: "queued",
    expected: "UNAVAILABLE",
  },
  {
    name: "complete without provenance",
    status: "complete",
    expected: "UNAVAILABLE",
  },
  {
    name: "job status partial",
    status: "partial",
    expected: "PARTIAL",
  },
  {
    name: "data_status partial",
    status: "complete",
    dataStatus: "partial",
    expected: "PARTIAL",
  },
  {
    name: "job partial beats live data_status",
    status: "partial",
    dataStatus: "live",
    expected: "PARTIAL",
  },
  {
    name: "data_status unavailable",
    status: "complete",
    dataStatus: "unavailable",
    expected: "UNAVAILABLE",
  },
  {
    name: "unavailable beats explicit live source",
    status: "complete",
    dataStatus: "unavailable",
    thermalSource: "fortyguard_live",
    expected: "UNAVAILABLE",
  },
  {
    name: "data_status live",
    status: "complete",
    dataStatus: "live",
    expected: "FORTYGUARD LIVE",
  },
  {
    name: "thermal_source fortyguard_live",
    status: "complete",
    thermalSource: "fortyguard_live",
    expected: "FORTYGUARD LIVE",
  },
  {
    name: "live data_status beats cached source",
    status: "complete",
    dataStatus: "live",
    thermalSource: "fortyguard_cached",
    expected: "FORTYGUARD LIVE",
  },
  {
    name: "live source beats cached data_status",
    status: "complete",
    dataStatus: "cached",
    thermalSource: "fortyguard_live",
    expected: "FORTYGUARD LIVE",
  },
  {
    name: "generic data_status cached",
    status: "complete",
    dataStatus: "cached",
    expected: "FORTYGUARD CACHED",
  },
  {
    name: "thermal_source fortyguard_cached",
    status: "complete",
    thermalSource: "fortyguard_cached",
    expected: "FORTYGUARD CACHED",
  },
  {
    name: "cached status with null thermal_source",
    status: "complete",
    dataStatus: "cached",
    thermalSource: null,
    expected: "FORTYGUARD CACHED",
  },
];

describe("pre-fix non-replay provenance matrix", () => {
  it.each(PRE_FIX_NON_REPLAY_PROVENANCE_MATRIX)(
    "$name → $expected",
    ({ status, dataStatus, thermalSource, expected }) => {
      expect(
        sourceBannerLabel({
          status,
          dataStatus,
          thermalSource,
        }),
      ).toBe(expected);
    },
  );
});

describe("sourceBannerLabel", () => {
  it("is UNAVAILABLE when no job or provenance exists", () => {
    expect(sourceBannerLabel({ status: null })).toBe("UNAVAILABLE");
  });

  it("maps thermal sources without claiming live on replay", () => {
    expect(
      sourceBannerLabel({ status: "complete", thermalSource: "fortyguard_live" }),
    ).toBe("FORTYGUARD LIVE");
    expect(
      sourceBannerLabel({
        status: "complete",
        thermalSource: "fortyguard_cached",
      }),
    ).toBe("FORTYGUARD CACHED");
    expect(sourceBannerLabel({ status: "complete", thermalSource: "replay" })).toBe(
      "REPLAY",
    );
  });

  it("labels PARTIAL from job status or data status", () => {
    expect(sourceBannerLabel({ status: "partial" })).toBe("PARTIAL");
    expect(
      sourceBannerLabel({ status: "complete", dataStatus: "partial" }),
    ).toBe("PARTIAL");
  });

  it("does not label queued jobs as live", () => {
    expect(sourceBannerLabel({ status: "queued" })).toBe("UNAVAILABLE");
  });
});

describe("replay provenance precedence", () => {
  it("labels replay + generic cached as REPLAY, not FORTYGUARD CACHED", () => {
    const label = sourceBannerLabel({
      status: "complete",
      dataMode: "replay",
      dataStatus: "cached",
      thermalSource: null,
    });
    expect(label).toBe("REPLAY");
    expect(label).not.toBe("FORTYGUARD CACHED");
  });

  it("evaluates data_mode replay before the generic cached branch", () => {
    const cachedBranchInput = {
      status: "complete" as const,
      dataStatus: "cached",
      thermalSource: null,
    };
    expect(sourceBannerLabel(cachedBranchInput)).toBe("FORTYGUARD CACHED");
    expect(
      sourceBannerLabel({ ...cachedBranchInput, dataMode: "replay" }),
    ).toBe("REPLAY");
  });

  it("keeps replay ahead of an explicit vendor-cached source when data_mode is replay", () => {
    expect(
      sourceBannerLabel({
        status: "complete",
        dataMode: "replay",
        dataStatus: "cached",
        thermalSource: "fortyguard_cached",
      }),
    ).toBe("REPLAY");
  });

  it.each([
    {
      name: "live mode + cached status",
      dataMode: "live" as DataMode,
      dataStatus: "cached",
      thermalSource: undefined,
      expected: "FORTYGUARD CACHED" as const,
    },
    {
      name: "auto mode + cached status",
      dataMode: "auto" as DataMode,
      dataStatus: "cached",
      thermalSource: undefined,
      expected: "FORTYGUARD CACHED" as const,
    },
    {
      name: "live mode + fortyguard_live",
      dataMode: "live" as DataMode,
      thermalSource: "fortyguard_live" as const,
      expected: "FORTYGUARD LIVE" as const,
    },
    {
      name: "auto mode + fortyguard_cached",
      dataMode: "auto" as DataMode,
      thermalSource: "fortyguard_cached" as const,
      expected: "FORTYGUARD CACHED" as const,
    },
  ])(
    "does not change pre-fix non-replay label for $name",
    ({ dataMode, dataStatus, thermalSource, expected }) => {
      expect(
        sourceBannerLabel({
          status: "complete",
          dataMode,
          dataStatus,
          thermalSource,
        }),
      ).toBe(expected);
    },
  );
});

describe("SourceTape replay badge", () => {
  it("renders REPLAY for the Phoenix historical replay snapshot", () => {
    const label = sourceBannerLabel({
      status: "complete",
      dataMode: "replay",
      dataStatus: "cached",
      thermalSource: null,
    });
    const html = renderToStaticMarkup(createElement(SourceTape, { active: label }));
    expect(label).toBe("REPLAY");
    expect(html).toContain("Thermal source:");
    expect(html).toContain("REPLAY");
    expect(html).not.toContain("FORTYGUARD CACHED");
    expect(html).toContain('aria-label="Replay source"');
    expect(html).not.toMatch(/aria-label="[^"]*FortyGuard/i);
    expect(html).toMatch(/data-active="true"[^>]*data-segment="replay"/);
    expect(html).toMatch(/data-active="false"[^>]*data-segment="cached"/);
  });

  it("names first-paint tape Evidence source, not a vendor product", () => {
    const html = renderToStaticMarkup(
      createElement(SourceTape, { active: "UNAVAILABLE" }),
    );
    expect(html).toContain('aria-label="Evidence source"');
    expect(html).not.toMatch(/aria-label="[^"]*FortyGuard/i);
    expect(html).not.toMatch(/aria-label="[^"]*FORTYGUARD/);
  });
});
