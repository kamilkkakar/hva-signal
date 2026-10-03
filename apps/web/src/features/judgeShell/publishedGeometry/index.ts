import collection from "./phoenix-demo.json";
import type { AreaGeometryPayload } from "@/api/areaGeometry";

// Exact frozen geometry paired with the bundled published Phoenix observation.
// Kept inside the web build so published viewing does not depend on API wake-up.
export function publishedPhoenixGeometry(areaId: string): AreaGeometryPayload | null {
  if (areaId !== "phoenix-demo") return null;
  return {
    areaId,
    zoneGeometryVersion: "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
    geometrySha256: "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    collection: collection as AreaGeometryPayload["collection"],
  };
}
