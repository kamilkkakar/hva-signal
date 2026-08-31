# CROSS_CITY_THERMAL_PROFILE_V1 (roadmap)

## Status

**Future capability only.** Not acquired. Not plotted. Not claimed in the
current Cross-City Explorer release.

## Intent

A future comparable multi-city **selected-time thermal profile** surface that
would show how Type-1 TCM varies across a small set of civil-local observation
instants for the same frozen `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` areas.

## Non-goals for this release

- Do **not** fabricate temporal plots from a single observation.
- Do **not** acquire additional FortyGuard times under this release program.
- Do **not** imply that the current single-clock bubble view is a diurnal or
  seasonal profile.

## Current published observation

- Contract: `CROSS_CITY_OBSERVATION_V1`
- Local civil clock: `2024-07-08` at `15:00` in each city timezone
- Metric: FortyGuard Type-1 TCM
- Cities published: Phoenix, Las Vegas, Tucson, Los Angeles

## Future gates (before any acquisition)

1. Explicit human authorization for additional paid vendor calls
2. Debit circuit + single-partition preflight per city / time
3. Stable display policy for multi-instant encoding (separate from this doc)
4. No public live vendor / hosted end-user triggering
