# CROSS_CITY_CANOPY

## Status

- CONTRACT STATUS: `MATERIALIZED` under `CROSS_CITY_CANOPY_CONTRACT_V1`
- Artifact root: `data/context/cross-city/canopy/`
- Coverage: 25/25 tracts for Phoenix, Las Vegas, Tucson, Los Angeles
- Phoenix OHR `TREE_PCT_N` is not used


- SOURCE SELECTED: `NLCD / USDA Forest Service Percent Tree Canopy Cover (Tree Canopy Cover, CONUS)`
- Why selected: it is nationally consistent across the conterminous U.S., covers Arizona, Nevada, and California, and is easier to defend across Phoenix, Las Vegas, Tucson, and Los Angeles than community-specific canopy products.

## Definition

- DEFINITION: percent of each `30 m` raster cell covered by tree canopy, derived from satellite imagery plus ancillary information.

## Vintage

- VINTAGE: use the `2021` NLCD Tree Canopy Cover layer as the cross-city baseline.
- Notes from source review: MRLC reports annual CONUS availability, but `2021` is the stable baseline selected for this validation package and matches common downstream tract aggregation references.

## Resolution

- RESOLUTION: `30 m` raster.

## Aggregation

- AGGREGATION to tracts: area-weighted zonal mean of pixel canopy percentages across tract polygons.
- Operational note: tract summaries should be produced from the raster directly rather than by silently reusing Phoenix-local canopy values or block-group-only community products.

## Coverage

- ALL FOUR CITIES: `yes`
- Basis: Phoenix, Las Vegas, Tucson, and Los Angeles are all in CONUS coverage for NLCD TCC.

## Phoenix Difference

- PHOENIX LOCAL CANOPY DIFFERENCE: Phoenix local canopy in this repo comes from the OHR shade-study semantics using `TREE_PCT_N` over plantable ground. That denominator is not the same as national total-land tree canopy from NLCD.

## Defensibility

- COMPARISON DEFENSIBLE: `yes`
- Caveat: defensible only when labeled as a separate national canopy contract. It is not numerically interchangeable with the Phoenix local canopy layer and must not be presented as the same metric.

## Silent Substitute Rule

- Never silent substitute: code constant `CROSS_CITY_CANOPY_CONTRACT_V1` lives in `apps/api/app/domain/multicity/cross_city_canopy.py`.
- Phoenix local canopy loader remains separate in `apps/api/app/services/vulnerability_preparedness/canopy.py`.

## Rejected Alternative

- EPA EnviroAtlas was not selected as the primary cross-city source because its higher-resolution canopy products are community-specific and commonly summarized at block-group scale, which makes it a weaker default for a single tract-level national contract across these four cities.

## Source Notes

- MRLC / NLCD Tree Canopy Cover: annual CONUS tree canopy cover at `30 m`, produced by USDA Forest Service.
- EPA EnviroAtlas: useful comparison source, but better treated as a separate community product rather than the default cross-city tract contract.
