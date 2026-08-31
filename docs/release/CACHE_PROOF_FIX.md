# Cache-proof fix — LIVE must be cache-first

**Related STOP:** `docs/release/PHASE3_STOP_DUPLICATE_SPEND.md`  
**Status:** unpaid remediation on `feat/final-hva-product-pass`. Acquisition remains **STOPPED** until human re-authorizes.

## Root cause

`FortyGuardAdapter._resolve` treated `DataMode.LIVE` as **always submit**:

1. Operator path `scripts/acquire_cross_city_type1.py` builds `HeatmapFetchRequest(data_mode=LIVE)` and calls `adapter.fetch_heatmap`.
2. Bounded selected-time miss path `_bounded_selected_time_acquire` also uses `DataMode.LIVE`.
3. `run_type1_live` correctly checks the **type1_live** cache before acquire, but an ad-hoc / operator LIVE call that hits the **adapter vendor cache** still re-submitted because LIVE skipped `cache.get(fingerprint)`.
4. Cache-proof after LA `2024-07-08T03:00:00` (debit 4220) used `DataMode.LIVE` directly → second activity / **+4220**. Provenance gate on the acquire script refused a second scripted run; the bypass was the LIVE adapter path.

AUTO mode already preferred cache; LIVE did not. That asymmetry is the duplicate-spend bug.

## Fix (minimal)

| Layer | Change |
|-------|--------|
| `FortyGuardAdapter._resolve` | LIVE and AUTO both **cache-first**. Identical fingerprint → `FORTYGUARD_CACHED`, no `_fetch_live`. |
| `type1_live._bounded_selected_time_acquire` | If assembly source is cached → `status=cache_hit`, `vendor_attempted=false`. |
| `acquire_cross_city_type1.py` | `peek_vendor_cache` **before** usage / heatmap submit; cache hit → `vendor_attempted=false`, `debit=0`. |

GENERAL vendor policy unchanged: `may_construct_real_vendor` / `refuse_real_vendor` stay hard-refuse. Bounded construction still requires `BOUNDED_SELECTED_TIME_LIVE_ENABLED` + route flag only.

## Regression tests (mock vendor only; paid calls = 0)

- `tests/contract/fortyguard/test_data_mode.py::test_live_mode_cache_hit_zero_http_no_new_activity`
- `tests/unit/test_bounded_selected_time_live.py::test_run_type1_live_vendor_disk_cache_hit_zero_http`
- `tests/unit/test_acquire_cross_city_datetime.py::test_peek_vendor_cache_hit_no_http`

## How to re-authorize safely later (human only)

Do **not** continue acquisition until all of the following are true:

1. Render `BOUNDED_SELECTED_TIME_LIVE_ENABLED=false` (circuit breaker) unless a new bounded wave is explicitly authorized.
2. Human writes a new authorization note (authorized Type-1 count, cities/clocks, debit budget).
3. Operator dry-run PASS for the next matrix row.
4. Prefer proving cache via **seeded cache + mock** or `peek_vendor_cache` / `run_type1_live` cache_hit — **never** a second LIVE submit “to check cache.”
5. After a successful Type-1, identical city+local+fingerprint must show `vendor_attempted=false` / debit 0 before any further paid row.
6. Do not merge to main until STOP is formally lifted.

Paid FortyGuard calls in this remediation: **0**.
