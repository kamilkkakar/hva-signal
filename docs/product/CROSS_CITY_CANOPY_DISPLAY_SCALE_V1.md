# CROSS_CITY_CANOPY_DISPLAY_SCALE_V1

## Purpose

Fixed **display** envelope for cross-city tree-canopy fill intensity in the
Cross-City Explorer. City identity remains the hue family; canopy only
controls lightness within that family.

## Contract

| Field | Value |
|-------|-------|
| Version | `CROSS_CITY_CANOPY_DISPLAY_SCALE_V1` |
| Unit | `%` (NLCD TCC tract mean) |
| Domain | `0` – `25` |
| Overflow | end-cap (≤0 / ≥25) |
| Visible-city stretch | **forbidden** |
| Per-city min/max | **forbidden** |
| Percentile stretch | **forbidden** |

## Why not 0–100

NLCD Percent Tree Canopy Cover is defined on 0–100% of each 30 m cell.
Packaged arid / western-urban tract means for the current comparison set sit
roughly in `0.01–11.6%`. Mapping that band onto a full 0–100 display would
collapse every city into a near-identical pale shade and erase within-city
structure.

## Why not derive from displayed cities

Deriving the domain from the currently visible city set would silently recolor
bubbles when the judge toggles cities. The display scale is therefore a stable
product policy, independent of which cities are plotted.

## Evidence for endcaps

From `CROSS_CITY_CANOPY_CONTRACT_V1` packaged ranges:

- Phoenix ≈ 0.30–4.45%
- Las Vegas ≈ 0.10–3.72%
- Tucson ≈ 0.01–0.67%
- Los Angeles ≈ 0.91–11.61%

`25%` leaves headroom above the current LA max toward denser urban tracts
without claiming 100% is the visual top of this surface.

## Implementation

- Web: `apps/web/src/features/crossCity/canopyDisplayScale.ts`
- Fill encoding: `citySpectrumFill(..., { metric: "treeCanopyPct" })`
