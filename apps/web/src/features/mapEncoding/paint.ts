import {
  SIGNAL_A_FILL_OPACITY,
  SIGNAL_A_HALO,
  SIGNAL_A_HALO_WIDTH,
  SIGNAL_A_HATCH_HIGH_ID,
  SIGNAL_A_HATCH_LOW_ID,
  SIGNAL_A_HATCH_MID_ID,
  SIGNAL_A_HATCH_OPACITY,
  SIGNAL_A_INSUFFICIENT_FILL,
  SIGNAL_A_INSUFFICIENT_LINE,
  SIGNAL_A_INSUFFICIENT_LINE_WIDTH,
  SIGNAL_A_LINE,
  SIGNAL_A_LINE_WIDTH,
  SIGNAL_A_POS_STOPS,
  THERMAL_C_STOPS,
} from "./tokens";

export type SignalAFillPaint = {
  "fill-color": unknown;
  "fill-opacity": number;
};

export type SignalAHatchPaint = {
  "fill-pattern": unknown;
  "fill-opacity": number;
};

export type SignalALinePaint = {
  "line-color": string;
  "line-width": number;
  "line-opacity": number;
};

export function signalAColorStops(maxOrder: number): Array<number | string> {
  const span = Math.max(1, maxOrder);
  const stops: Array<number | string> = [];
  const last = SIGNAL_A_POS_STOPS.length - 1;
  for (let index = 0; index < SIGNAL_A_POS_STOPS.length; index += 1) {
    const t = last === 0 ? 0 : index / last;
    const order = 1 + t * (span - 1);
    const color = SIGNAL_A_POS_STOPS[index];
    if (color == null) {
      continue;
    }
    stops.push(Number(order.toFixed(4)), color);
  }
  return stops;
}

export function signalAFillPaint(input: {
  authorized: boolean;
  maxOrder: number;
}): SignalAFillPaint {
  if (!input.authorized) {
    return {
      "fill-color": SIGNAL_A_INSUFFICIENT_FILL,
      "fill-opacity": 0,
    };
  }
  return {
    "fill-color": [
      "interpolate",
      ["linear"],
      ["get", "backend_order"],
      ...signalAColorStops(input.maxOrder),
    ],
    "fill-opacity": SIGNAL_A_FILL_OPACITY,
  };
}

export function signalAHatchSteps(maxOrder: number): unknown[] {
  const span = Math.max(1, maxOrder);
  const midStart = Math.max(2, Math.ceil(span / 3) + 1);
  const highStart = Math.max(midStart + 1, Math.ceil((2 * span) / 3) + 1);
  return [
    "step",
    ["get", "backend_order"],
    SIGNAL_A_HATCH_LOW_ID,
    midStart,
    SIGNAL_A_HATCH_MID_ID,
    highStart,
    SIGNAL_A_HATCH_HIGH_ID,
  ];
}

export function signalAHatchPaint(input: {
  authorized: boolean;
  maxOrder: number;
}): SignalAHatchPaint {
  if (!input.authorized) {
    return {
      "fill-pattern": SIGNAL_A_HATCH_LOW_ID,
      "fill-opacity": 0,
    };
  }
  return {
    "fill-pattern": signalAHatchSteps(input.maxOrder),
    "fill-opacity": SIGNAL_A_HATCH_OPACITY,
  };
}

export function signalALinePaint(authorized: boolean): SignalALinePaint {
  if (!authorized) {
    return {
      "line-color": SIGNAL_A_INSUFFICIENT_LINE,
      "line-width": SIGNAL_A_INSUFFICIENT_LINE_WIDTH,
      "line-opacity": 1,
    };
  }
  return {
    "line-color": SIGNAL_A_LINE,
    "line-width": SIGNAL_A_LINE_WIDTH,
    "line-opacity": 1,
  };
}

export function signalAHaloPaint(authorized: boolean): SignalALinePaint {
  return {
    "line-color": SIGNAL_A_HALO,
    "line-width": SIGNAL_A_HALO_WIDTH,
    "line-opacity": authorized ? 1 : 0,
  };
}

/** Selected-time absolute °C on a fixed semantic scale. Missing zones stay outline-only. */
export function signalBThermalFillPaint(): SignalAFillPaint {
  return {
    "fill-color": [
      "interpolate",
      ["linear"],
      ["get", "mean_temperature_c"],
      ...THERMAL_C_STOPS,
    ],
    "fill-opacity": [
      "case",
      ["==", ["get", "has_semantic_fill"], true],
      0.78,
      0,
    ] as unknown as number,
  };
}

export const CONTEXT_FILL_PROPERTY = "context_fill_value";

export function contextQuantityFillPaint(min: number, max: number): {
  "fill-color": unknown;
  "fill-opacity": unknown;
} {
  const lo = Math.min(min, max);
  const hi = Math.max(min, max);
  const top = hi === lo ? lo + 1 : hi;
  const low = SIGNAL_A_POS_STOPS[0] ?? SIGNAL_A_INSUFFICIENT_FILL;
  const high = SIGNAL_A_POS_STOPS[SIGNAL_A_POS_STOPS.length - 1] ?? low;
  return {
    "fill-color": [
      "case",
      ["==", ["typeof", ["get", CONTEXT_FILL_PROPERTY]], "number"],
      ["interpolate", ["linear"], ["get", CONTEXT_FILL_PROPERTY], lo, low, top, high],
      SIGNAL_A_INSUFFICIENT_FILL,
    ],
    "fill-opacity": [
      "case",
      ["==", ["typeof", ["get", CONTEXT_FILL_PROPERTY]], "number"],
      SIGNAL_A_FILL_OPACITY,
      0,
    ],
  };
}
