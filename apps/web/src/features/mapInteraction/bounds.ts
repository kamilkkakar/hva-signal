export function featureCollectionBounds(
  collection: { features: Array<{ geometry: unknown }> },
): [[number, number], [number, number]] | null {
  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  const visit = (value: unknown): void => {
    if (!Array.isArray(value)) {
      return;
    }
    if (
      value.length >= 2 &&
      typeof value[0] === "number" &&
      typeof value[1] === "number"
    ) {
      minLng = Math.min(minLng, value[0]);
      maxLng = Math.max(maxLng, value[0]);
      minLat = Math.min(minLat, value[1]);
      maxLat = Math.max(maxLat, value[1]);
      return;
    }
    for (const item of value) {
      visit(item);
    }
  };
  for (const feature of collection.features) {
    visit((feature.geometry as { coordinates?: unknown } | null)?.coordinates);
  }
  if (!Number.isFinite(minLng) || !Number.isFinite(minLat)) {
    return null;
  }
  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}
