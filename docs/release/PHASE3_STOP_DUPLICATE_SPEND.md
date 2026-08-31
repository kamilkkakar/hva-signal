# Phase 3 STOP — duplicate spend

**Verdict: STOP acquisition.** Product UI KEEP (no core-shell loss). Do **not** merge. Do **not** continue Type-1.

## Remediation (unpaid) — see also `CACHE_PROOF_FIX.md`

Root cause: `DataMode.LIVE` in `FortyGuardAdapter._resolve` **always submitted** and never read `vendor_cache`. Cache-proof after the first LA Type-1 therefore created a second activity (+4220).

Fix on this branch: LIVE is now **cache-first** (adapter + bounded selected-time + operator `peek_vendor_cache`). Identical fingerprint → cached result, `vendor_attempted=false`, 0 new debit, no HTTP. GENERAL `refuse_real_vendor` / `may_construct_real_vendor` unchanged.

**Acquisition remains STOPPED** until human re-authorizes. This fix does not resume spend.

## Human action required (now)

On Render service `urban-thermal-api` set:

| Var | Value |
|-----|-------|
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | **`false`** |

Keep: `DATA_MODE=replay`, `HOSTED_LIVE_ENABLED=false`, `HOSTED_LIVE_REAL_VENDOR_ENABLED=false`, GENERAL vendor OFF.

Agent has **no Render CLI** in this environment to flip the var. Production Phase-1 construct is **not** deployed (main=`6bfde4a`), so public `POST /api/v1/live/selected-time` still returns `acquisition_unavailable` with `vendor_attempted=false` — but gate must still be turned OFF per circuit-breaker protocol.

## What happened

1. Pre-paid checks PASS (safety `6bfde4a`, `/health`+`/ready` replay, gate ON but cannot pay on prod, zero passive vendor on probes, LA matrix row match, operator dry-run PASS).
2. **REAL PATH:** operator `scripts/acquire_cross_city_type1.py` + local key file (not production bounded POST).
3. First intentional paid call **PASS:** LA `2024-07-08T03:00:00` — activity `0ab0d92f-…`, debit **4220**, tiles **1727**, zones **25**.
4. Cache-proof mistake: manual `DataMode.LIVE` adapter call **always submits** (does not read `vendor_cache`). Second activity `eea72b19-…` completed → debit **+4220**. Duplicate spend → **STOP**.

Script provenance gate correctly refused a second `acquire_cross_city_type1.py` run; the failure was the ad-hoc LIVE proof, not the acquire script.

## Counts

| Metric | Value |
|--------|-------|
| New Type-1 this wave | **2** (1 good + 1 duplicate) |
| Forecast | **0** |
| Session debit | **8440** |
| Matched matrix rows complete | **1 / 12** |
| `CROSS_CITY_MATCHED_INSTANTS_V1` | not built |
| Compare Time lens | not enabled |

## Do not

- Re-run acquire for remaining 11 clocks
- Enable GENERAL hosted live
- Merge `feat/final-hva-product-pass` → main until human re-authorization after this STOP
