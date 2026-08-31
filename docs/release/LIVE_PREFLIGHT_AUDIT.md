## READ-ONLY LIVE-PREFLIGHT — `POST /api/v1/live/selected-time`

Repo: `F:\cursor\hackathon-final-hva-product-pass`  
Blueprints: `infra\render.yaml` ≡ root `render.yaml` (byte-identical).  
No files changed. No paid calls. Key not printed.

---

### 1. Current blueprint / defaults

| Env var | Blueprint (`infra/render.yaml`) | Code default (`Settings`) | Desired (activation) |
|---------|----------------------------------|---------------------------|----------------------|
| `DATA_MODE` | `replay` | `replay` | `replay` |
| `HOSTED_LIVE_ENABLED` | `false` | `false` | `false` |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` | `false` | `false` (**never** `true`) |
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `false` | `false` | `true` (human activation only) |
| `BOUNDED_SELECTED_TIME_DAILY_LIMIT` | `"20"` | `20` | **`40`** |
| `FORTYGUARD_API_KEY` | `sync: false` (dashboard secret) | `""` | leave empty for zero-spend / replay |
| `DEMO_ALLOWANCE_*` | disabled / `0` | off | stay off |
| `CACHE_DIR` | `/tmp/fortyguard-cache` | `.cache/fortyguard` | server-owned |

Observable public check: `GET /ready` → `data_mode` only (does **not** expose bounded/live flags).

**Gap vs desired:** blueprint still has bounded surface **OFF** and daily limit **20**, not 40.

---

### 2. Code path (selected-time live)

```
POST /api/v1/live/selected-time
  → bounded_selected_time_live.post_selected_time_live
       1) BOUNDED_SELECTED_TIME_LIVE_ENABLED? else 503 bounded_selected_time_live_disabled
       2) in-memory daily budget check (vendor attempts only)
       3) body: city_id + local_datetime only (extra/server-owned fields → 422)
       4) run_type1_live(Type1LiveClientRequest, FortyGuardCache(CACHE_DIR))
            a) cache lookup by server fingerprint
               → HIT: status=cache_hit, vendor_attempted=False  ← zero spend
            b) MISS: spend_gate + construct_vendor_stage
               → may_construct_real_vendor() ALWAYS False
               → refuse_real_vendor() → HostedLiveDisabledError
               → route maps to acquisition_unavailable, vendor_attempted=False
       5) daily counter increments ONLY if vendor_attempted (should stay 0 while vendor refused)
```

Key files:
- `apps\api\app\api\routes\bounded_selected_time_live.py`
- `apps\api\app\domain\multicity\type1_live.py` (`run_type1_live`)
- `apps\api\app\core\hosted_live_policy.py` (`may_construct_real_vendor` → always `False`)

**`DATA_MODE`:** not consulted as a spend gate on this route (client `data_mode` is rejected). Replay remains public-path authority via settings / `/ready`.

**`HOSTED_LIVE_*`:** not required to open the bounded route; real vendor construction is program-hard-refused regardless of env.

---

### 3. HUMAN ACTION REQUIRED — Render env (cannot safely mutate live Render from here)

Deploy docs: hosting is **HUMAN-controlled** Render workspace; `FORTYGUARD_API_KEY` is **dashboard-only** (`sync: false`). This session is read-only and must not edit blueprints or touch secrets.

To reach desired config on **`urban-thermal-api`** (dashboard env and/or blueprint sync + redeploy):

| Action | Exact env var | Exact value |
|--------|---------------|-------------|
| Keep | `DATA_MODE` | `replay` |
| Keep | `HOSTED_LIVE_ENABLED` | `false` |
| Keep | `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` |
| **Flip** | `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `true` |
| **Raise** | `BOUNDED_SELECTED_TIME_DAILY_LIMIT` | `40` |
| Confirm | `FORTYGUARD_API_KEY` | empty / unset for zero-spend (never set from repo; never print) |
| Keep | `DEMO_ALLOWANCE_ENABLED` | `false` |
| Keep | `DEMO_ALLOWANCE_MAX_TOTAL_UNITS` | `0` |

Do **not** set `HOSTED_LIVE_REAL_VENDOR_ENABLED=true` (code still refuses construction; flipping it is policy-forbidden and confusing).

After change: confirm in Render UI (repo cannot see live dashboard overrides). Redeploy/restart so process picks up env.

---

### 4. Cache proof approach (0 vendor calls on hit)

Safe, no-paid methods:

1. **Unit proof (already in repo):** `apps\api\tests\unit\test_bounded_selected_time_live.py`
   - `test_bounded_live_cache_hit_zero_vendor` — seed via `seed_type1_live_cache`, POST → `status=cache_hit`, `provenance.vendor_attempted=false`, `acquisition_language=cache_hit`
   - `test_bounded_live_cache_miss_refuses_vendor` — miss → `acquisition_unavailable`, message includes no Type-1 request

2. **Live/staging proof (after human enables bounded flag only):**
   - Seed server cache for known `(city, hour)` under `CACHE_DIR` (operator seed / prior safe payload) **or** use a fingerprint already present
   - `POST /api/v1/live/selected-time` with `{"city_id":"…","local_datetime":"…T..:00:00"}`
   - Assert response: `status == "cache_hit"`, `provenance.vendor_attempted === false`
   - Optional: API logs show no outbound FortyGuard HTTP; usage delta not needed if never constructing vendor
   - Miss path should still be `acquisition_unavailable` with `vendor_attempted=false` while real vendor refused

3. **What not to do for proof:** do not enable real vendor; do not call `/v1/heatmap`; do not print/use API key.

---

### 5. Risk notes

| Risk | Detail |
|------|--------|
| Blueprint ≠ desired | Bounded OFF + limit 20 until human sets `BOUNDED_*=true` / `40` |
| Real vendor hard-off | `may_construct_real_vendor()` always `False` — miss never pays; also means no live acquisition via this route until a future program change |
| Debit >5000 breaker | Documented for Temporal/acquisition-owner scripts; **not wired** into this POST path |
| `HVA_LIVE_*` resource guards | Hosted-live worker path only; **not** this bounded route |
| Daily limit | In-process memory; Free sleep/restart resets counter; counts only `vendor_attempted` (usually unused while vendor refused) |
| `/tmp` cache | Free tier ephemeral — cache hits may vanish after sleep/redeploy; seed may need re-run |
| `DATA_MODE` ≠ route gate | Leaving `DATA_MODE=replay` is correct intent but does not alone disable the POST once bounded flag is on |
| Env mutation | Repo/blueprint edits alone do not update a running service until human applies blueprint/dashboard + redeploy; secret key never from repo |
| Client privilege | Body cannot supply AOI/key/base_url/`data_mode`; still refuse client force-live |

**Verdict:** With blueprint as-is, the route is **503-disabled** and vendor construction is **hard-refused** → zero-spend safe. Desired activation (`BOUNDED=true`, `DAILY_LIMIT=40`, others false/replay) requires **human Render action**; do not enable `HOSTED_LIVE_REAL_VENDOR_ENABLED`.