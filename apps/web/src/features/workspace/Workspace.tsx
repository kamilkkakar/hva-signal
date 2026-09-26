import { useEffect, useState } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { ExploreCity } from "./ExploreCity";
import { CompareCities } from "./CompareCities";
import { fetchCityCatalog } from "./cityCatalog";
import {
  CITIES,
  type WorkspaceMode,
  type CityConfig,
  type CityId,
  type ValidationJurisdiction,
} from "./types";
import "@/features/experience/experience.css";
import "./workspace.css";
import "./workspace-polish.css";

export function Workspace() {
  const [mode, setMode] = useState<WorkspaceMode>("explore");
  const [cityId, setCityId] = useState<CityId>("phoenix-az");
  const [cities, setCities] = useState<readonly CityConfig[]>(CITIES);
  const [validationJurisdictions, setValidationJurisdictions] = useState<readonly ValidationJurisdiction[]>([]);

  useEffect(() => {
    let cancelled = false;
    void fetchCityCatalog().then((catalog) => {
      if (cancelled) return;
      const fallback = catalog.cities[0];
      if (!fallback) return;
      setCities(catalog.cities);
      setValidationJurisdictions(catalog.validationJurisdictions);
      setCityId((current) => catalog.cities.some((city) => city.id === current) ? current : fallback.id);
    }).catch(() => {
      // Keep the packaged fail-closed catalog when the server catalog is unavailable.
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div
      className="ws"
      data-testid="workspace"
      data-core-product-shell="present"
      data-mode={mode}
      data-city={cityId}
    >
      <WorkspaceHeader mode={mode} onModeChange={setMode} />
      {mode === "explore" ? (
        <ExploreCity
          cityId={cityId}
          cities={cities}
          validationJurisdictions={validationJurisdictions}
          onCityChange={setCityId}
        />
      ) : (
        <CompareCities />
      )}
    </div>
  );
}
