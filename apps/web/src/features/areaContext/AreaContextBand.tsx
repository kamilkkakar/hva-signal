import { useEffect, useState } from "react";
import { AreaContextList } from "./AreaContextList";
import { AreaContextPanel } from "./AreaContextPanel";
import { MAP_MODE_LABEL } from "./copy";
import { fetchAreaContext } from "./fetchContext";
import { MAP_MODES } from "./mapModes";
import { allowedMapModes, presentList, presentSelectedArea } from "./present";
import type { AreaContextDocument, MapMode } from "./types";
import "./areaContext.css";

export type AreaContextBandProps = {
  areaId?: string;
  selectedZoneId?: string | null;
};

export function AreaContextBand({
  areaId = "phoenix-demo",
  selectedZoneId = null,
}: AreaContextBandProps) {
  const [document, setDocument] = useState<AreaContextDocument | null>(null);
  const [mode, setMode] = useState<MapMode>("THERMAL");

  useEffect(() => {
    let cancelled = false;
    void fetchAreaContext(areaId, selectedZoneId)
      .then((payload) => {
        if (!cancelled) {
          setDocument(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDocument(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [areaId, selectedZoneId]);

  if (!document) {
    return null;
  }

  const modes = allowedMapModes(document);
  const selected = document.selected
    ? presentSelectedArea(document.selected)
    : null;

  return (
    <section
      className="judge-area-context"
      data-testid="area-context-band"
      aria-label="Analysis area context"
    >
      <div className="area-context-modes" role="tablist" aria-label="Context map modes">
        {MAP_MODES.filter((item) => modes.includes(item)).map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={mode === item}
            data-mode={item}
            onClick={() => setMode(item)}
          >
            {MAP_MODE_LABEL[item]}
          </button>
        ))}
      </div>
      {selected ? <AreaContextPanel view={selected} /> : null}
      <AreaContextList rows={presentList(document)} mode={mode} />
    </section>
  );
}
