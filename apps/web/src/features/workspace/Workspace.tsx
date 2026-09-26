import { useEffect, useState } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { ExploreCity } from "./ExploreCity";
import { CompareCities } from "./CompareCities";
import { fetchCityCatalog } from "./cityCatalog";
import { CITIES, type WorkspaceMode, type CityConfig, type CityId } from "./types";
import "@/features/experience/experience.css";
import "./workspace.css";
import "./workspace-polish.css";

export function Workspace() {
  const [mode, setMode] = useState<WorkspaceMode>("explore");
  const [cityId, setCityId] = useState<CityId>("phoenix-az");
  const [cities, setCities] = useState<readonly CityConfig[]>(CITIES);

  useEffect(() => {
    let cancelled = false;
    void fetchCityCatalog().then((catalog) => {
      if (cancelled) return;
      const fallback = catalog[0];
      if (!fallback) return;
      setCities(catalog);
      setCityId((current) => catalog.some((city) => city.id === current) ? current : fallback.id);
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
        <ExploreCity cityId={cityId} cities={cities} onCityChange={setCityId} />
      ) : (
        <CompareCities />
      )}
    </div>
  );
}
