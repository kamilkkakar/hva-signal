# Phoenix hourly Type-1 pilot

Status: **PREREGISTERED — execution evidence not yet present**

This pilot tests whether FortyGuard can supply the true hourly fields required
by the candidate persistent relative thermal-exceedance contract. It does not
close Gate 0, freeze the event, or create an operational outcome.

## Frozen scope

- Area: the exact 25-tract `phoenix-demo` geometry.
- Provider AOI: deterministic dissolved union of those tracts.
- Dates: July 15 in 2022, 2023, and 2024.
- Hours: every exact AOI-local hour from `00:00` through `23:00`.
- Requests: 72 unique FortyGuard Type-1 (`filter_type=1`) TCM fields at 100 m.
- Canary: `2024-07-15T03:00` America/Phoenix.
- Batch: the other 71 fields, executed sequentially only after canary PASS.
- Automatic retry: forbidden after an ambiguous vendor attempt.
- Window aggregates and interpolation: forbidden.

The machine-readable manifest is
`data/gate0/phoenix-v1/hourly_thermal_pilot_manifest.json`, SHA-256
`f3505b68dca4279cd9d50c941290c1daf1140707a74ea7686b129f5a8bdf1617`.
Its exact provider request geometry is
`data/gate0/phoenix-v1/hourly_pilot_provider_aoi.geojson`.

## Why this canary comes first

The tracked reference panel contains all 25 zone means for the exact
`2024-07-15 03:00` local instant. The canary therefore tests more than HTTP
success. It must reproduce:

- one single-hour request with the manifest fingerprint;
- a complete single-partition assembly;
- 3,749 mapped temperature tiles;
- the exact expected tile count for every tract;
- a temperature for every tile and every tract;
- a cache-only second fetch with the same fingerprint and values;
- an exactly metered debit when the first fetch is live; and
- the tracked same-instant zone means within a mean absolute difference of
  0.02 °C and a maximum per-zone difference of 0.05 °C.

Those temperature tolerances are acquisition-consistency guards, not heat-risk
or event thresholds. A failure indicates provider revision, request-time
ambiguity, geometry/aggregation drift, or another method mismatch that must be
explained before buying the remaining fields.

The canary cannot independently prove that a vendor-labelled hour is physically
the claimed hour. It establishes consistency with the previously retained
same-instant field. The completed 24-hour sequences must still be inspected for
duplicate fields, missing hours, and implausible or static diurnal behavior.

## Quality stop rules

The runner stops on the first failed slot. It does not continue when:

- the manifest or any source hash changes;
- a request is not a single exact Type-1 hour;
- the provider AOI partitions or the 25-zone geometry changes;
- the returned or assigned tile lattice differs from the 3,749-tile baseline;
- any tile or zone temperature is missing;
- the cache recheck is not an identical zero-submit reuse;
- a live request's debit cannot be measured; or
- the canary differs from the retained same-instant reference beyond its frozen
  acquisition-consistency tolerances.

An interrupted or failed request is marked ambiguous before submission. The
runner will not issue a blind retry unless the operator first reconciles the
activity or retained fingerprint cache.

## Execution

Use the API environment for all commands.

```bash
python scripts/build_phoenix_hourly_pilot_manifest.py --check
python scripts/acquire_phoenix_hourly_pilot.py preflight
```

Paid execution requires `FORTYGUARD_API_KEY` in the process environment or an
explicit local `--env-file`. The value is neither printed nor written.

```bash
python scripts/acquire_phoenix_hourly_pilot.py \
  canary \
  --confirm-manifest-sha f3505b68dca4279cd9d50c941290c1daf1140707a74ea7686b129f5a8bdf1617

python scripts/acquire_phoenix_hourly_pilot.py \
  batch \
  --confirm-manifest-sha f3505b68dca4279cd9d50c941290c1daf1140707a74ea7686b129f5a8bdf1617
```

Runtime state retains redacted upstream payloads, aligned tile fields,
normalized zone means, activity identifiers, per-request debit, and every
quality check. It is deliberately outside the tracked product and public API.

The pilot is request-count bounded, not credit capped. The historical Phoenix
envelope of roughly 4,220 credits per comparable field implies about 303,840
credits for 72 new misses, but that is an empirical planning estimate rather
than a vendor price contract. Each live request is measured separately.

## What pilot completion unlocks

A passing pilot supports a decision to acquire the full 31-day × 3-year ×
24-hour reference cube and to run the preregistered threshold/duration
sensitivity grid. It does not itself provide the 31 observations per year,
zone, and local hour required by the candidate detector.

It also does not provide an operational-outcome event. That requires a separate
timestamped, deidentified service-demand or health-outcome dataset, its own
geographic/time alignment contract, denominator and reporting-delay treatment,
baseline definition, leakage-safe train/validation split, calibration tests,
and explicit human approval of the allowed claim. Thermal fields alone cannot
stand in for those labels.

## UI and runtime boundary

This slice adds no public route, feature flag, UI component, probability,
forecast, ranking, intervention recommendation, or deployment change. The live
product remains unchanged.
