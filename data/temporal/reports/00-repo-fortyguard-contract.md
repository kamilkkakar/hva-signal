# HVA-Signal / FortyGuard / Temporal Binding Contract (Repo Scout)

**Scout date:** 2026-08-30  
**Project root:** `f:\cursor\hackathon-temporal-intelligence`  
**Product:** HVA-Signal (3K Labs)  
**Contract version referenced:** `hva-signal-temporal-domain-v1`  
**Status:** Read-only scout — no FortyGuard calls, no climate downloads

---

## 1. Executive summary

The canonical HVA-Signal codebase lives at **`hackathon-temporal-intelligence`**. It is a replay-first urban heat decision-support product with a frozen **25-zone census-tract analysis window** (`phoenix-demo`) and a substantial **backend temporal domain layer** that is **not yet wired to public UI or on-disk public climate cubes**.

| Layer | Current state |
|---|---|
| **FortyGuard** | Spatial thermal surface only — 100 m TCM tiles aggregated to 25 zones via centroid-within mean. Used for Signal A/B thermal evidence, not regional climatology. |
| **Public temporal context** | Domain types + mixing rules exist (`TemporalSourceFamily.PUBLIC`). All committed fixtures are **synthetic**. No nClimGrid / NLDAS / URMA ingest pipeline in repo. |
| **Temporal UI** | No climate time-series widgets in the main web app. Signal A uses a **historical position strip** (q_A), not daily/seasonal charts. Daily / seasonal context stays **unpublished**. JudgeShell mounts a **dated cached Signal B** bind (phoenix-demo 2025-07-15 03:00, **25/25**, `fortyguard_cached`) as **AVAILABLE NOW — CACHED EVIDENCE**. The two-signal rail stays **unmounted** unless `VITE_HVA_SELECTED_TIME_SNAPSHOT=1`. Downtown TCM **0/25** remains the negative **GATE 1** fixture. |
| **On-disk temporal data** | **`data/temporal/` does not exist yet** (this report creates `data/temporal/reports/`). Real evidence today is `data/phoenix/reference/` (FortyGuard-derived replay panel). |

**Binding rule (implementable):** Public sources supply **AOI/regional temporal context** at their native grain. FortyGuard supplies **local spatial evidence** at 100 m → 25-zone aggregation. **Never downscale public regional series to 25 tracts.** **Never blend families into one number.**

---

## 2. Project location and duplicates

### Canonical project

| Path | Role |
|---|---|
| `f:\cursor\hackathon-temporal-intelligence\` | **Primary HVA-Signal repo** — README, apps, data, tests, infra |

### Related but not canonical

The workspace contains many sibling `hackathon-*` trees (e.g. `hackathon-live-o-deploy`, `hackathon-decision-ui-2`) that fork or snapshot the same stack. **Bind new temporal work to `hackathon-temporal-intelligence` only** unless a parent agent explicitly targets another tree.

`hackathon-decision-ui-2` contains a `TemporalChart.tsx` workforce prototype with **empty/pending** state (`"awaiting temporal program"`). It is **not** part of the shipped HVA-Signal web app.

---

## 3. Spatial model: 25 zones / tracts

### Definition

- **Zone type:** U.S. Census 2020/2025 tract (`GEOID` property)
- **Expected count:** exactly **25** (`EXPECTED_ZONE_COUNT = 25`)
- **Frozen demo:** `phoenix-demo` under policy `PHX_DEMO_AOI_POLICY_V1`
- **Geometry version:** `US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f`

### Aggregation pipeline (FortyGuard → zones)

```
FortyGuard heatmap (100 m TCM tiles, °C)
  → assign_tiles_centroid_within(zones_geojson, tiles_geojson)
  → aggregate_mean_temperature(per zone)
  → ZoneThermalSeries / ZoneThermalObservation
```

Key files:

| File | Purpose |
|---|---|
| `apps/api/app/services/zone_aggregator.py` | Centroid-within assignment + zone mean |
| `apps/api/app/domain/phoenix_v1.py` | Frozen PHX constants (25 zones, aggregation version, reference window) |
| `data/demo/phoenix/area_config.json` | Human-frozen AreaConfig |
| `data/areas/phoenix-demo/geometry.geojson` | 25-tract GeoJSON |
| `data/phoenix/reference/observations.jsonl` | Frozen replay panel: 93 timestamps × 25 GEOIDs × 03:00 local |

### National resolver (future geography, not demo)

- Library + harness: `scripts/national_resolver_panel.py`
- Policy candidate: `NATIONAL_PLACE_GEOGRAPHY_V1`
- Selects a connected 25-tract analysis window **within** a Census Place
- Downloads TIGER place + tract layers when `HVA_CENSUS_FETCH=1`
- **Public resolve disabled** at default flags; L2 timezone gate open

### Spatial scope in temporal domain

`SpatialScope` enum: `zone` | `aoi`

- **FortyGuard observations:** always zone-scoped after tile join (`spatial_scope=ZONE`, `zone_id` required)
- **Public regional context:** must use `spatial_scope=AOI` with **`zone_id=None`** — do not assign public grid cells to tracts

---

## 4. FortyGuard role (spatial thermal evidence only)

### What FortyGuard provides

| Attribute | Value |
|---|---|
| **Quantity** | `tcm_zone_mean` (`TemperatureQuantity.TCM_ZONE_MEAN`) |
| **Source family** | `TemporalSourceFamily.FORTYGUARD` |
| **Spatial grain** | 100 m tiles → 25-zone centroid-within mean |
| **Temporal modes (API)** | `single_hour`, `hour_range`, `full_day`, `day_range`, `month` → FortyGuard `filter_type` 1–4 |
| **Wire modes** | `replay`, `fortyguard_cached`, `fortyguard_live` |

### What FortyGuard does **not** provide in this architecture

- Regional climatology or CONUS-scale context
- JJA/DJF seasonal summaries at AOI level without zone cube held locally
- Public 2 m air temperature (`public_2m_air_zone_mean` is forbidden on FortyGuard family)
- Automatic 24-hour daily profiles unless a held hourly cube exists

### Integration surface

| File | Role |
|---|---|
| `apps/api/app/integrations/fortyguard/adapter.py` | All vendor HTTP (backend-only key) |
| `apps/api/app/integrations/fortyguard/mapper.py` | Heatmap JSON → tile observations |
| `apps/api/app/integrations/fortyguard/temporal_modes.py` | Request payload builder |
| `apps/api/app/integrations/fortyguard/partitioning.py` | AOI partition planning |
| `apps/api/app/services/temporal_normalize.py` | Cached 25-zone snapshot → domain types |
| `scripts/sanitize_fortyguard_fixture.py` | Sanitize replay fixtures (no API key in output) |

### Replay evidence (committed)

| Path | Content |
|---|---|
| `apps/api/tests/fixtures/fortyguard/` | Sanitized heatmap fixtures |
| `data/phoenix/reference/observations.jsonl` | Decision 1B runtime panel (93 × 25 @ 03:00) |
| `apps/api/tests/fixtures/temporal/live_record.json` | Documents cache reuse (`live_calls: 0`) |

Default deployment: `DATA_MODE=replay`, `FORTYGUARD_API_KEY` empty — **no vendor calls on public path**.

---

## 5. Public temporal context (domain — not yet on disk)

### Existing code contracts

| File | Role |
|---|---|
| `apps/api/app/domain/temporal.py` | Provider-neutral types; `hva-signal-temporal-domain-v1` |
| `apps/api/app/services/temporal_source.py` | Provenance stamps; **refuse_blend** across families |
| `apps/api/app/services/temporal_assemble.py` | Held-document assembly (`NOT_PREPARED` if cube missing) |
| `apps/api/app/services/temporal_store.py` | Candidate SQLite zone-hour store |
| `apps/api/app/services/daily_thermal_profile.py` | HOURLY_24 profile (missing hours stay missing) |
| `apps/api/app/services/seasonal_thermal.py` | JJA/DJF calendar; S2-only → NOT_PREPARED |
| `apps/api/app/services/year_over_year.py` | YoY comparability gates |
| `apps/api/app/api/routes/temporal_internal.py` | **Unpublished** internal router (not on public app) |

### Public family rules (already enforced in code)

```python
# temporal_source.py — mixed family = two objects; no blended number
refuse_blend(TemporalSourceFamily.FORTYGUARD, TemporalSourceFamily.PUBLIC)  # raises SourceMixError

# temporal.py — public cannot claim TCM
stamp_public(acquire_mode="replay")
# → source_family=PUBLIC, temperature_quantity=PUBLIC_2M_AIR_ZONE_MEAN, variable_id=fixture_2m_t
```

### Season / window vocabulary (backend)

| Window ID pattern | Meaning |
|---|---|
| `SEASON:JJA:{year}` | Jun 1 – Aug 31 (92 days) |
| `SEASON:DJF:{year}` | Dec 1 – Feb 29/28 (91 days) |
| `HOURLY_24` | 24 hourly slots, AOI-local civil day |
| `ANCHOR_0300` | Single 03:00 anchor (Decision 1B / S2) |

**Note:** Phoenix demo Signal A uses a **narrow seasonal window** (Jun 30 – Jul 30) for q_A reference — distinct from JJA/DJF product calendar in `seasonal_thermal.py`.

### Public datasets **not** in repo (search results)

| Dataset | In codebase? |
|---|---|
| nClimGrid | **No** ingest, schema, or paths |
| NLDAS | **No** |
| URMA | **No** |
| RTMA | **Research only** — `scripts/gate0_rtma_sample.py` compares Gate 0 AOIs vs FortyGuard (Gate 0 audit, not product pipeline) |

### Synthetic fixtures only

All under `apps/api/tests/fixtures/temporal/` — every `SOURCE.json` declares:

```json
{
  "kind": "SYNTHETIC_FIXTURE",
  "not_product_data": true,
  "not_phoenix_climatology": true,
  "not_public_observation": true
}
```

Subfolders: `daily/`, `seasonal/`, `yoy/`, `coverage/`, `zones_25/`, `public_context/`.

---

## 6. Temporal UI / widgets (current state)

### Main web app (`apps/web`)

| Component | Path | State |
|---|---|---|
| **HistoricalPositionStrip** | `features/judgeShell/charts/HistoricalPositionStrip.tsx` | **Live** — shows per-zone q_A marks at 03:00 (Signal A). Not a climate chart. |
| **SelectedZonePosition** | `features/judgeShell/charts/SelectedZonePosition.tsx` | Zone click detail for historical position |
| **SignalRail (A/B)** | `features/signals/SignalRail.tsx` | **Unmounted** unless `VITE_HVA_SELECTED_TIME_SNAPSHOT=1` |
| **Signal B section** | `features/signals/SignalBSection.tsx` | Shared presenter. Public phoenix-demo bind is the **cached 25/25** JudgeShell panel (`SignalBCachedPanel`), not this rail |
| **Signal B cached panel** | `features/judgeShell/signalB/SignalBCachedPanel.tsx` | **AVAILABLE NOW — CACHED EVIDENCE** — phoenix-demo 2025-07-15 03:00, 25/25, `fortyguard_cached`. Not live |
| **GATE 1 downtown fixture** | `features/judgeShell/signalB/SignalBUnavailableDisclosure.tsx` | Downtown TCM **0/25** — negative unavailable contract. Do not rewrite this to the 25/25 bind |
| **TemporalChart** | — | **Does not exist** in main web app |
| **Daily / seasonal / YoY charts** | — | **Not implemented** in UI — still unpublished |

Default flags (`apps/web/src/features/signals/flags.ts`):

- `VITE_HVA_SELECTED_TIME_SNAPSHOT` → **off** (two-signal rail unmounted)
- `VITE_HVA_LIVE_DEMO_CONFIRMATION` → **off**

`presentTwoSignals()` sets `mounted: false` when snapshot flag is off — entire A/B rail hidden. That flag-off rail is **not** the public Signal B surface. JudgeShell already binds the dated cached 25/25 snapshot. Daily and seasonal temporal widgets remain unpublished.

### What the UI actually shows today

1. **Map** — 25-zone choropleth (Signal A rank or withhold)
2. **Historical position strip** — q_A distribution across zones (not temperature time series)
3. **Action framing** — Decision 8 authorize/withhold copy
4. **Cached Signal B** — dated phoenix-demo 2025-07-15 03:00, 25/25, **AVAILABLE NOW — CACHED EVIDENCE**. Not live. Downtown 0/25 GATE 1 fixture stays separate
5. **No** 24-hour profile, JJA/DJF panel, or public climatology widget — daily/seasonal still unpublished

### Backend temporal API

- `POST /internal/v1/temporal/documents:assemble` — returns `NOT_PREPARED` stub
- **Not registered** on public FastAPI app (`temporal_internal.py` docstring)
- `GET never acquires` — assembly from held cube only

**Verdict:** Temporal **widgets for public climate context are empty/unbuilt**. Existing charts are **Signal A historical-position visuals**, backed by frozen FortyGuard replay — not NOAA temporal cubes.

---

## 7. Data directories and schemas (existing)

### Committed data layout

```text
data/
├── areas/
│   ├── registry.json
│   └── phoenix-demo/
│       ├── geometry.geojson      # 25-tract analysis window
│       └── manifest.json
├── census/2025/SOURCE.json       # Gazetteer metadata (place national zip)
├── demo/phoenix/
│   ├── area_config.json          # PHX_AREA_CONFIG_V1 (human-frozen)
│   ├── metadata.json
│   └── README.md
└── phoenix/reference/
    └── observations.jsonl        # 93×25 frozen TCM panel @ 03:00

apps/api/tests/fixtures/
├── fortyguard/                   # Sanitized vendor replay
└── temporal/                     # Synthetic unit oracles (NOT product data)
```

### Temporal store schema (candidate, SQLite)

Defined in `apps/api/app/services/temporal_store.py`:

- **`zone_hour`** — per zone, UTC/local hour, temperature, source_family, temperature_quantity, sampling_design, geometry/aggregation versions
- **`daily_profile_summary`**, **`season_summary`**, **`year_comparison_summary`**

Feature flag: `HVA_TEMPORAL_STORE_BACKEND` (default in-memory).

### Domain document IDs (assemble layer)

| Kind | ID pattern |
|---|---|
| Daily profile | `tdp.v1.{area_id}.{zone_id}.{local_date}.{design}.{source_mode}` |
| Season summary | `tss.v1.{area_id}.{zone_id}.{window_id}.{design}.{source_mode}` |
| YoY comparison | `tyc.v1.{area_id}.{zone_id}.{window_id}.{year_a}.{year_b}.{design}.{source_mode}` |

Publication status: **`UNPUBLISHED`** — `FAMILY_CONTRACT = hva-signal-temporal-documents-v1`

---

## 8. Environment variables

### Backend (`.env.example`)

| Variable | Default / note |
|---|---|
| `DATA_MODE` | `replay` |
| `FORTYGUARD_API_KEY` | empty (backend only) |
| `FORTYGUARD_BASE_URL` | `https://api.fortyguard.com` |
| `CACHE_DIR` | `.cache/fortyguard` |
| `HVA_TEMPORAL_STORE_BACKEND` | opt-in SQLite path (code) |
| `HVA_PUBLIC_GEOGRAPHY` | `0` — place/geography routes off |
| `HVA_PUBLIC_TWO_SIGNAL` | `0` — two-signal API off |
| `HVA_CENSUS_FETCH` | `0` — no live TIGER HTTP |

### Frontend (Vite)

| Variable | Default | Effect |
|---|---|---|
| `VITE_HVA_SELECTED_TIME_SNAPSHOT` | off | Signal B / two-signal rail |
| `VITE_HVA_LIVE_DEMO_CONFIRMATION` | off | Live demo confirmation UI |
| `VITE_HVA_JUDGE_SHELL` | on (≠ `0`) | JudgeShell vs CommandCenter |
| `VITE_HVA_PLACE_SEARCH` | off | Place search |

---

## 9. Download / maintenance scripts

| Script | Purpose | FortyGuard? |
|---|---|---|
| `scripts/sanitize_fortyguard_fixture.py` | Sanitize vendor JSON → test fixtures | Reads local raw only |
| `scripts/national_resolver_panel.py` | TIGER place/tract download + 25-zone resolver harness | No |
| `scripts/gate0_rtma_sample.py` | Sample NWS RTMA 2.5 km for Gate 0 AOI comparison | Compare label only |
| `scripts/gate0_*.py` | Spatial/temporal audit scripts (research) | Some require API key in env file |
| `scripts/verify-public-deploy.*` | Deploy smoke | No |

**No script** currently downloads nClimGrid, NLDAS, or URMA into the repo.

---

## 10. Proposed binding contract

### 10.1 Role separation

| Role | Source family | Spatial grain | Temporal grain | Quantity | May join to 25 zones? |
|---|---|---|---|---|---|
| **Regional temporal context** | `PUBLIC` | Native grid / station / CONUS cell | Hourly, daily, monthly, seasonal (source-native) | `public_2m_air_zone_mean` or source-specific ID | **NO** — AOI scope only |
| **Local spatial evidence** | `FORTYGUARD` | 100 m tiles → 25 tracts | Hourly instant or vendor window aggregate | `tcm_zone_mean` | **YES** — zone-scoped only |
| **Unit tests** | `FIXTURE` | synthetic | synthetic | either (labeled) | test-only |

### 10.2 Hard prohibitions (align with existing code)

1. **No silent fusion** — `refuse_blend()`, `assert_homogeneous_series()`, `juxtapose_or_none()` → two objects in API/UI
2. **No public → tract downscaling** — public records carry `spatial_scope=AOI`, `zone_id=null`
3. **No TCM labels on public data** — `temperature_quantity` must differ; `analytic=tcm` forbidden on PUBLIC
4. **No GET/acquire on assemble** — public cubes must be pre-materialized on disk; `assemble_from=held_only`
5. **Missing ≠ zero** — empty coverage → `NOT_PREPARED` / `INSUFFICIENT`, never `0 °C`
6. **Every value carries** — `source_family`, `source_mode`, `temperature_quantity`, `spatial_scope`, `window_id` or `valid_time_local`, `aggregation_method` (if zoned), `geometry_version` (if zoned)

### 10.3 Juxtaposition pattern (UI/API)

When both families are available for the same analysis window:

```json
{
  "regional_context": {
    "source_family": "public",
    "spatial_scope": "aoi",
    "dataset_id": "nclimgrid-daily-tmax",
    "window_id": "SEASON:JJA:2024",
    "mean_temperature_c": 34.2,
    "provenance": { "...": "native CONUS 5km — not downscaled" }
  },
  "local_spatial_evidence": {
    "source_family": "fortyguard",
    "spatial_scope": "zone",
    "zones": [ "...25 ZoneThermalObservation..." ],
    "provenance": { "...": "100m TCM centroid-within mean" }
  },
  "blend_forbidden": true
}
```

### 10.4 Suggested public source mapping (future — not implemented)

| Use case | Candidate public source | Native grain | HVA binding |
|---|---|---|---|
| Regional daily Tmax/Tmin context | nClimGrid-Daily | ~5 km CONUS | AOI daily series; no tract split |
| Land-surface / soil moisture context | NLDAS-2 | 0.125° | AOI only |
| Hourly 2 m analysis (CONUS) | URMA/RTMA | 2.5 km | AOI hourly; compare to FG only in audit scripts |
| Seasonal context (JJA/DJF) | Derived from daily public cube | AOI | `SEASON:JJA:YYYY` documents at AOI scope |

**Do not claim product readiness for any row until a SOURCE.json + held cube exists.**

---

## 11. Proposed on-disk paths

Create under project root ( **`data/temporal/` is new** — no conflict with existing trees):

```text
data/temporal/
├── raw/                          # Immutable vendor/NOAA downloads
│   ├── public/
│   │   ├── nclimgrid/
│   │   │   └── {dataset}/{year}/...
│   │   ├── nldas/
│   │   └── urma/
│   └── fortyguard/               # Optional: pre-sanitized bulk (never raw secrets)
│       └── README.md             # "Use scripts/sanitize_fortyguard_fixture.py"
├── cube/                         # Normalized held artifacts (assemble reads here)
│   ├── public/
│   │   └── aoi/
│   │       └── {area_id}/
│   │           ├── daily/{local_date}.json
│   │           ├── season/{window_id}.json
│   │           └── SOURCE.json   # dataset id, grain, vintage, method
│   └── fortyguard/
│       └── zone/
│           └── {area_id}/
│               ├── zone_hour/{valid_time_utc}.json
│               └── SOURCE.json
├── store/                        # Optional SQLite (HVA_TEMPORAL_STORE_BACKEND path)
│   └── temporal_store.sqlite
└── reports/                      # Scout + audit markdown (this file)
    └── 00-repo-fortyguard-contract.md
```

### Alignment with existing paths

| Existing | Relationship |
|---|---|
| `data/phoenix/reference/observations.jsonl` | **FortyGuard replay panel** — keep; do not move without migration plan. Maps to `cube/fortyguard/zone/phoenix-demo/` conceptually. |
| `apps/api/tests/fixtures/temporal/` | **Synthetic oracles** — stay in tests; do not promote to `data/temporal/cube/`. |
| `.cache/fortyguard` | Runtime vendor cache — not canonical held cube. |

### SOURCE.json template (public AOI cube)

```json
{
  "kind": "HELD_PUBLIC_CUBE",
  "source_family": "public",
  "dataset_id": "nclimgrid-daily-tmax",
  "spatial_grain": "native_conus_5km",
  "spatial_scope": "aoi",
  "downscale_to_zones": false,
  "area_id": "phoenix-demo",
  "timezone": "America/Phoenix",
  "method": "aoi_representative_or_bbox_mean",
  "vintage": "2024",
  "sha256": "..."
}
```

---

## 12. Key files index (for binding agents)

### Domain & services

- `apps/api/app/domain/temporal.py`
- `apps/api/app/domain/phoenix_v1.py`
- `apps/api/app/services/temporal_source.py`
- `apps/api/app/services/temporal_normalize.py`
- `apps/api/app/services/temporal_assemble.py`
- `apps/api/app/services/temporal_store.py`
- `apps/api/app/services/zone_aggregator.py`
- `apps/api/app/services/daily_thermal_profile.py`
- `apps/api/app/services/seasonal_thermal.py`
- `apps/api/app/services/year_over_year.py`

### FortyGuard

- `apps/api/app/integrations/fortyguard/adapter.py`
- `apps/api/app/integrations/fortyguard/mapper.py`
- `apps/api/app/integrations/fortyguard/temporal_modes.py`

### UI

- `apps/web/src/features/judgeShell/charts/HistoricalPositionStrip.tsx`
- `apps/web/src/features/judgeShell/signalA/SignalAPanel.tsx`
- `apps/web/src/features/signals/SignalRail.tsx`
- `apps/web/src/features/signals/presentation.ts`

### Tests (contract locks)

- `apps/api/tests/contract/temporal/test_source_modes.py`
- `apps/api/tests/contract/temporal/test_domain_types.py`
- `apps/api/tests/contract/fortyguard/test_temporal_and_partitions.py`

### Product docs

- `README.md` (sections 7, 8, 16 — Signal A/B, data/provenance)

---

## 13. Next binding contract (short, implementable)

**Phase 0 — paths & metadata (no downloads)**

1. Create `data/temporal/raw/public/`, `data/temporal/cube/public/aoi/phoenix-demo/`, `data/temporal/cube/fortyguard/zone/phoenix-demo/`
2. Add `SOURCE.json` to each cube leaf documenting grain, scope, and `downscale_to_zones: false` for public
3. Wire `HVA_TEMPORAL_STORE_BACKEND` optional path to `data/temporal/store/temporal_store.sqlite`

**Phase 1 — public ingest (offline scripts, not API)**

1. Add `scripts/temporal/fetch_public_{nclimgrid,nldas,urma}.py` writing only to `data/temporal/raw/public/`
2. Add `scripts/temporal/build_public_aoi_cube.py` → `cube/public/aoi/{area_id}/` at **AOI scope**
3. Normalize into `TemporalProvenance` with `source_family=PUBLIC`, `spatial_scope=AOI`

**Phase 2 — assemble (internal route first)**

1. Extend `temporal_assemble.py` to read held public AOI documents from `data/temporal/cube/public/`
2. Keep FortyGuard zone documents separate — return juxtaposed payload
3. Register internal route only; public OpenAPI unchanged until publication gate

**Phase 3 — UI (after cubes exist)**

1. New `RegionalContextPanel` at AOI scope — **not** 25-tract choropleth
2. Keep `HistoricalPositionStrip` FortyGuard/q_A only
3. Do not mount `SignalRail` until genuine Signal B cube exists

---

## 14. Scout constraints observed

- No git push
- No FortyGuard API calls
- No climate data downloaded
- No invented product claims — all maturity statements sourced from `README.md` and code flags
- Public and FortyGuard sources documented separately throughout
