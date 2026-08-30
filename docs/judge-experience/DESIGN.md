# HVA-Signal judge experience — internal design

Classification: architectural UI overhaul. Implementation is authorized by the parent program after this contract lock.

## Skills used

- using-git-worktrees
- frontend-design
- brainstorming
- verification-before-completion

## UX-C contract (bind only these)

| Surface | Source | Fields used |
|---|---|---|
| Selected area | Catalog GEOID order | `Analysis Area N`, GEOID secondary |
| Signal A / historical position | Job `result.zones[].q_A` only when D8 `SUFFICIENT` and ordering permitted | Percent language from q_A ∈ [0,1]. Never print `q_A` on first-read |
| Spatial ranking | `thermal_differentiation_state` / limitations | Supported vs withheld. Withhold is a feature |
| Signal B snapshot | Cached phoenix seed | Absolute °C, 2025-07-15 03:00 America/Phoenix, 25/25 |
| Matched nighttime | `GET /api/v1/demo/matched-nighttime-window` | `mean_by_year`, `change_2024_vs_2022`, `matched_nights`, median change |
| Observed instants | `GET /api/v1/demo/observed-thermal-instants` | Four named instants, `temperature_c`, direct deltas. Discrete only |
| Context | `GET /api/v1/areas/phoenix-demo/context?zone_id=` | canopy, income, pre-1980, one-person, year built, age 65+ with MOE gates |
| Preparedness | `cooling_site_status` / story sentences | IDENTIFIED / NOT IDENTIFIED IN THIS DATASET / UNKNOWN |
| Action | Existing direction rules + withhold copy | Verify, do not prescribe |

Not invented: combined score, vulnerability score, HeatDose, AfterHeat, WBGT, climate trend, hourly curve, intervention efficacy.

## IA (20-second path)

1. Brand + one sentence + FortyGuard cached badge
2. Selected Analysis Area + key °C + historical position or withhold + 2024 vs 2022
3. Large map (clickable polygons + compact selector)
4. Matched-night chart
5. Observed-instant chart
6. Context cards
7. Preparedness
8. So what? evidence → interpretation → verify
9. About this evidence (collapsed)

## Visual system

Mineral civic desk, not a research notebook.

- Paper `#EEF1EC` · Ink `#1C2420` · Field `#243833` · Copper `#C45C26` · Quiet `#D7DDD6` · Brass `#8A6A2F`
- Display: Literata. Body: Source Sans 3. Data: Source Code Pro (temperatures only)
- Signature: copper survey-pin — one accent that marks the selected area on hero, map outline, and chart highlight

## Selection

One GEOID drives map, hero, charts, context, preparedness, and direction. Default Analysis Area 1. Default replay is the existing 2022-07-01 03:00 window (ranking withheld is the honest first state).
