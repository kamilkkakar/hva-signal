import { useEffect, useState } from "react";
import { createGeometryLoader } from "@/api/areaGeometry";
import { SignalBMapStage } from "@/features/analysisMap/SignalBMapStage";
import type { SignalBGeometryCollection } from "@/features/analysisMap/signalBTypes";
import {
  CACHED_B_WORDING,
  phoenixDemoCachedSelectedTime,
  presentPublicCachedB,
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
  const facts = presentPublicCachedB(selectedZoneId);
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
      data-rank="no"
    >
      <p className="chip" data-testid="signal-b-maturity">
        {CACHED_B_WORDING}
      </p>
      <dl className="signal-b-public-facts" data-testid="signal-b-public-facts">
        {facts.selectedLabel ? (
          <div>
            <dt>Selected zone</dt>
            <dd data-testid="signal-b-selected-zone">
              {facts.selectedZoneId}: {facts.selectedLabel}
            </dd>
          </div>
        ) : null}
        <div>
          <dt>Coverage</dt>
          <dd data-testid="signal-b-coverage">{facts.coverage}</dd>
        </div>
        {facts.zoneAverageLabel ? (
          <div>
            <dt>Zone average</dt>
            <dd data-testid="signal-b-zone-average">{facts.zoneAverageLabel}</dd>
          </div>
        ) : null}
        <div>
          <dt>Source</dt>
          <dd data-testid="signal-b-source">{facts.source}</dd>
        </div>
        <div>
          <dt>Range</dt>
          <dd data-testid="signal-b-range">{facts.rangeLabel}</dd>
        </div>
      </dl>
      <details className="signal-b-footnote" data-testid="signal-b-footnote">
        <summary>Not a historical order</summary>
        <p>{facts.footnote}</p>
      </details>
      <SignalBMapStage
        enabled
        showZoneTable={false}
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
