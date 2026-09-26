import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CapabilityEvidenceDisclosure } from "./CapabilityEvidenceDisclosure";
import type { CityConfig, ValidationJurisdiction } from "./types";

const city: CityConfig = {
  id: "phoenix-az",
  label: "Phoenix",
  state: "AZ",
  apiCityId: "phoenix",
  timezone: "America/Phoenix",
  hasLocalAnalysis: true,
  capabilities: { local_story: "AVAILABLE" },
  capabilityEvidence: {
    local_story: {
      state: "VERIFIED",
      reason: "Reviewed server artifacts exist.",
      affectedScope: "local_story",
      nextCheck: "Repeat integrity checks after a source change.",
    },
  },
};

const validation: ValidationJurisdiction = {
  jurisdictionId: "yuma_az",
  displayName: "Yuma",
  regionCode: "AZ",
  validationClass: "SMALL_PLACE",
  selectable: false,
  state: "NOT_YET_TESTED",
  reason: "Small-place evidence has not been validated.",
  affectedScope: ["place_geometry"],
  nextCheck: "Test native tracts without a minimum count.",
  capabilities: {},
};

describe("capability evidence disclosure", () => {
  it("labels evidence as non-ranking and validation places as non-selectable", () => {
    const html = renderToStaticMarkup(createElement(CapabilityEvidenceDisclosure, {
      city,
      validationJurisdictions: [validation],
    }));
    expect(html).toContain("not heat severity or city rank");
    expect(html).toContain("Reviewed server artifacts exist");
    expect(html).toContain("data-selectable=\"false\"");
    expect(html).toContain("validation only");
    expect(html).not.toContain("<option");
  });

  it("does not invent evidence when only the packaged fallback is available", () => {
    const html = renderToStaticMarkup(createElement(CapabilityEvidenceDisclosure, {
      city: { ...city, capabilityEvidence: undefined },
      validationJurisdictions: [],
    }));
    expect(html).toContain("Structured server evidence is unavailable");
  });

  it("distinguishes published thermal evidence from the live acquisition path", () => {
    const html = renderToStaticMarkup(createElement(CapabilityEvidenceDisclosure, {
      city: {
        ...city,
        capabilityEvidence: {
          selected_time_thermal: { ...city.capabilityEvidence!.local_story },
          type1_live: { ...city.capabilityEvidence!.local_story, state: "NOT_YET_TESTED" },
        },
      },
      validationJurisdictions: [],
    }));
    expect(html).toContain("Selected-time thermal evidence");
    expect(html).toContain("Live selected-time acquisition");
  });
});
