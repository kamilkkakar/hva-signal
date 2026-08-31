# HUMAN ACTION REQUIRED — live / temporal activation

LEAD-RC cannot safely mutate Render production environment from this session.

## Desired API service env (`urban-thermal-api`)

Set **exactly**:

| Variable | Desired value |
|----------|---------------|
| `DATA_MODE` | `replay` |
| `HOSTED_LIVE_ENABLED` | `false` |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` (**must stay false**) |
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `true` |
| `BOUNDED_SELECTED_TIME_DAILY_LIMIT` | `40` |

Do **not** put FortyGuard secrets on `urban-thermal-web`.

## Important code constraint

Even with `BOUNDED_SELECTED_TIME_LIVE_ENABLED=true`, `POST /api/v1/live/selected-time` is **cache-first**. On cache miss, `may_construct_real_vendor()` returns **False** (hard program refuse). Public route will return `acquisition_unavailable` with **0** vendor calls.

Paid temporal acquisition for this pass must go through the **ACQUISITION-OWNER** operator path (`scripts/acquire_cross_city_type1.py` or a controlled extension), using the external server-side key env file — never print/log/commit the key.

## Confirm back in chat

Reply with:

1. Render API env updated to the table above (yes/no)
2. Whether operator key env file is available for ACQUISITION-OWNER (yes/no — **do not paste the key**)
3. Authorization to spend up to 12 temporal Type-1 requests on the 12-row matrix in `docs/release/TEMPORAL_PREFLIGHT_MATRIX.md`

Then LEAD-RC will continue Gate 8 → Time lens → Outlook (if forecast SUPPORTS) → pre-merge gates.
