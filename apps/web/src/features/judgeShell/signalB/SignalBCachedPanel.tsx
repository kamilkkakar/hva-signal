import { useEffect, useState } from "react";
import { createGeometryLoader } from "@/api/areaGeometry";
import { SignalBMapStage } from "@/features/analysisMap/SignalBMapStage";
import type { SignalBGeometryCollection } from "@/features/analysisMap/signalBTypes";
import { SignalBSection } from "@/features/signals/SignalBSection";
import "@/features/signals/signals.css";
import { presentSelectedTime } from "@/features/signals/presentation";
import {
  CACHED_B_WORDING,
  phoenixDemoCachedSelectedTime,
  selectedZoneTemperatureC,
} from "./cachedPhoenix";
import { PUBLIC_SIGNAL_B } from "./publicBGate";
import "./signalB.css";

type SignalBCachedPanelProps = {
  selectedZoneId?: string | null;
};

export function SignalBCachedPanel({
  selectedZoneId = null,
}: SignalBCachedPanelProps) {
  const section = phoenixDemoCachedSelectedTime();
  const view = presentSelectedTime(section, { liveDemoConfirmation: false });
  const selectedC = selectedZoneTemperatureC(selectedZoneId);
  const [geometry, setGeometry] = useState<SignalBGeometryCollection | null>(null);

  useEffect(() => {
    const loader = createGeometryLoader();
    let cancelled = false;
    void loader
      .load("phoenix-demo")
      .then((outcome) => {
        if (cancelled || outcome.stale) {
          return;
        }
        setGeometry(outcome.payload.collection);
      })
      .catch(() => {
        if (!cancelled) {
          setGeometry(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div
      className="signal-b-cached-panel"
      data-testid="signal-b-cached-panel"
      data-public-signal-b={PUBLIC_SIGNAL_B ? "cached" : "disabled"}
      data-capability="available-now-cached-evidence"
      data-coverage="25/25"
      data-source="fortyguard_cached"
    >
      <p className="chip" data-testid="signal-b-maturity">
        {CACHED_B_WORDING}
      </p>
      <SignalBSection view={view} />
      {selectedC != null ? (
        <p className="job-id" data-testid="signal-b-selected-zone">
          Selected zone {selectedZoneId}: {selectedC.toFixed(1)} °C
        </p>
      ) : null}
      <SignalBMapStage
        enabled
        snapshot={{
          units: "celsius",
          aggregation_method: "centroid_within_mean",
          spatial_resolution: "zone",
          user_facing_tile_map: false,
          target_timestamp: section.target_timestamp ?? undefined,
          timezone: section.timezone ?? undefined,
          zones: section.zones,
          expected_zone_count: section.expected_zone_count,
          valid_zone_count: section.valid_zone_count,
          missing_zone_ids: section.missing_zone_ids,
          temperature_min_c: section.temperature_min_c,
          temperature_max_c: section.temperature_max_c,
        }}
        geometry={geometry}
        availability="ready"
      />
    </div>
  );
}
