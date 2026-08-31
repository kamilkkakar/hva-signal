# Resume Phase 3 — after human confirms API healthy

Wait for chat confirmation: `BOUNDED vars set; API healthy`

Then, **in order**, unpaid first:

1. **Phase 3 zero-spend QA** on `urban-thermal-api`
   - Confirm `BOUNDED_SELECTED_TIME_LIVE_ENABLED=true`, `BOUNDED_SELECTED_TIME_DAILY_LIMIT=40`
   - Confirm still `HOSTED_LIVE_REAL_VENDOR_ENABLED=false`, `DATA_MODE=replay`
   - Hit `POST /api/v1/live/selected-time` for a **published** city+15:00 clock → expect **cache hit** / no debit
   - Hit an uncached matrix clock with live still gated carefully → document response (`acquisition_unavailable` vs live miss path per deployed build)
   - Do **not** enable GENERAL hosted live

2. **Re-read** `docs/release/TEMPORAL_PREFLIGHT_MATRIX.md` (12 rows already verified offline)

3. **Human supersede** `data/acquisitions/cross-city/STOP_DECISION.json` before any new paid Type-1

4. **First paid call (if authorized):** Los Angeles `2024-07-08T03:00:00`
   ```text
   python scripts/acquire_cross_city_type1.py los_angeles --local-datetime 2024-07-08T03:00:00 --dry-run
   # then drop --dry-run only after dry-run gate pass + human GO
   ```
   Then Las Vegas → Tucson → Phoenix CROSS_CITY (never phoenix-demo). Persist after each; stop if debit > 5000.

5. **Forecast:** stays **BLOCKED** — do not spend Gate 10 budget.

Paid FortyGuard calls before step 4 GO: **must remain 0**.
