import { useState } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { ExploreCity } from "./ExploreCity";
import { CompareCities } from "./CompareCities";
import type { WorkspaceMode, CityId } from "./types";
import "./workspace.css";

export function Workspace() {
  const [mode, setMode] = useState<WorkspaceMode>("explore");
  const [cityId, setCityId] = useState<CityId>("phoenix-az");

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
        <ExploreCity cityId={cityId} onCityChange={setCityId} />
      ) : (
        <CompareCities />
      )}
    </div>
  );
}
