# UX-C contract — judge experience (production bind)

Classification: bind-only. No invented fields.

| Surface | Route / source | Keys used | Units / semantics |
|---|---|---|---|
| Selected area | Client catalog `ANALYSIS_AREA_GEOIDS` | GEOID, Analysis Area N label | Identity only |
| Map geometry | `GET /api/v1/areas/{area_id}/geometry` | GeoJSON FeatureCollection, `GEOID`, polygon coordinates | Real Phoenix AOI polygons |
| Selected-time thermal (map + hero) | Cached seed `cachedPhoenixSnapshot.json` via `phoenixDemoCachedSelectedTime()` | `zone_id`, `mean_temperature_c`, `coverage_status` | Absolute °C; fixed 25–45 scale on map |
| Historical position | Job `result.zones[].q_A` when D8 sufficient | q_A ∈ [0,1] → percent language | Withheld when differentiation insufficient |
| Matched nighttime | `GET /api/v1/demo/matched-nighttime-window?zone_id=` | `mean_by_year`, `change_2024_vs_2022`, `matched_nights`, `matched_nights_warmer`, `analysis_geography.median_change_2024_vs_2022` | °C; 31 matched 03:00 nights |
| Observed instants | `GET /api/v1/demo/observed-thermal-instants?zone_id=` | Four instants, `temperature_c`, `direct_differences` | °C; discrete points only |
| Context | `GET /api/v1/areas/phoenix-demo/context?zone_id=` | ACS + canopy facts with MOE gates | Percent / USD; no scores |
| Preparedness | Context `cooling_site_status` | IDENTIFIED / NOT_IDENTIFIED_IN_DATASET / UNKNOWN | Never "NO COOLING SITE" |
| Direction | `composeSelectedAreaStory` rules R0–R5 | Evidence-specific verify lines | No priority scores |
| Method / provenance | Collapsed `EvidenceDisclosure` | activity_id, q_A expand, Decision 8 | Not first-read |

Not bound: combined score, vulnerability, WBGT, HeatDose, climate trend, 24-hour curve, intervention efficacy.
