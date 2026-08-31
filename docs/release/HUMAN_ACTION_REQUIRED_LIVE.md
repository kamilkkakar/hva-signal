# HUMAN ACTION REQUIRED — live / temporal activation

LEAD-RC cannot safely mutate Render production environment from this session.

Audits incorporated: LIVE-PREFLIGHT, TEMPORAL-PREFLIGHT, FORECAST-AUDIT (see `docs/release/*_AUDIT.md` and matrix).

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

## Important code constraints

1. Even with `BOUNDED_SELECTED_TIME_LIVE_ENABLED=true`, `POST /api/v1/live/selected-time` is **cache-first**. On cache miss, `may_construct_real_vendor()` returns **False** (hard program refuse). Public route returns `acquisition_unavailable` with **0** vendor calls.
2. Paid temporal acquisition must go through **ACQUISITION-OWNER** operator path (`scripts/acquire_cross_city_type1.py` or controlled extension). That script is currently **hardcoded to 15:00** — must be extended for the 12-row matrix clocks before spend.
3. `data/acquisitions/cross-city/STOP_DECISION.json` has `additional_fortyguard_calls_authorized: false`. Explicit new human authorization is required to supersede that stop.
4. Forecast / Thermal Outlook: **BLOCKED** (no documented horizon) — do not authorize forecast paid calls.

## Confirm back in chat

Reply with:

1. Render API env updated to the table above (yes/no)
2. Operator key env file available for ACQUISITION-OWNER (yes/no — **do not paste the key**)
3. Authorization to supersede `STOP_DECISION` and spend up to **12** temporal Type-1 requests on `docs/release/TEMPORAL_PREFLIGHT_MATRIX.md`
4. Authorization to extend `acquire_cross_city_type1.py` for non-15:00 clocks (yes/no)

Then LEAD-RC continues Gate 8 → Time lens → pre-merge gates. Outlook stays blocked unless forecast contract becomes SUPPORTS.
