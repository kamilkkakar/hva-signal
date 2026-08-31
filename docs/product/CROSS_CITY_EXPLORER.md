# Cross-City Explorer

## Purpose

Cross-City Explorer extends the judge experience with a compact comparison
view across curated cities while preserving Phoenix as the published local
analysis baseline.

## Public question

How do thermal conditions vary across comparison areas with different levels
of tree canopy?

Patterns are descriptive and do not establish causal relationships.

## Default encodings

| Channel | Encoding |
|---------|----------|
| X | Tree canopy (%) |
| Y | Selected-time temperature (°C) |
| Size | Population |
| City | Hue family (OKLCH) |
| Fill intensity | Tree canopy on `CROSS_CITY_CANOPY_DISPLAY_SCALE_V1` |

Income remains available as an axis / fill option. Older housing (% units
built before 1980) is also available. Population density is not published on
this surface (no clean people/km² provenance wired for release).

## Interaction

- City selector sets focus city.
- Legend supports toggle, Only-isolate, and Show all.
- Exactly one isolated city uses a **Focused city scale** for axes (with
  optional **Use comparison scale**).
- Show all restores the common cross-city axis scale.
- Fill metric changes shade intensity only — never a universal palette.
- Hover / focus tooltip: Comparison Area N; City, State; Temp; Canopy; Pop;
  Income; Open area analysis → (Phoenix only).

## Guardrails

- No live place search
- No causal claims
- No intervention ranking
- No Phoenix screenshot replacement
- No Yuma / Palm Springs until ALG1 geography clears
- Graceful empty or error state when the comparison API is unavailable
