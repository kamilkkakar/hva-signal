import { ANALYSIS_AREA_GEOIDS } from "@/features/selectedAreaStory/types";
import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { GEOID_SECONDARY, SELECTOR_LABEL } from "./copy";

type AreaSelectorProps = {
  selectedZoneId: string | null;
  onSelect: (geoid: string) => void;
};

export function AreaSelector({ selectedZoneId, onSelect }: AreaSelectorProps) {
  return (
    <label className="hx-selector" data-testid="area-selector">
      <span>{SELECTOR_LABEL}</span>
      <select
        aria-label={SELECTOR_LABEL}
        data-testid="area-selector-input"
        value={selectedZoneId ?? ""}
        onChange={(event) => onSelect(event.target.value)}
      >
        {ANALYSIS_AREA_GEOIDS.map((geoid) => (
          <option key={geoid} value={geoid}>
            {analysisAreaLabel(geoid)} · {GEOID_SECONDARY} {geoid}
          </option>
        ))}
      </select>
    </label>
  );
}
