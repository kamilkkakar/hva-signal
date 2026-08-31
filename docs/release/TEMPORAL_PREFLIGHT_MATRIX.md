# Temporal preflight matrix (zero-spend)

Gate 8 prep only. **No paid FortyGuard calls executed for this document.**

Verified SHA: `0f0f82fbc65702316986c20ca701c368922a0ad8` (`feat/final-hva-product-pass`)  
Source: offline `dry_run_type1_preflight` against current `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` AOIs (2026-08-31 regenerate).

## Geography caution (Phoenix Explore ≠ cross-city)

| Surface | Geography | Notes |
|---------|-----------|-------|
| Explore City Phoenix | `phoenix-demo` local analysis | Level-1 published local product |
| Cross-city / temporal / bounded selected-time | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | Frozen comparison AOIs for all four cities including Phoenix |

**Do not** use Phoenix Explore local AOI (`phoenix-demo`) for temporal matched-instant acquisition or bounded-route production calls.  
`data/areas/cross-city/phoenix/reuse_proof.json`: Explore vs CROSS_CITY → `reusable: NO` (0/25 tracts, zero spatial overlap).

| city_id | City | IANA | July offset | tract freeze prefix | AOI km² | expected tiles |
|---------|------|------|-------------|---------------------|---------|----------------|
| `las_vegas` | Las Vegas | America/Los_Angeles | PDT UTC−7 | `…PLACE_3240000.CROSS_CITY_COMPARISON_GEOGRAPHY_V1.4023d404` | 39.827 | 3983 |
| `tucson` | Tucson | America/Phoenix | UTC−7 (no DST) | `…PLACE_0477000.CROSS_CITY_COMPARISON_GEOGRAPHY_V1.3455b316` | 112.243 | 11225 |
| `los_angeles` | Los Angeles | America/Los_Angeles | PDT UTC−7 | `…PLACE_0644000.CROSS_CITY_COMPARISON_GEOGRAPHY_V1.7049e495` | 17.231 | 1724 |
| `phoenix` | Phoenix | America/Phoenix | UTC−7 (no DST) | `…PLACE_0455000.CROSS_CITY_COMPARISON_GEOGRAPHY_V1.d3185750` | 56.167 | 5617 |

Provider UTC (all cities UTC−7 in July):  
`03:00 D` → `2024-07-08T10:00:00Z` · `21:00` → `2024-07-09T04:00:00Z` · `03:00 D+1` → `2024-07-09T10:00:00Z`

Shared request shape for all 12 rows: **Type-1** · **TCM mean** · **100m** · **1 partition** · aggregation `HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN` · **25-zone** expectation.

## Existing published observation (do NOT reacquire)

| Contract | Clock | Cities | Output root |
|----------|-------|--------|-------------|
| `CROSS_CITY_OBSERVATION_V1` | 2024-07-08 **15:00** local | Phoenix, Las Vegas, Tucson, Los Angeles | `data/acquisitions/cross-city/{city_id}/` |

`data/acquisitions/cross-city/STOP_DECISION.json`: `additional_fortyguard_calls_authorized: false` (prior wave complete). **New human authorization required** before any Gate 8 spend.

## 12-row matrix (cache miss on all)

| # | city | city_id | local_datetime | timezone | UTC | geography | AOI notes | Type-1/TCM/100m | partition | request_fingerprint | cache_fingerprint | cache | aggregation | 25-zone | output path |
|---|------|---------|----------------|----------|-----|-----------|-----------|-----------------|-----------|---------------------|-------------------|-------|-------------|---------|-------------|
| 1 | Las Vegas | `las_vegas` | 2024-07-08T03:00:00 | America/Los_Angeles | 2024-07-08T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | 39.827 km² · PLACE_3240000 | yes | 1 | `88b650171311db6759d10430adf5c966a44542e6db4e396d7a007d7b5ba1c57c` | `1322c7dc6c2a751c1b3849eda4ea83061d799721910d857ab314e9c04bd4b04b` | **MISS** | national centroid-within mean | expect 25 | `data/acquisitions/cross-city/las_vegas/matched/20240708T030000/` |
| 2 | Las Vegas | `las_vegas` | 2024-07-08T21:00:00 | America/Los_Angeles | 2024-07-09T04:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | same | yes | 1 | `83aec0a8bd20a35203217eaa84bb0d2d36595ee0cbe823d24f9b3a040259f219` | `cd8be115892a551782bf6b7f486ffcd574e35fd8bf00088263027715ea174c56` | **MISS** | same | expect 25 | `…/las_vegas/matched/20240708T210000/` |
| 3 | Las Vegas | `las_vegas` | 2024-07-09T03:00:00 | America/Los_Angeles | 2024-07-09T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | same | yes | 1 | `014969941ec272f549f682abbb3ba8e79dc403f9a5a25264e18fcad650735b50` | `58a496c5e0de494be728e165c4233e577fc300ab8805f241b490d3428b3da32e` | **MISS** | same | expect 25 | `…/las_vegas/matched/20240709T030000/` |
| 4 | Tucson | `tucson` | 2024-07-08T03:00:00 | America/Phoenix | 2024-07-08T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | 112.243 km² · PLACE_0477000 · largest AOI | yes | 1 | `93349a84739f8607daf2a7cb658e808d6207b83d10e36bbc91491d9400d02c4b` | `0a483ec45595298960b1d59879bfd8f245c1e416042139ba1eac771906475342` | **MISS** | same | expect 25 | `…/tucson/matched/20240708T030000/` |
| 5 | Tucson | `tucson` | 2024-07-08T21:00:00 | America/Phoenix | 2024-07-09T04:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | same | yes | 1 | `387bad79d6ca79f45fac83b09659ae1ba23dc566884b44b2e6ec63befea668d6` | `d9238964e2b3c9280c15f30f862bd73bbde8b675b7692d8ccdef551d546d14a7` | **MISS** | same | expect 25 | `…/tucson/matched/20240708T210000/` |
| 6 | Tucson | `tucson` | 2024-07-09T03:00:00 | America/Phoenix | 2024-07-09T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | same | yes | 1 | `d191c7ffeaad67e2afc3fe20b99264f4470416ea61325275a70ee0c77d10b2d2` | `3858bf112ffbdcb2863a2aded32a3afecd29bb8eea9c69c64ba87184a4543b96` | **MISS** | same | expect 25 | `…/tucson/matched/20240709T030000/` |
| 7 | Los Angeles | `los_angeles` | 2024-07-08T03:00:00 | America/Los_Angeles | 2024-07-08T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | 17.231 km² · PLACE_0644000 · smallest AOI | yes | 1 | `30243c803c8b6ecec0074dc93f8551e35e9b19ddd7d70f20816a384e9d62ecbf` | `69fd1a4c413441e0d9b2bd404835a8aba89bd8a2c70aeb35135f4f5510a5c3ff` | **MISS** | same | expect 25 | `…/los_angeles/matched/20240708T030000/` |
| 8 | Los Angeles | `los_angeles` | 2024-07-08T21:00:00 | America/Los_Angeles | 2024-07-09T04:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | same | yes | 1 | `bf51c9f145f33e6356589b63590b54f7dc09aa004f7748e9ee966ec62901f578` | `abb04b335f91129c61d39e4ce6064f579fd6fd1f2cd019725928de4836f8fbed` | **MISS** | same | expect 25 | `…/los_angeles/matched/20240708T210000/` |
| 9 | Los Angeles | `los_angeles` | 2024-07-09T03:00:00 | America/Los_Angeles | 2024-07-09T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | same | yes | 1 | `9c0c12301f4554ce6978e73f86c42c729fa74ea3eb33581a0f12653366bace28` | `85702d41aa2e50f18e43fa772338cd8da304045f70c3ad426e40556f1cf0c3a8` | **MISS** | same | expect 25 | `…/los_angeles/matched/20240709T030000/` |
| 10 | Phoenix | `phoenix` | 2024-07-08T03:00:00 | America/Phoenix | 2024-07-08T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | **≠ phoenix-demo** · 56.167 km² · PLACE_0455000 | yes | 1 | `215290401a2e12fa559ac49382a9c679012e7f0b4bf45b2dfe85d74781d5ed5b` | `553668a05c0b07ca50d9f5a774904e4527397e8cfd7372126c28dd1967175ac5` | **MISS** (≠ Explore) | same | expect 25 | `…/phoenix/matched/20240708T030000/` |
| 11 | Phoenix | `phoenix` | 2024-07-08T21:00:00 | America/Phoenix | 2024-07-09T04:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | **≠ phoenix-demo** | yes | 1 | `8288371fdc0a5879c2851022b6a29a64926dc4c9b455b9e90779fb525703a195` | `5cea8cf02d0b3fc65f1128e964afbeea22c5de3d210e26dcc1ef386f5855227b` | **MISS** (≠ Explore) | same | expect 25 | `…/phoenix/matched/20240708T210000/` |
| 12 | Phoenix | `phoenix` | 2024-07-09T03:00:00 | America/Phoenix | 2024-07-09T10:00:00Z | `CROSS_CITY_COMPARISON_GEOGRAPHY_V1` | **≠ phoenix-demo** | yes | 1 | `cadf93cda9e46463928ab367448ddc7ba680529246456c5f7d5b59f919322fe6` | `bf2350fc172cb8d2a6e2506167e21a22fa4b9e46446d4460c3baf0603bb7f84f` | **MISS** (≠ Explore) | same | expect 25 | `…/phoenix/matched/20240709T030000/` |

Cache status is knowable without paying: no type1 live cache entries and no `matched/` acquisition trees exist for these clocks; only published 15:00 provenances are present.

## First production bounded-route candidates (LV / Tucson / LA)

Safe order for first paid / first bounded selected-time production exercise (after human env flip + authorization):

1. **`los_angeles`** — preferred first call: smallest AOI, lowest empirical upper bound, proven flat ~4220 debit at 15:00, no Explore/cross-city mismatch risk.
2. **`las_vegas`** — second: mid-size AOI, proven 15:00 acquisition, same UTC−7 July clock as LA.
3. **`tucson`** — third: largest AOI / highest tile estimate; still safe geography (no Explore mismatch) but higher scope risk — run only after LA/LV look normal.
4. **`phoenix` (CROSS_CITY only)** — last among the four: required for matched-instants package completeness, but operators must not confuse with Explore `phoenix-demo`.

## Operator acquire path

```text
python scripts/acquire_cross_city_type1.py los_angeles --local-datetime 2024-07-08T03:00:00 --dry-run
```

Approved clocks only: matrix 03:00 / 21:00 / D+1 03:00, plus default published `2024-07-08T15:00:00` (do not reacquire 15:00).

| Path | Paid calls? | Notes |
|------|-------------|-------|
| `POST /api/v1/live/selected-time` | Cache-first; miss may pay only when bounded live enabled | Geometry/time owned by server (`CROSS_CITY_COMPARISON_GEOGRAPHY_V1`) |
| `scripts/acquire_cross_city_type1.py` | Yes (external key env) | `--local-datetime` accepts approved matrix clocks; geometry/metric/resolution unchanged |
| GENERAL hosted live | Off | Never enable `HOSTED_LIVE_REAL_VENDOR_ENABLED` |

## Circuit breakers

- Debit > 5000 → STOP (prior wave flat ~4220 / city)
- Wrong geometry / time / metric / coverage → STOP
- Duplicate spend → turn live OFF
- Persist after **each** request; no blind retry
- Max **12** temporal + up to **2** forecast Type-1 requests this pass
- Forecast Gate 10: **BLOCKED** (no documented horizon) — do not spend forecast budget

## Package target after acquisition

`CROSS_CITY_MATCHED_INSTANTS_V1` — required before enabling Compare **Time** lens (`CROSS_CITY_MATCHED_INSTANTS_PACKAGE_ID` in web).

## Preflight verdict

**PASS (zero-spend)** — 12/12 fingerprints re-verified from current code; geography/timezone/UTC/25-zone/Type-1 TCM 100m checked; 15:00 excluded from reacquire.  
**BLOCKED (execution)** — needs (1) human Render `BOUNDED_SELECTED_TIME_LIVE_ENABLED=true` + `DAILY_LIMIT=40`, (2) human re-authorization superseding `STOP_DECISION`, (3) ACQUISITION-OWNER sequential paid run starting with Los Angeles.
