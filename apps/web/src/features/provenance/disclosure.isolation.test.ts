import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { P1_LANDING_SELECTED_TIME_REQUESTED } from "./sourceTapeBind";

const here = dirname(fileURLToPath(import.meta.url));

function read(rel: string): string {
  return readFileSync(join(here, rel), "utf8");
}

describe("disclosure isolation", () => {
  it("keeps public B off and never mounts the leftover SourceTape bind", () => {
    expect(P1_LANDING_SELECTED_TIME_REQUESTED).toBe(false);
    const owned = [
      read("HowDetermined.tsx"),
      read("determination.ts"),
      read("disclosureCopy.ts"),
      read("../judgeShell/ProvenanceBand.tsx"),
    ].join("\n");
    expect(owned).not.toContain("SourceTape");
    expect(owned).not.toContain("sourceBannerLabel");
    expect(owned).not.toContain("judgeShell/signalB/sourceTapeBind");
    expect(owned).not.toContain("selectedTimeRequested: true");
  });

  it("leaves signalB sourceTapeBind as residual, not enablement", () => {
    const leftover = read("../judgeShell/signalB/sourceTapeBind.tsx");
    expect(leftover).toContain("SourceTape");
    expect(leftover).toContain("a-only-tape");
    const band = read("../judgeShell/ProvenanceBand.tsx");
    expect(band).not.toContain("from \"./signalB\"");
    expect(band).not.toContain("from \"./signalB/sourceTapeBind\"");
    expect(band).toContain("CommandCenterProvenanceHeader");
    expect(band).toContain("HowDetermined");
  });
});
