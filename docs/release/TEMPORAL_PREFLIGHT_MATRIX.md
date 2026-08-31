# Temporal preflight matrix (zero-spend)

Gate 8 prep only. **No paid FortyGuard calls executed in this document.**

Baseline SHA: `6bfde4afd081386d16aa900093e251d27a0f312b`  
Feature tip (at matrix write): see `feat/final-hva-product-pass`

## Geography caution

| Surface | Geography | Notes |
|---------|-----------|-------|
| Explore City Phoenix | `phoenix-demo` local analysis | Level-1 published local product |
| Cross-city / temporal | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | Frozen comparison AOIs for all four cities including Phoenix |

**Do not** use Phoenix Explore local AOI for temporal matched-instant acquisition.

## Existing published observation (do NOT reacquire)

| Contract | Clock | Cities |
|----------|-------|--------|
| `CROSS_CITY_OBSERVATION_V1` | 2024-07-08 **15:00** local | Phoenix, Las Vegas, Tucson, Los Angeles |

## Planned 12-row acquisition targets

Local civil times (naive, city timezone):

- 2024-07-08 **03:00**
- 2024-07-08 **21:00**
- 2024-07-09 **03:00** (next-day)

| # | city_id | geography | timezone | local_datetime | cache known? | notes |
|---|---------|-----------|----------|----------------|--------------|-------|
| 1 | las_vegas | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Los_Angeles | 2024-07-08T03:00:00 | unknown / prefer miss | Prefer first real call |
| 2 | las_vegas | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Los_Angeles | 2024-07-08T21:00:00 | unknown | |
| 3 | las_vegas | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Los_Angeles | 2024-07-09T03:00:00 | unknown | |
| 4 | tucson | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Phoenix | 2024-07-08T03:00:00 | unknown | |
| 5 | tucson | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Phoenix | 2024-07-08T21:00:00 | unknown | |
| 6 | tucson | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Phoenix | 2024-07-09T03:00:00 | unknown | |
| 7 | los_angeles | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Los_Angeles | 2024-07-08T03:00:00 | unknown | |
| 8 | los_angeles | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Los_Angeles | 2024-07-08T21:00:00 | unknown | |
| 9 | los_angeles | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Los_Angeles | 2024-07-09T03:00:00 | unknown | |
| 10 | phoenix | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 (**not** phoenix-demo) | America/Phoenix | 2024-07-08T03:00:00 | unknown | Cross-city AOI only |
| 11 | phoenix | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Phoenix | 2024-07-08T21:00:00 | unknown | |
| 12 | phoenix | CROSS_CITY_COMPARISON_GEOGRAPHY_V1 | America/Phoenix | 2024-07-09T03:00:00 | unknown | |

Fingerprint/cache keys are computed server-side by `type1_live` / FortyGuard cache fingerprint helpers (`apps/api/app/domain/multicity/type1_live.py`). Run dry-run preflight per row before spend.

## Acquisition path reality

| Path | Paid calls? | Notes |
|------|-------------|-------|
| `POST /api/v1/live/selected-time` | **No** on miss | Cache-first; `may_construct_real_vendor()` **always False**; miss → `acquisition_unavailable` |
| Operator script `scripts/acquire_cross_city_type1.py` | Yes (external key env) | Historical 15:00 acquisition path; extend carefully for new clocks |
| GENERAL hosted live | Off | Never enable `HOSTED_LIVE_REAL_VENDOR_ENABLED` |

## Circuit breakers

- Debit > 5000 → STOP
- Wrong geometry / time / metric / coverage → STOP
- Duplicate spend → turn live OFF
- Persist after **each** request; no blind retry
- Max **12** temporal + up to **2** forecast Type-1 requests this pass

## Package target after acquisition

`CROSS_CITY_MATCHED_INSTANTS_V1` — required before enabling Compare **Time** lens (`CROSS_CITY_MATCHED_INSTANTS_PACKAGE_ID` in web).

## Preflight verdict

**PASS (zero-spend planning)** — matrix defined, geography/timezone checked, 15:00 excluded from reacquire.  
**BLOCKED (execution)** — waiting on human Render/key activation + ACQUISITION-OWNER sequential paid run.
