## READ-ONLY LIVE-PREFLIGHT — `POST /api/v1/live/selected-time`

Updated after Phase 1 architecture fix (narrow bounded construction). GENERAL vendor remains hard-refused.

### 1. Desired vs code defaults

| Variable | Code default | Desired production |
|----------|--------------|--------------------|
| `DATA_MODE` | `replay` | `replay` |
| `HOSTED_LIVE_ENABLED` | `false` | `false` |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` | `false` (**never** `true`) |
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `false` | `true` (human activation) |
| `BOUNDED_SELECTED_TIME_DAILY_LIMIT` | `20` | **`40`** |

### 2. Code path (selected-time live)

See also: [`BOUNDED_LIVE_VENDOR_PATH.md`](./BOUNDED_LIVE_VENDOR_PATH.md)

```
POST /api/v1/live/selected-time
  → bounded_selected_time_live.post_selected_time_live
       1) BOUNDED_SELECTED_TIME_LIVE_ENABLED? else 503
       2) daily limit
       3) Type1LiveClientRequest (server AOI)
       4) run_type1_live(..., bounded_selected_time_authorized=True)
            cache hit → cache_hit, vendor_attempted=false
            miss → construct_bounded_selected_time_http_client(Settings.fortyguard_api_key)
                 → FortyGuardAdapter LIVE (server geometry / 100m / TCM)
                 → seed type1 cache → live_acquired
```

GENERAL: `may_construct_real_vendor()` **always False**; `run_type1_live` without the bounded flag still `refuse_real_vendor()`.

### 3. Files

- `apps/api/app/api/routes/bounded_selected_time_live.py`
- `apps/api/app/domain/multicity/type1_live.py` (`construct_bounded_selected_time_http_client`)
- `apps/api/app/core/hosted_live_policy.py` (`may_construct_real_vendor` → always `False`)

### 4. Tests

`apps/api/tests/unit/test_bounded_selected_time_live.py` — general refuse; gate true/false construct; missing secret; secret not serialized; provider fields rejected; mock acquire + cache replay.

### 5. Activation

Flip only:

| Action | Variable | Value |
|--------|----------|-------|
| Keep | `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` |
| **Flip** | `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `true` |
| **Raise** | `BOUNDED_SELECTED_TIME_DAILY_LIMIT` | `40` |

Do **not** set `HOSTED_LIVE_REAL_VENDOR_ENABLED=true`.
