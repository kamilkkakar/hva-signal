/** Public two-signal chrome stays off until a stitcher opts in. */

export type SignalFeatureFlags = {
  selectedTimeSnapshotInterface: boolean;
  liveDemoConfirmation: boolean;
};

function envFlag(name: string): boolean {
  const env = import.meta.env as Record<string, string | boolean | undefined>;
  const raw = env[name];
  return raw === true || raw === "1" || raw === "true";
}

export function defaultSignalFeatureFlags(): SignalFeatureFlags {
  return {
    selectedTimeSnapshotInterface: envFlag("VITE_HVA_SELECTED_TIME_SNAPSHOT"),
    liveDemoConfirmation: envFlag("VITE_HVA_LIVE_DEMO_CONFIRMATION"),
  };
}

export function isSelectedTimeSnapshotInterfaceEnabled(
  flags: Partial<SignalFeatureFlags> = {},
): boolean {
  return (
    flags.selectedTimeSnapshotInterface ??
    defaultSignalFeatureFlags().selectedTimeSnapshotInterface
  );
}

export function isLiveDemoConfirmationEnabled(
  flags: Partial<SignalFeatureFlags> = {},
): boolean {
  return (
    flags.liveDemoConfirmation ?? defaultSignalFeatureFlags().liveDemoConfirmation
  );
}

export function resolveSignalFeatureFlags(
  overrides: Partial<SignalFeatureFlags> = {},
): SignalFeatureFlags {
  const defaults = defaultSignalFeatureFlags();
  return {
    selectedTimeSnapshotInterface:
      overrides.selectedTimeSnapshotInterface ?? defaults.selectedTimeSnapshotInterface,
    liveDemoConfirmation:
      overrides.liveDemoConfirmation ?? defaults.liveDemoConfirmation,
  };
}
