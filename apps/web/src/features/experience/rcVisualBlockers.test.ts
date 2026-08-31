import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SectionNav } from "@/features/experience/SectionNav";
import { ThermalHero } from "@/features/experience/ThermalHero";
import { ThermalSnapshotLegend } from "@/features/mapEncoding/ThermalSnapshotLegend";
import {
  ACTIVE_THERMAL_DISPLAY_SCALE,
  THERMAL_DISPLAY_SCALE_V1,
} from "@/features/mapEncoding/thermalDisplayScale";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("RC visual blockers", () => {
  it("has no external basemap tile provider that can watermark API KEY REQUIRED", () => {
    const stagePath = resolve(
      process.cwd(),
      "src/features/mapInteraction/MapInteractionStage.tsx",
    );
    const source = readFileSync(stagePath, "utf8");
    expect(source).not.toMatch(/basemaps\.carto|API KEY REQUIRED|maptiler\.com|tile\.openstreetmap\.org/i);
    expect(source).toMatch(/No external basemap|neutral paper/i);
  });

  it("keeps THERMAL_DISPLAY_SCALE_V1 as the active fixed scale", () => {
    expect(ACTIVE_THERMAL_DISPLAY_SCALE).toBe(THERMAL_DISPLAY_SCALE_V1);
    expect(THERMAL_DISPLAY_SCALE_V1.currentAoiStretch).toBe(false);
    expect(THERMAL_DISPLAY_SCALE_V1.localContrastDefault).toBe(false);
    expect(THERMAL_DISPLAY_SCALE_V1.domainMin).toBe(15);
    expect(THERMAL_DISPLAY_SCALE_V1.domainMax).toBe(60);
  });

  it("renders separated thermal legend ticks with °C and observed range", () => {
    const html = renderToStaticMarkup(
      createElement(ThermalSnapshotLegend, {
        observedMinC: 33.5,
        observedMaxC: 33.7,
        enhanceLocalContrast: false,
      }),
    );
    expect(html).toContain('data-testid="thermal-legend-ticks"');
    expect(html).toContain("≤15");
    expect(html).toContain("≥60");
    expect(html).toContain("°C");
    expect(html).toContain("Observed range");
    expect(html).toContain("Low spatial variation");
    expect(html).toContain('data-local-contrast="no"');
    expect(html).toContain('data-scale-version="THERMAL_DISPLAY_SCALE_V1"');
    const ticksJoined = (html.match(/hva-thermal-tick-value">([^<]+)/g) ?? [])
      .map((chunk) => chunk.replace(/.*">/, ""))
      .join("");
    expect(ticksJoined).not.toBe("152535455560");
    expect(ticksJoined).not.toMatch(/^2530354045$/);
  });

  it("does not stack full section list beside compact mobile nav by default", () => {
    const html = renderToStaticMarkup(createElement(SectionNav));
    expect(html).toContain('data-testid="section-nav-compact"');
    expect(html).toContain('data-testid="section-nav-all"');
    expect(html).toContain("All sections");
    expect(html).not.toMatch(/<details[^>]*open[^>]*data-testid="section-nav-all"/i);
  });

  it("hides Previous at 01/05 and Next at 05/05 in compact nav markup", () => {
    const html = renderToStaticMarkup(createElement(SectionNav));
    expect(html).toMatch(/data-testid="section-nav-prev"[^>]*\bdisabled\b/);
    expect(html).toMatch(/data-testid="section-nav-prev"[^>]*\bhidden=""/);
    expect(html).toMatch(
      /data-testid="section-nav-next"(?![^>]*\bdisabled\b)[^>]*>Next<\/button>/,
    );
    expect(html).not.toMatch(/data-testid="section-nav-next"[^>]*\bhidden=""/);
  });

  it("compresses historical unavailable behind Why unavailable?", () => {
    const html = renderToStaticMarkup(
      createElement(ThermalHero, {
        selectedZoneId: "04013107401",
        onSelect: () => undefined,
        temperatureC: 33.7,
        observationStamp: "15 Jul 2025 · 03:00",
        history: {
          status: "unavailable",
          sentence: "Not available for this observation.",
          reason: "A comparable own-area 03:00 historical position is not published for this case.",
          percent: null,
        },
        spatial: {
          status: "withheld",
          sentence: "Thermal differences across the analysis areas are too small.",
        },
        change2024vs2022: 1.54,
      }),
    );
    expect(html).toContain("Not available for this observation.");
    expect(html).toContain("Why unavailable?");
    expect(html).not.toMatch(/>Why\?</);
    expect(html).not.toMatch(/no row/i);
    expect(html).not.toMatch(/fill_kind|Decision 8|q_A|job clock|payload/i);
    expect(html).toContain('data-testid="hero-history"');
  });
});
