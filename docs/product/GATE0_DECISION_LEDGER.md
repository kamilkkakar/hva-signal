# Phoenix Gate 0 decision ledger

Phoenix v1 has a frozen `AreaConfig`, but the system-wide analytical Gate 0 is
still **OPEN**. These are deliberately separate states:

- `AreaConfig.gate0_status="frozen"` means the Decision 9 configuration bytes
  are human-frozen and hash-checked.
- `data/gate0/phoenix-v1/ledger.json` governs whether analytical capabilities
  are authorized.

The API verifies the ledger schema, exact decision and capability sets,
repository evidence paths, disabled module flags, and SHA-256 before a Phoenix
analysis runs. A mismatch fails the job closed. The ledger is also recorded in
the Evidence DAG so a blocked probability result points to the decision state
that blocked it.

## Current state

| Item | State | Meaning |
|---|---|---|
| Overall Gate 0 | `OPEN` | The full analytical system is not authorized. |
| Descriptive thermal ordering | `CONDITIONAL` | Allowed only with a full historical reference and sufficient Decision 8 spread. |
| Vulnerability/preparedness context | `AUTHORIZED` | Inventory context may be shown with source, vintage, coverage, and missingness. |
| Calibrated event probability | `BLOCKED` | No `P(event)` may be emitted. |
| Consequence, protection, priority, least-regret | `BLOCKED` | These engines do not have frozen evidence and policies. |
| Intervention evidence, human thermal burden, overnight recovery | `DISABLED` | Phoenix v1 module flags remain false. |

Three required decisions remain incomplete:

| Decision | Missing evidence |
|---|---|
| Adverse-event definition | The tracked persistent-relative-exceedance candidate still needs hourly evidence, sensitivity analysis, and human approval before its threshold and duration can be frozen. |
| Between-AOI variance test | A same-date, same-local-time, same-granularity replay bundle for at least three separated Phoenix AOIs. |
| Temporal/static-field test | Tracked protocol inputs and a reproducible, ratified result. |

The expected tile-coverage distribution is now `VERIFIED`. The deterministic
evidence package at
`data/gate0/phoenix-v1/expected_tile_coverage.json` rebuilds from 93 complete
historical 03:00 fields plus the tracked 15:00 and 21:00 snapshots. Across all
95 fields (2,375 zone observations), each zone has an invariant contributing-
tile count and every field contains 3,749 mapped tiles.

This verifies an empirical 100 m baseline for the frozen Phoenix geography. It
does **not** authorize a minimum coverage ratio, change the existing zero-tile
fail-closed behavior, or permit probability or priority ranking. Run
`python scripts/build_gate0_expected_tile_coverage.py --check` to verify that
the tracked artifact still reproduces byte-for-byte.

The adverse-event candidate is now explicit at
`data/gate0/phoenix-v1/hourly_thermal_event_candidate.json`: a frozen Phoenix
tract with a year-balanced, leave-one-timestamp-out same-local-hour historical
quantile at or above 0.97 for three consecutive observed hours. It is a retrospective thermal
state, not an operational-demand outcome, health outcome, forecast, or
probability. The candidate is SHA-locked and executable against held data, but
its ledger decision remains `INCOMPLETE` until an hourly pilot, pre-registered
sensitivity analysis, and human freeze approval are complete. See
`docs/product/PHOENIX_HOURLY_THERMAL_EVENT_CANDIDATE.md`.

## Evidence audit on 2026-09-03

The replay-only diagnostics were run without an API key and without live vendor
calls:

- `scripts/gate0_between_aoi.py` returned
  `INCOMPLETE_WITHOUT_LIVE_MULTI_AOI` because the clean repository has no
  qualifying multi-AOI replay bundle.
- `scripts/gate0_static_field.py` returned incomplete because the clean
  repository has neither the required downtown cache nor a tracked probe JSON.
- The tracked four-instant Phoenix comparison contains complete 25-zone means,
  but not the aligned tile fields required by the pre-registered static-field
  protocol. It is supporting context, not a substitute test.
- `scripts/gate0_nighttime.py` was not run because it can initiate live
  FortyGuard calls.

Ignored `workforce/` material cannot serve as runtime evidence. Any evidence
used to change a ledger decision must be committed at a repository-relative
path.

## Closure procedure

Gate 0 cannot be closed by merely editing `overall_status` or by relying on the
frozen `AreaConfig` marker.

1. Reproduce each incomplete decision from tracked inputs without substituting
   a weaker protocol.
2. Commit the evidence and reference it from the corresponding ledger item.
3. Change required decisions from `INCOMPLETE` to `VERIFIED` or `FROZEN`.
4. Commit an explicit human approval record and set `human_close_approval`.
5. Set the overall state to `CLOSED` and update the canonical ledger SHA in the
   registry.
6. Change and review the runtime policy before authorizing any currently
   blocked capability.

Until all six steps occur together, calibrated probability and downstream
priority claims remain fail-closed.
