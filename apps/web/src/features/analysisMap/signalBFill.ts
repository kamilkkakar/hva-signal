import {
  SIGNAL_B_FILL_OPACITY,
  SIGNAL_B_LINE_WIDTH,
  SIGNAL_B_NEUTRAL_FILL,
  SIGNAL_B_NEUTRAL_LINE,
} from "./signalBPolicy";
import type { SignalBFillPaint, SignalBLinePaint } from "./signalBTypes";

/**
 * V1 fill is one shared ink. Color and opacity do not read °C, min, max,
 * or any rank field. Missing zones use outline only (opacity 0).
 */
export function signalBFillPaint(): SignalBFillPaint {
  return {
    "fill-color": SIGNAL_B_NEUTRAL_FILL,
    "fill-opacity": [
      "case",
      ["==", ["get", "has_valid_temperature"], true],
      SIGNAL_B_FILL_OPACITY,
      0,
    ],
  };
}

export function signalBLinePaint(): SignalBLinePaint {
  return {
    "line-color": SIGNAL_B_NEUTRAL_LINE,
    "line-width": SIGNAL_B_LINE_WIDTH,
  };
}

export function signalBValidZoneFill(): { color: string; opacity: number } {
  return {
    color: SIGNAL_B_NEUTRAL_FILL,
    opacity: SIGNAL_B_FILL_OPACITY,
  };
}
