# Phoenix hourly thermal-event candidate

Status: **CANDIDATE — not frozen and not authorized for probability**

The proposed Gate 0 event is:

> A frozen Phoenix v1 census tract is in a candidate persistent relative
> thermal-exceedance state when its year-balanced, leave-one-timestamp-out
> historical quantile for hourly zone-mean TCM is at or above 0.97 against the
> same local hour from June 30 through July 30 across 2022–2024 for at least
> three consecutive observed hours.

The machine-readable contract is
`data/gate0/phoenix-v1/hourly_thermal_event_candidate.json`. It is SHA-locked,
loaded fail-closed, and intentionally leaves the Gate 0
`adverse_event_definition` decision `INCOMPLETE`.

## Why this is the current candidate

- Own-tract history preserves the architecture's `HISTORICAL` reference-frame
  default and avoids AOI min-max normalization.
- Same-local-hour comparison avoids treating the normal diurnal cycle as an
  anomaly.
- Year-balanced midrank ECDF preserves the existing Phoenix Signal A
  normalization family and prevents one reference year from dominating the
  condition.
- Three consecutive observed hours distinguishes persistence from a single
  hourly spike.
- The 97th percentile follows the v0.4 architecture's reference example, but
  remains a candidate until sensitivity results are reviewed.
- The existing June 30–July 30, 2022–2024 window preserves continuity with the
  frozen 03:00 Phoenix reference rather than silently changing Signal A.

This is a **retrospective thermal-state definition**. It is not a heat illness,
911-demand, cooling-center-demand, safety, intervention-effect, priority, or
forecast outcome.

## Fail-closed behavior

- Only consecutive single-hour instant observations are eligible.
- Window aggregates cannot be inserted into hourly slots.
- Missing hours are not interpolated and break a qualifying run.
- A qualifying run may be detected despite unrelated missing hours elsewhere
  in the evaluated interval.
- `NOT_DETECTED` requires every hour in the evaluated interval to have both an
  observation and a complete same-hour reference, and the interval must be at
  least as long as the persistence rule. Otherwise the result is
  `INSUFFICIENT_EVIDENCE`.
- The evaluator reports the run length and peak historical quantile. It does
  not report degree-hours, because integration semantics are not yet verified.
- No result contains or implies calibrated event probability.

## Evidence required before freezing

1. Use the SHA-locked `PHX_HOURLY_TYPE1_PILOT_V1` acquisition manifest for true
   single-hour fields while keeping the current 03:00 reference unchanged.
2. Run its bounded three-date pilot before wider acquisition. The pilot should
   exercise 24 consecutive local hours on matched dates in 2022, 2023, and
   2024 and retain aligned tile fields for the separate static-field test.
3. Measure source semantics, request deduplication, cache reuse, zone coverage,
   missingness, and exact credit debit under an explicitly approved cap.
4. Only if the pilot passes, build the full held `PHX_HOURLY_THERMAL_V1`
   reference cube. The three-date pilot alone cannot satisfy the contract's
   31-observation-per-year, per-zone, per-hour reference requirement.
5. Run the pre-registered sensitivity grid over threshold percentiles
   `{0.90, 0.95, 0.97}` and minimum durations `{2, 3, 4}`. Report event counts,
   tract coverage, run-length distribution, and instability under small policy
   changes; do not optimize against a desired event count.
6. Obtain product-owner approval of the exact sentence, threshold, duration,
   missing-data rule, and allowed claims.

Only after those steps may a later change mark the ledger decision `FROZEN`.
That later change still would not authorize a probability engine: calibration,
validation, the remaining Gate 0 decisions, and an explicit runtime-policy
change remain separate requirements.
