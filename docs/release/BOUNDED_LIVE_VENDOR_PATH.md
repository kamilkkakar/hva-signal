## BOUNDED SELECTED-TIME LIVE — exact call path

**Date:** 2026-08-31  
**Commit intent:** `live: narrow bounded vendor construction path`  
**Paid calls in this change:** **0** (unit tests use `httpx.MockTransport` only)

### Separation invariant

| Path | Authority | Construction |
|------|-----------|--------------|
| GENERAL real vendor | `may_construct_real_vendor()` → **always False**; `refuse_real_vendor()` always raises | **Never** constructs `FortyGuardHttpClient` |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | Must stay **false**; ignored for construction | Does **not** authorize client |
| Bounded selected-time | `BOUNDED_SELECTED_TIME_LIVE_ENABLED` + route flag `bounded_selected_time_authorized=True` | **Only** `construct_bounded_selected_time_http_client()` |

### Exact call path (cache miss → vendor)

```
POST /api/v1/live/selected-time
  body: { city_id, local_datetime }   # extra/provider fields → 422
  → bounded_selected_time_live.post_selected_time_live
       1) BOUNDED_SELECTED_TIME_LIVE_ENABLED? else 503 bounded_selected_time_live_disabled
       2) daily limit (vendor attempts only)
       3) Type1LiveClientRequest(city=server catalog, target_local=body)
       4) FortyGuardCache(settings.cache_dir)
       5) run_type1_live(..., bounded_selected_time_authorized=True)
            a) dry_run_type1_preflight (server AOI / 100m / TCM / CROSS_CITY geometry)
            b) cache.get(cache_fingerprint) → cache_hit (vendor_attempted=false)
            c) MISS → _bounded_selected_time_acquire
                 → construct_bounded_selected_time_http_client(settings)
                      requires gate true
                      may_construct_real_vendor must still be False
                      Settings.fortyguard_api_key (empty → MissingApiKeyError → acquisition_unavailable, 0 paid)
                      returns FortyGuardHttpClient(api_key=…, base_url=settings.fortyguard_base_url)
                 → FortyGuardAdapter(http_client=…, data_mode=LIVE, server polygon)
                 → seed_type1_live_cache (sanitized; secrets stripped)
                 → status=live_acquired, vendor_attempted=true
```

### GENERAL refuse path (unchanged)

```
run_type1_live(..., bounded_selected_time_authorized=False)  # default
  → cache miss → construct_vendor_stage() → refuse_real_vendor() → HostedLiveDisabledError
```

Browser / other routes never pass `bounded_selected_time_authorized=True`.

### Proof tests

`apps/api/tests/unit/test_bounded_selected_time_live.py`:

- general vendor refused even with hosted/real/bounded flags + secret present
- bounded constructs only when gate true; refuses when false
- missing secret → safe acquisition_unavailable (0 vendor)
- secret never in HTTP response (seeded or live)
- arbitrary client provider fields rejected (422)
- mock transport acquire + identical request → cache_hit, no second POST

### Activation (Phase 2 — not done in this commit)

Desired API env remains:

- `DATA_MODE=replay`
- `HOSTED_LIVE_ENABLED=false`
- `HOSTED_LIVE_REAL_VENDOR_ENABLED=false` (**never true**)
- `BOUNDED_SELECTED_TIME_LIVE_ENABLED=true`
- `BOUNDED_SELECTED_TIME_DAILY_LIMIT=40`
