import { describe, expect, it } from "vitest";
import { defaultSignalFeatureFlags } from "./flags";
import { fixturePair } from "./fixtures";
import {
  notPreparedLooksLikeLowRisk,
  presentTwoSignals,
  selectedTimeShowsLiveChrome,
  selectedTimeUx,
  sortSnapshotZones,
} from "./presentation";

const ENABLED = {
  selectedTimeSnapshotInterface: true,
  liveDemoConfirmation: false,
} as const;

describe("default feature flags", () => {
  it("mounts the selected-time interface and keeps live-demo confirmation off", () => {
    const flags = defaultSignalFeatureFlags();
    expect(flags.selectedTimeSnapshotInterface).toBe(true);
    expect(flags.liveDemoConfirmation).toBe(false);
  });
});

describe("two-signal presentation", () => {
  it("maps A NOT_PREPARED without a low-risk reading", () => {
    const pair = fixturePair("a_not_prepared_b_cached");
    const view = presentTwoSignals({ ...pair, flags: ENABLED });
    expect(view.mounted).toBe(true);
    expect(view.historical.ux).toBe("historical_not_prepared");
    expect(view.historical.stamp).toBe("REFERENCE NOT PREPARED");
    expect(view.historical.tone).toBe("not-prepared");
    expect(notPreparedLooksLikeLowRisk(view.historical)).toBe(false);
  });

  it("keeps A and B independent and never emits a combined score", () => {
    const pair = fixturePair("a_not_prepared_b_ready");
    const view = presentTwoSignals({ ...pair, flags: ENABLED });
    expect(view.combined_score_authorized).toBe(false);
    expect(view.combined_score).toBeNull();
    expect(view.signal_a_blocks_signal_b).toBe(false);
    expect(view.overall_job_complete).toBe(false);
    expect(view.historical.availability).toBe("NOT_PREPARED");
    expect(view.selected_time.ux).toBe("b_ready");
    expect(view.independence_copy.toLowerCase()).toContain(
      "combined score is not authorized",
    );
  });

  it("does not let A insufficient suppress B", () => {
    const pair = fixturePair("a_insufficient_b_ready");
    const view = presentTwoSignals({ ...pair, flags: ENABLED });
    expect(view.historical.ux).toBe("historical_insufficient");
    expect(view.selected_time.ux).toBe("b_ready");
    expect(view.signal_a_blocks_signal_b).toBe(false);
  });

  it("maps cached / unavailable / fetching / partial / ready as sibling B states", () => {
    expect(
      presentTwoSignals({ ...fixturePair("a_not_prepared_b_cached"), flags: ENABLED })
        .selected_time.ux,
    ).toBe("b_cached");
    expect(
      presentTwoSignals({
        ...fixturePair("a_not_prepared_b_unavailable"),
        flags: ENABLED,
      }).selected_time.ux,
    ).toBe("b_unavailable");
    expect(
      presentTwoSignals({
        ...fixturePair("a_not_prepared_b_fetching"),
        flags: ENABLED,
      }).selected_time.ux,
    ).toBe("b_fetching");
    expect(
      presentTwoSignals({
        ...fixturePair("a_not_prepared_b_partial"),
        flags: ENABLED,
      }).selected_time.ux,
    ).toBe("b_partial");
    expect(
      presentTwoSignals({ ...fixturePair("a_not_prepared_b_ready"), flags: ENABLED })
        .selected_time.ux,
    ).toBe("b_ready");
  });

  it("hides live-demo confirmation unless the future flag is on", () => {
    const pair = fixturePair("a_not_prepared_live_demo");
    const hidden = presentTwoSignals({ ...pair, flags: ENABLED });
    expect(hidden.selected_time.ux).toBe("b_unavailable");
    expect(hidden.selected_time.show_live_demo).toBe(false);
    expect(selectedTimeUx(pair.selectedTime, { liveDemoConfirmation: false })).toBe(
      "b_unavailable",
    );
    const shown = presentTwoSignals({
      ...pair,
      flags: { selectedTimeSnapshotInterface: true, liveDemoConfirmation: true },
    });
    expect(shown.selected_time.ux).toBe("live_demo_confirmation");
    expect(shown.selected_time.show_live_demo).toBe(true);
  });

  it("never labels cached B as live and never shows live tape", () => {
    const cached = presentTwoSignals({
      ...fixturePair("a_not_prepared_b_cached"),
      flags: ENABLED,
    });
    expect(cached.selected_time.source).toBe("REPLAY");
    expect(cached.selected_time.live_tape).toBe(false);
    expect(selectedTimeShowsLiveChrome(cached.selected_time)).toBe(false);
    const ready = presentTwoSignals({
      ...fixturePair("a_not_prepared_b_ready"),
      flags: ENABLED,
    });
    expect(ready.selected_time.source).toBe("CACHED");
    expect(selectedTimeShowsLiveChrome(ready.selected_time)).toBe(false);
  });

  it("sorts B zones by id and leaves missing values unknown", () => {
    const pair = fixturePair("a_not_prepared_b_partial");
    const view = presentTwoSignals({ ...pair, flags: ENABLED });
    const ids = view.selected_time.zones.map((zone) => zone.zone_id);
    expect(ids).toEqual([...ids].sort((left, right) => left.localeCompare(right)));
    expect(view.selected_time.zones.some((zone) => zone.mean_temperature_c == null)).toBe(
      true,
    );
    expect(sortSnapshotZones(pair.selectedTime.zones)[0]?.zone_id).toBe(
      "FIX-1714000-01",
    );
  });

  it("stays unmounted when the selected-time interface flag is off", () => {
    const view = presentTwoSignals({
      ...fixturePair("a_not_prepared_b_cached"),
      flags: { selectedTimeSnapshotInterface: false, liveDemoConfirmation: false },
    });
    expect(view.mounted).toBe(false);
  });

  it("forbids reference fields on B", () => {
    const pair = fixturePair("a_not_prepared_b_cached");
    expect(pair.selectedTime.reference_version).toBeNull();
    expect(pair.selectedTime.reference_source).toBeNull();
  });
});
