# UX-C contract — judge experience (production bind)

Classification: bind-only. No invented fields.

| Surface | Route / source | Keys used | Units / semantics |
|---|---|---|---|
| Selected area | Client catalog `ANALYSIS_AREA_GEOIDS` | GEOID, Analysis Area N label | Identity only |
| Map geometry | `GET /api/v1/areas/{area_id}/geometry` | GeoJSON FeatureCollection, `GEOID`, polygon coordinates | Real Phoenix AOI polygons + restrained Carto basemap |
| Selected-time thermal (map + hero) | Cached seed `cachedPhoenixSnapshot.json` via `phoenixDemoCachedSelectedTime()` | `zone_id`, `mean_temperature_c`, `coverage_status` | Absolute °C; **fixed 25–45 scale by default**; optional enhance-local-contrast OFF |
| Dominant evidence pattern | `synthesizeNarrative` rule engine | spatial_diff, matched change, context, preparedness | Typed pattern — not a score |
| Historical position | Job `result.zones[].q_A` when D8 sufficient | q_A ∈ [0,1] → percent language | Own-area only; separated from spatial ranking |
| Spatial comparison | `thermal_differentiation_state` / ordering | withheld vs supported | Separate card from historical position |
| Matched nighttime | `GET /api/v1/demo/matched-nighttime-window?zone_id=` | `mean_by_year`, `change_2024_vs_2022`, `matched_nights`, median geography change | °C; line+points; 31 matched 03:00 nights |
| Observed instants | `GET /api/v1/demo/observed-thermal-instants?zone_id=` | Four instants, `temperature_c`, `direct_differences` | °C; discrete points; one interval note |
| Context | `GET /api/v1/areas/phoenix-demo/context?zone_id=` | ACS + canopy facts with MOE gates | Number-first cards; strengthen/weaken/complicate |
| Canopy semantics | Shade-study `TREE_PCT_N` | plantable-ground share verified in bundle | May say plantable ground |
| Preparedness | Context `cooling_site_status` | IDENTIFIED / NOT_IDENTIFIED_IN_DATASET / UNKNOWN | Heat-relief resources; no "no row" first-read |
| Direction | `synthesizeNarrative` | evidence_summary, why_it_matters, verify_next | Deterministic; evidence-responsive |
| Map mode legends | fill_kind gate | thermal vs canopy/income/housing | Own title/unit/palette — never thermal legend on context modes |
| Method / provenance | Collapsed `EvidenceDisclosure` | activity_id, q_A expand, Decision 8 | Level 3 only |

Not bound: combined score, vulnerability, WBGT, HeatDose, climate trend, 24-hour curve, intervention efficacy.
