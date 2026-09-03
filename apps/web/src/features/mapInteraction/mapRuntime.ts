export type MapRuntimeResult<T> =
  | { state: "ready"; map: T }
  | { state: "unavailable"; map: null };

/** Fail closed when a browser cannot construct the map renderer. */
export function startMapRuntime<T>(create: () => T): MapRuntimeResult<T> {
  try {
    return { state: "ready", map: create() };
  } catch {
    return { state: "unavailable", map: null };
  }
}
