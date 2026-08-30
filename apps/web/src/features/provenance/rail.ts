import type { SignalKind } from "./types";

export function decision8PanelPermitted(signalKind: SignalKind): boolean {
  return signalKind === "historical_normalized";
}

export function referenceLinePermitted(signalKind: SignalKind): boolean {
  return signalKind === "historical_normalized";
}

export function qaHoverPermitted(signalKind: SignalKind): boolean {
  return signalKind === "historical_normalized";
}

export function legacyThermalSource(input: {
  selectedTimeRequested: boolean;
  historicalSource?: string | null;
}): string | null {
  if (input.selectedTimeRequested) {
    return null;
  }
  return input.historicalSource ?? null;
}
