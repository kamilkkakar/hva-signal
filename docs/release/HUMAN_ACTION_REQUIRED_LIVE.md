# HUMAN ACTION REQUIRED — bounded live env only

LEAD-RC cannot mutate Render production environment from this session (no `RENDER_API_KEY` / Render CLI).

**Phase 1 (architecture) is complete** on `feat/final-hva-product-pass` @ `4a074a6`. Zero paid calls.

## Set ONLY these two on `urban-thermal-api`

| Variable | Required value |
|----------|----------------|
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `true` |
| `BOUNDED_SELECTED_TIME_DAILY_LIMIT` | `40` |

## Confirm already correct (do not change unless wrong)

| Variable | Required value |
|----------|----------------|
| `DATA_MODE` | `replay` |
| `HOSTED_LIVE_ENABLED` | `false` |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` (**never** `true`) |
| `FORTYGUARD_API_KEY` | present (do not paste) |

Do **not** put FortyGuard secrets on `urban-thermal-web`.

## After deploy healthy

Reply in chat: `BOUNDED vars set; API healthy` — LEAD-RC resumes Phase 3 (zero-spend QA) → temporal preflight → ≤12 acquisitions.
