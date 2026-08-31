# Render / runtime env variable audit (from actual code)

Sprint: guided-live finish. Values never include secrets. FortyGuard key placeholder only.

## urban-thermal-api (server only)

| Env var | Read in code | Default | Public/prod intent | Notes |
|---------|--------------|---------|-------------------|-------|
| `APP_ENV` | `Settings.app_env` | `development` | `production` on Render | |
| `DATA_MODE` | `Settings.data_mode` | `replay` | `replay` | Public path authority |
| `LOG_LEVEL` | `Settings.log_level` | `info` | `info` | |
| `CACHE_DIR` | `Settings.cache_dir` | `.cache/fortyguard` | `/tmp/fortyguard-cache` | Server cache root |
| `FORTYGUARD_API_KEY` | `Settings.fortyguard_api_key` | `""` | sync:false secret | **API only. Never print. Never on web.** Use `<PASTE FORTYGUARD API KEY HERE>` in operator runbooks. |
| `FORTYGUARD_BASE_URL` | `Settings.fortyguard_base_url` | `https://api.fortyguard.com` | same | API only |
| `HOSTED_LIVE_ENABLED` | `Settings.hosted_live_enabled` | `false` | `false` | GENERAL hosted-live gate |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `Settings.hosted_live_real_vendor_enabled` | `false` | `false` | Still refused by `may_construct_real_vendor()` |
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `Settings.bounded_selected_time_live_enabled` | `false` | `false` until release decision | **Separate** from GENERAL vendor |
| `BOUNDED_SELECTED_TIME_DAILY_LIMIT` | `Settings.bounded_selected_time_daily_limit` | `20` | `20` | Counts vendor attempts only |
| `DEMO_ALLOWANCE_ENABLED` | `Settings.demo_allowance_enabled` | `false` | `false` | |
| `DEMO_ALLOWANCE_MAX_TOTAL_UNITS` | `Settings.demo_allowance_max_total_units` | `0` | `0` | |
| `DEMO_ALLOWANCE_MAX_UNITS_PER_REQUEST` | settings | `1` | leave default | |
| `DEMO_ALLOWANCE_ALLOWED_AREAS` | settings | `""` | leave default | |
| `DEMO_ALLOWANCE_VALID_FROM` / `_UNTIL` | settings | `""` | leave default | |
| `DEMO_ALLOWANCE_STORE_PATH` | settings | `""` | leave default | |
| `DEMO_ALLOWANCE_RESERVATION_TTL_SECONDS` | settings | `900` | leave default | |
| `DEMO_ALLOWANCE_MAX_OPEN_RESERVATIONS` | settings | `8` | leave default | |
| `OPERATOR_APPROVAL_ENABLED` | settings | `false` | `false` | |
| `LOCAL_SQLITE_PERSISTENCE_ENABLED` | settings | `false` | `false` | |
| `LOCAL_SQLITE_PATH` | settings | `""` | leave default | |
| `HVA_PUBLIC_CONTEXT` | settings / os | `true` / `1` | `1` | Cache-only context GETs |
| `HVA_PUBLIC_TEMPORAL_STORIES` | settings | `true` / `1` | `1` | Cache-only temporal GETs |
| `HVA_PUBLIC_TWO_SIGNAL` | settings | `false` / `0` | `0` | |
| `HVA_PUBLIC_GEOGRAPHY` | `os.environ` | off | `0` | |
| `HVA_PUBLIC_SAFETY_MIDDLEWARE` | `os.environ` | on when set | `1` | |
| `API_PUBLIC_URL` | settings | localhost | from Render service | |
| `WEB_PUBLIC_URL` | settings | localhost | from Render web | |
| `ALLOWED_ORIGINS` | settings | localhost | web public URL | |
| `HVA_LIVE_*` | live_resource_guards / retry_timeout | process ceilings | operator only | Never on web |

## urban-thermal-web (non-secret flags only)

| Env var | Read in code | Default / bake | Notes |
|---------|--------------|----------------|-------|
| `PORT` | Docker/nginx | `10000` | |
| `API_UPSTREAM` | reverse proxy | Render API URL | |
| `WEB_PUBLIC_URL` | from Render | self URL | |
| `VITE_HVA_JUDGE_SHELL` | `App.tsx` | `1` | Judge shell ON |
| `VITE_API_BASE_URL` | optional | same-origin proxy | |
| `VITE_HVA_PUBLIC_CONTEXT` | gate | bake if used | Non-secret |
| `VITE_HVA_PLACE_SEARCH` | flags | bake if used | Non-secret |
| `VITE_HVA_LIVE_DEMO_CONFIRMATION` | flags | off | Non-secret UI only |
| `VITE_HVA_SELECTED_TIME_SNAPSHOT` | flags | off | Non-secret |

**Forbidden on web:** `FORTYGUARD_API_KEY`, all `HOSTED_LIVE_*`, `BOUNDED_SELECTED_TIME_*`, `DEMO_ALLOWANCE_*`, `DATA_MODE` as spend authority, `HVA_LIVE_*`.

## Gate separation

| Gate | Purpose | Default |
|------|---------|---------|
| GENERAL arbitrary vendor | `may_construct_real_vendor()` always False this program | OFF |
| Hosted live demo flag | `HOSTED_LIVE_ENABLED` | OFF |
| Bounded selected-time surface | `BOUNDED_SELECTED_TIME_LIVE_ENABLED` → `POST /api/v1/live/selected-time` | OFF |
| Real vendor construction | refused even if flags flipped (program hard-stop) | OFF |

Cache-hit on bounded route = **0** vendor calls. Cache-miss returns `acquisition_unavailable` without a paid call.
