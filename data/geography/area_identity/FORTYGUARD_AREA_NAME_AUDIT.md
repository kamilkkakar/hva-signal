# FortyGuard area-name audit (AREA_IDENTITY_V1)

**Date:** 2026-08-31  
**Scope:** official FG integration + retained fixtures/raw heatmap + map_data/stats/activity metadata  
**Paid FG calls this pass:** 0

## Verdict

| Question | Answer |
|---|---|
| **FORTYGUARD_AREA_NAME_AVAILABLE** | **NO** |
| **FIELD** | none for neighborhood / locality / public polygon name |
| **SEMANTICS** | Thermal tile / activity evidence only (`temperature`, partitions, activity ids, time labels) |
| **STABLE ENOUGH FOR PUBLIC LABEL** | **NO** |

## Evidence reviewed

- `apps/api/app/integrations/fortyguard/` transport + mapper + assembly — no place/neighborhood name fields on zone identity.
- Retained fixtures under `apps/api/tests/fixtures/fortyguard/` — `label` appears only as temporal/instant labels, not geography names.
- Cross-city acquisitions `data/acquisitions/cross-city/*/raw/` — tile geometry + thermal means; no locality names usable as polygon titles.
- Product contract docs already treat FG as spatial thermal surface aggregated to census tracts.

## Implication

FortyGuard remains the **thermal evidence source only**. Public primary labels come from **AREA_IDENTITY_V1** census geography packages (`data/geography/area_identity/`), not FG metadata and not invented neighborhood names.
