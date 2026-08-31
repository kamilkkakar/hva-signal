import {
  CANOPY_STOPS,
  HOUSING_STOPS,
  INCOME_STOPS,
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
  THERMAL_C_LOCAL_HIGH,
  THERMAL_C_LOCAL_LOW,
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

export type SignalBThermalFillInput = {
  observedMinC: number;
  observedMaxC: number;
  /** OFF by default. Only stretch when the analyst opts in. */
  enhanceLocalContrast?: boolean;
};

function fixedThermalFillPaint(): SignalAFillPaint["fill-color"] {
  return [
    "interpolate",
    ["linear"],
    ["get", "mean_temperature_c"],
    ...THERMAL_C_STOPS,
  ];
}

/** Selected-time absolute °C. Default = true fixed 25–45 scale. */
export function signalBThermalFillPaint(input?: SignalBThermalFillInput): SignalAFillPaint {
  const lo = input?.observedMinC;
  const hi = input?.observedMaxC;
  const enhance = input?.enhanceLocalContrast === true;
  const useLocalContrast =
    enhance &&
    lo != null &&
    hi != null &&
    Number.isFinite(lo) &&
    Number.isFinite(hi) &&
    hi > lo;

  return {
    "fill-color": useLocalContrast
      ? [
          "interpolate",
          ["linear"],
          ["get", "mean_temperature_c"],
          lo,
          THERMAL_C_LOCAL_LOW,
          hi,
          THERMAL_C_LOCAL_HIGH,
        ]
      : fixedThermalFillPaint(),
    "fill-opacity": [
      "case",
      ["==", ["get", "has_semantic_fill"], true],
      0.82,
      0,
    ] as unknown as number,
  };
}

export const CONTEXT_FILL_PROPERTY = "context_fill_value";

export type ContextPaletteId = "canopy" | "income" | "housing" | "default";

export function contextPaletteStops(palette: ContextPaletteId): readonly string[] {
  if (palette === "canopy") return CANOPY_STOPS;
  if (palette === "income") return INCOME_STOPS;
  if (palette === "housing") return HOUSING_STOPS;
  return SIGNAL_A_POS_STOPS;
}

export function contextQuantityFillPaint(
  min: number,
  max: number,
  palette: ContextPaletteId = "default",
): {
  "fill-color": unknown;
  "fill-opacity": unknown;
} {
  const lo = Math.min(min, max);
  const hi = Math.max(min, max);
  const top = hi === lo ? lo + 1 : hi;
  const stops = contextPaletteStops(palette);
  const low = stops[0] ?? SIGNAL_A_INSUFFICIENT_FILL;
  const high = stops[stops.length - 1] ?? low;
  const mid = stops[Math.floor(stops.length / 2)] ?? high;
  const midValue = lo + (top - lo) / 2;
  return {
    "fill-color": [
      "case",
      ["==", ["typeof", ["get", CONTEXT_FILL_PROPERTY]], "number"],
      [
        "interpolate",
        ["linear"],
        ["get", CONTEXT_FILL_PROPERTY],
        lo,
        low,
        midValue,
        mid,
        top,
        high,
      ],
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
