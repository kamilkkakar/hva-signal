## FORECAST-AUDIT (SHA `6bfde4a` / `feat/final-hva-product-pass`)

### 1. FORTYGUARD FORECAST CONTRACT: **BLOCKED**

### 2. DOCUMENTED HORIZON
**None found.**  
- `docs/client` is **absent** (not in this worktree; not in sibling trees checked).  
- No in-repo FortyGuard provider/client doc states a forecast horizon.  
- Gate text notes prior research *suggested* ~+12h TCM forecast but says **do not assume**; do not invent +6h/+12h (`_gate_specs_extract.txt`).  
- HVA `AnalysisRequest.horizon_hours` is **0–12** (product field). UI: “Operational (0–12h) is **not** a forecast.” — not a vendor forecast horizon.

### 3. ENDPOINT / SEMANTICS found
**Observed Type-1 heatmap only** (no forecast-specific API):

| Item | Evidence |
|------|----------|
| Base | `https://api.fortyguard.com` |
| Submit | `POST /v1/heatmap` |
| Poll | `GET /v1/status/{activity_id}` |
| Auth | `api-key` header |
| Request body | `polygon_aoi`, `date_time.{start_date,start_time?,end_time?,end_date?,filter_type}`, `granularity`, `analytic_type` (+ optional `threshold`/`direction`) |
| `filter_type` | 1=`single_hour`, 2=`hour_range`, 3=`full_day`, 4=`day_range`/`month` |
| Response (adapter) | submit → `{data.activity_id}`; status → `{data.status, result}`; tiles from `result.map_data.features[].properties` (`tile_id`, `average_temperature`, `min_temperature`, `max_temperature`) + optional `stats_data` |
| Type-1 contract | endpoint `/v1/heatmap`, mode `single_hour`, filter_type `1`, metric `"TCM mean"`, 100 m |

No endpoint/field in client or docs that **explicitly** marks forecast/prediction.

### 4. TCM support notes
- Type-1 metric: **TCM** / `analytic_type: "tcm"`; product quantity zone-mean TCM °C.  
- Mapper treats tile temps as **Celsius** (notes official client docstring °F as wrong).  
- Repo treats FG as **spatial thermal / observed** evidence, not climatology or WBGT.  
- **No** TCM-as-forecast contract documented.

### 5. 100m resolution notes
- Adapter default / Type-1: `granularity` / `TYPE1_RESOLUTION_M = 100` (also allows 60, 80).  
- Repo scout: 100 m TCM tiles → zone aggregation.  
- Documented for **heatmap Type-1**, not as a forecast-horizon contract.

### 6. Thermal Outlook without inventing horizons?
**No.** Gate: ship THERMAL OUTLOOK only if forecast is supported and only with **documented** horizons. Contract is BLOCKED → cannot implement without inventing horizons (e.g. +6h/+12h).

### 7. Evidence file paths
- **Missing:** `F:\cursor\hackathon-final-hva-product-pass\docs\client` (does not exist)  
- `F:\cursor\hackathon-final-hva-product-pass\_gate_specs_extract.txt` (§25–29)  
- `F:\cursor\hackathon-final-hva-product-pass\docs\release\PRE_FINAL_HVA_PRODUCT_ROLLBACK.md` (budget: “up to 2 forecast” — spend budget, not horizon)  
- `F:\cursor\hackathon-final-hva-product-pass\docs\product\PHOENIX_DESIGN_CONTRACT.md` (forecast = non-goal)  
- `F:\cursor\hackathon-final-hva-product-pass\data\temporal\reports\00-repo-fortyguard-contract.md`  
- `F:\cursor\hackathon-final-hva-product-pass\apps\api\app\integrations\fortyguard\{client,adapter,temporal_modes,transport_models,mapper,cache}.py`  
- `F:\cursor\hackathon-final-hva-product-pass\apps\api\app\domain\multicity\type1_live.py`  
- `F:\cursor\hackathon-final-hva-product-pass\apps\api\app\domain\requests.py` (`horizon_hours` 0–12)  
- `F:\cursor\hackathon-final-hva-product-pass\apps\api\tests\fixtures\fortyguard\heatmap_tcm_hourly_1500.json`  
- `F:\cursor\hackathon-final-hva-product-pass\apps\api\tests\contract\fortyguard\test_cache_ttl.py`  
- `F:\cursor\hackathon-final-hva-product-pass\apps\web\src\features\command-center\QueryRail.tsx`

### 8. Existing forecast code in `apps/api`
**No forecast fetch / Thermal Outlook route.** Closest:
- `integrations/fortyguard/cache.py` — TTL for `start_date >= today` labeled “Operational/forecast” (cache policy only; **not** vendor forecast contract).  
- `tests/contract/fortyguard/test_cache_ttl.py` — same.  
- `domain/requests.py` — product `horizon_hours` 0–12 (not FG forecast).  
- Adapter/client: **only** `/v1/heatmap` + `/v1/status/{id}` for observed temporal modes 1–4.