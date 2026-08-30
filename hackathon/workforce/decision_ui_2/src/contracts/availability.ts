/** Shared availability states. Temporal fields stay pending until a real contract binds. */

export const AVAILABILITY = {
  PENDING_TEMPORAL_PROGRAM: "pending_temporal_program",
  UNAVAILABLE: "unavailable",
  READY: "ready",
} as const;

export type AvailabilityStatus = (typeof AVAILABILITY)[keyof typeof AVAILABILITY];

export type PendingTemporal<T> = {
  readonly availability: typeof AVAILABILITY.PENDING_TEMPORAL_PROGRAM;
  readonly value: null;
  readonly bind: string;
  readonly _phantom?: T;
};

export type Unavailable<T> = {
  readonly availability: typeof AVAILABILITY.UNAVAILABLE;
  readonly value: null;
  readonly reason: string;
  readonly _phantom?: T;
};

export type Ready<T> = {
  readonly availability: typeof AVAILABILITY.READY;
  readonly value: T;
};

export type BoundField<T> = PendingTemporal<T> | Unavailable<T> | Ready<T>;

export function pendingTemporal<T>(bind: string): PendingTemporal<T> {
  return {
    availability: AVAILABILITY.PENDING_TEMPORAL_PROGRAM,
    value: null,
    bind,
  };
}

export function isReady<T>(field: BoundField<T>): field is Ready<T> {
  return field.availability === AVAILABILITY.READY && field.value !== null;
}

export function isPending(
  field: BoundField<unknown>,
): field is PendingTemporal<unknown> {
  return field.availability === AVAILABILITY.PENDING_TEMPORAL_PROGRAM;
}

export function fieldNote(field: BoundField<unknown>): string {
  if (field.availability === AVAILABILITY.PENDING_TEMPORAL_PROGRAM) {
    return field.bind;
  }
  if (field.availability === AVAILABILITY.UNAVAILABLE) {
    return field.reason;
  }
  return "";
}
