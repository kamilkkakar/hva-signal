import { describe, expect, it } from "vitest";
import {
  allIdentityPackages,
  assertAreaIdentityQa,
  crossCityDisplayName,
  phoenixLocalDisplayName,
  resolvePhoenixLocalIdentity,
  tractDisplayNameFromGeoid,
} from "./registry";

describe("AREA_IDENTITY_V1 registry", () => {
  it("packages every published area with a non-blank geographic primary label", () => {
    for (const pkg of allIdentityPackages()) {
      const errors = assertAreaIdentityQa(pkg);
      expect(errors, pkg.city_id).toEqual([]);
      expect(pkg.areas.length).toBe(25);
    }
  });

  it("uses Census Tract labels for Phoenix local instead of Analysis Area N", () => {
    expect(phoenixLocalDisplayName("04013107401")).toBe("Census Tract 1074.01");
    expect(phoenixLocalDisplayName("04013107401")).not.toMatch(/Analysis Area/i);
    const identity = resolvePhoenixLocalIdentity("04013107401");
    expect(identity?.secondary_label).toMatch(/Local analysis/);
    expect(identity?.secondary_label).toMatch(/Phoenix, AZ/);
    expect(identity?.method_detail).toMatch(/GEOID 04013107401/);
  });

  it("keeps Phoenix local and cross-city Phoenix identities distinct", () => {
    const local = resolvePhoenixLocalIdentity("04013107401");
    const cross = crossCityDisplayName("phoenix-az", "04013104501");
    expect(local?.geography_kind).toBe("local_analysis");
    expect(cross).toBe("Census Tract 1045.01");
    expect(local?.display_name).not.toBe(cross);
  });

  it("formats tract fallbacks from GEOID consistently", () => {
    expect(tractDisplayNameFromGeoid("06037267800")).toBe("Census Tract 2678.00");
    expect(tractDisplayNameFromGeoid("32003003003")).toBe("Census Tract 30.03");
  });

  it("does not invent neighborhood names", () => {
    for (const pkg of allIdentityPackages()) {
      for (const row of pkg.areas) {
        expect(row.display_name).toMatch(/^Census Tract /);
        expect(row.name_source).not.toMatch(/neighborhood|poi|web_search/i);
      }
    }
  });
});
