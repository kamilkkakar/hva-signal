import { useEffect, useState } from "react";
import { createGeometryLoader } from "@/api/areaGeometry";
import { SignalBMapStage } from "@/features/analysisMap/SignalBMapStage";
import type { SignalBGeometryCollection } from "@/features/analysisMap/signalBTypes";
import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { GEOID_DETAILS_SUMMARY } from "@/features/selectedAreaStory/copy";
import {
  CACHED_B_WORDING,
  phoenixDemoCachedSelectedTime,
  presentPublicCachedB,
} from "./cachedPhoenix";
import { PUBLIC_SIGNAL_B } from "./publicBGate";
import "./signalB.css";

type SignalBCachedPanelProps = {
  selectedZoneId?: string | null;
  showMap?: boolean;
};

export function SignalBCachedPanel({
  selectedZoneId = null,
  showMap = true,
}: SignalBCachedPanelProps) {
  const section = phoenixDemoCachedSelectedTime();
  const facts = presentPublicCachedB(selectedZoneId);
  const [geometry, setGeometry] = useState<SignalBGeometryCollection | null>(null);

  useEffect(() => {
    if (!showMap) {
      return;
    }
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
  }, [showMap]);

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
            <dt>Selected area</dt>
            <dd data-testid="signal-b-selected-zone">
              {analysisAreaLabel(facts.selectedZoneId) ?? "Selected analysis area"}: {facts.selectedLabel}
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
      {facts.selectedZoneId ? (
        <details data-testid="signal-b-selected-geoid">
          <summary>{GEOID_DETAILS_SUMMARY}</summary>
          <p>{facts.selectedZoneId}</p>
        </details>
      ) : null}
      <details className="signal-b-footnote" data-testid="signal-b-footnote">
        <summary>Not a historical order</summary>
        <p>{facts.footnote}</p>
      </details>
      {showMap ? (
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
      ) : null}
    </div>
  );
}
