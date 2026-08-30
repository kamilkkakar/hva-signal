import {
  SIGNAL_A_HATCH_HIGH_ID,
  SIGNAL_A_HATCH_LOW_ID,
  SIGNAL_A_HATCH_MID_ID,
} from "./tokens";

export type HatchKind = "low" | "mid" | "high";

export type HatchImage = {
  id: string;
  width: number;
  height: number;
  data: Uint8Array;
};

const SIZE = 16;

function period(kind: HatchKind): number {
  if (kind === "low") {
    return 8;
  }
  if (kind === "mid") {
    return 5;
  }
  return 3;
}

function alpha(kind: HatchKind): number {
  if (kind === "low") {
    return 90;
  }
  if (kind === "mid") {
    return 120;
  }
  return 155;
}

export function hatchImageId(kind: HatchKind): string {
  if (kind === "low") {
    return SIGNAL_A_HATCH_LOW_ID;
  }
  if (kind === "mid") {
    return SIGNAL_A_HATCH_MID_ID;
  }
  return SIGNAL_A_HATCH_HIGH_ID;
}

/** Diagonal ink hatch. Node-safe (no canvas). Transparent cells stay empty. */
export function hatchImage(kind: HatchKind): HatchImage {
  const data = new Uint8Array(SIZE * SIZE * 4);
  const step = period(kind);
  const inkAlpha = alpha(kind);
  for (let y = 0; y < SIZE; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      const on = (x + y) % step === 0;
      if (!on) {
        continue;
      }
      const index = (y * SIZE + x) * 4;
      data[index] = 16;
      data[index + 1] = 20;
      data[index + 2] = 14;
      data[index + 3] = inkAlpha;
    }
  }
  return { id: hatchImageId(kind), width: SIZE, height: SIZE, data };
}

export function allHatchImages(): HatchImage[] {
  return [hatchImage("low"), hatchImage("mid"), hatchImage("high")];
}
