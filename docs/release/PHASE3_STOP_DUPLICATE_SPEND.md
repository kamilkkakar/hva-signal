# Phase 3 STOP — duplicate spend

> **Current resolution (1 Sep 2026):** this document is retained as the incident record for the stopped acquisition wave. The duplicate-spend bug was subsequently remediated with cache-first LIVE/AUTO behaviour and regression coverage. The replay product release is **not blocked by this historical STOP**. New paid temporal acquisition and public bounded-live activation remain blocked until a separate production cache/spend proof is explicitly authorized and passes.

## Incident verdict

**STOP acquisition.** Product UI KEEP (no core-shell loss). At the time of the incident: do **not** merge and do **not** continue Type-1 acquisition.

## Remediation (unpaid) — see also `CACHE_PROOF_FIX.md`

Root cause: `DataMode.LIVE` in `FortyGuardAdapter._resolve` always submitted and never read `vendor_cache`. Cache-proof after the first LA Type-1 therefore created a second activity (+4220).

The remediation made LIVE/AUTO cache-first and added cache checks to the bounded selected-time and operator paths. An identical fingerprint must resolve from cache with `vendor_attempted=false`, no HTTP request and no new debit. GENERAL `refuse_real_vendor` / `may_construct_real_vendor` remains unchanged.

The fix does **not** itself authorize new spend.

### Release status after remediation

- Replay/public product release: **allowed after the later release gate passed**.
- General real-vendor construction: **OFF**.
- Bounded selected-time public live: **OFF until a separate production cache/spend proof**.
- Remaining cross-city matched-time acquisition: **not resumed by this resolution**.
- Forecast: **BLOCKED**.

This distinction matters: resolving the code defect and allowing the replay release did not reopen the acquisition budget.

## Required production posture

Keep:

| Var | Value |
|-----|-------|
| `DATA_MODE` | `replay` |
| `HOSTED_LIVE_ENABLED` | `false` |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` |
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `false` until separate proof |

GENERAL vendor remains OFF.

## What happened

1. Pre-paid checks passed: safety ref present, `/health` and `/ready` in replay, zero passive vendor activity, LA matrix row match and operator dry-run passed.
2. **REAL PATH:** operator `scripts/acquire_cross_city_type1.py` + local secret (not the production bounded POST).
3. First intentional paid call succeeded: LA `2024-07-08T03:00:00` — activity `0ab0d92f-…`, debit **4220**, tiles **1727**, zones **25**.
4. The cache-proof mistake used an ad-hoc `DataMode.LIVE` adapter path that always submitted instead of reading vendor cache. A second activity `eea72b19-…` completed for another **4220** debit.
5. Duplicate spend triggered the STOP. The normal acquisition script had correctly refused a second paid run via its provenance gate.

## Counts at the STOP

| Metric | Value |
|--------|-------|
| New Type-1 calls in this wave | **2** (1 intended + 1 duplicate) |
| Forecast calls | **0** |
| Session debit | **8440** |
| Matched matrix rows complete | **1 / 12** |
| `CROSS_CITY_MATCHED_INSTANTS_V1` | not built |
| Compare Time lens | not enabled |

## Still prohibited without new authorization

- Re-running acquisition for the remaining matched clocks
- Enabling GENERAL hosted live
- Enabling public bounded selected-time live without the production cache/spend proof
- Treating this incident resolution as blanket authorization for FortyGuard spend
