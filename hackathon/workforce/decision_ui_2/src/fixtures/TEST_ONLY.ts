/**
 * TEST_ONLY — do not import from production routes or publicSurface.
 * Fixture values exist for component development and automated tests.
 * They must never appear on the public decision surface.
 */
export const TEST_ONLY = "TEST_ONLY" as const;

export const TEST_ONLY_BANNER =
  "TEST_ONLY fixture. Not a published HVA-Signal reading.";
