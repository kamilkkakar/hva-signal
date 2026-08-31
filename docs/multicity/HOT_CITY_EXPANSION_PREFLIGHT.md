# Hot-city expansion preflight — Yuma & Palm Springs

## Decision

**BLOCKED — no FortyGuard acquisition.** Both candidate places fail
`CROSS_CITY_COMPARISON_GEOGRAPHY_V1` / ALG1 preflight. Per release safety:
do not acquire, do not substitute, do not claim hotter-than-Phoenix.

## Candidates

| City | Place GEOID | Timezone (intended) | ALG1 result |
|------|-------------|---------------------|-------------|
| Yuma, AZ | `0485540` | America/Phoenix | **FAIL** `INSUFFICIENT_CONNECTED_TRACTS` |
| Palm Springs, CA | `0655254` | America/Los_Angeles | **FAIL** `INSUFFICIENT_ELIGIBLE_TRACTS` |

## Details

### Yuma

- Place found in TIGER 2025 AZ places.
- Eligible tracts exist (26), but the seed rook-connected component has only
  **6** tracts; **25** are required.
- Outside-place expansion is not performed by ALG1.
- Matches existing national-resolver fail-closed pin for Yuma.

### Palm Springs

- Place found in TIGER 2025 CA places (`0655254` confirmed).
- Eligible tract count = **17** (&lt; 25 required).
- Place is not expanded.

## Vendor calls

- Authorized max new FortyGuard calls this wave: **2**
- Actual new calls: **0**
- Public live vendor: **OFF**
- Hosted end-user vendor triggering: **OFF**

## Explorer impact

- Cross-City Explorer remains the published **four-city** set
  (Phoenix, Las Vegas, Tucson, Los Angeles).
- Hue families for Yuma (red/coral) and Palm Springs (gold/magenta) are
  reserved in `apps/web/src/features/crossCity/colors.ts` for a future
  geography-compatible release — not shown in the live allowlist.
