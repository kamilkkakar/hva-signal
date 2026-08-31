# AREA_IDENTITY_V1

Public UI primary label: `display_name` (Census tract NAMELSAD / GEOID-derived tract label).

Machine id: `area_id` (= GEOID). Keep stable for provenance.

Secondary: geography kind · City, State.

Naming hierarchy:
1. Authoritative neighborhood/district — **none packaged** (no invented names)
2. Census NAMELSAD when well-formed (contains decimal)
3. Census tract label derived from GEOID (`Census Tract 123.45`)
4. Generic Analysis/Comparison Area N — method detail only, not primary UI

Phoenix local vs cross-city Phoenix are **distinct** packages with distinct secondary labels.

FortyGuard area names: **NO** — FG remains thermal evidence source only.
