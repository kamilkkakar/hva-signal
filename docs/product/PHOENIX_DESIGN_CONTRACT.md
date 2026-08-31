# Phoenix Design Contract (Frozen)

**Status:** FROZEN — human-approved Phoenix product direction.  
**Approved HEAD (pre-polish):** `6a82515`  
**Freeze HEAD:** see git ref `safety/phoenix-design-approved-<SHORT_SHA>` after Phase 2 commit.  
**Branch:** `feat/judge-experience-overhaul`  
**Worktree:** `F:\cursor\hackathon-judge-experience-overhaul`

Do **not** broadly redesign Phoenix after this freeze. Multi-city work belongs on `feat/multicity-explorer` only.

## Story

Phoenix is a single-city Level-1 evidence product: one analysis area drives map, hero, temporal charts, context, preparedness, and verify-next direction. First-read language stays public and non-causal. Method tokens (`q_A`, Decision 8, job clocks, payload jargon) stay behind disclosure.

## Differentiator

FortyGuard zone-mean TCM (°C) as the thermal spine, with honest withhold when spatial differences are too small, own-area historical position when available, matched nighttime change, discrete observed instants, ACS + local canopy context, and preparedness inventory status — without scores, rankings-as-scores, or causal AI.

## Map rules

- Neutral paper geographic context — no external basemap tiles that can watermark API keys.
- Selected-time thermal uses **THERMAL_DISPLAY_SCALE_V1** (HVA display policy, fixed 15–60 °C envelope, ≤15 / ≥60 endcaps). Not a vendor physical range. No AOI stretch by default.
- Context modes (canopy / income / older housing) use their own legends — never the thermal legend.
- Selected area outline is the copper survey-pin accent.

## Temporal rules

- Matched nighttime: same calendar dates, same hour (03:00 local windows) — not a climate series.
- Observed instants: discrete points only; gaps are not measured.
- Historical position is own-area only and separate from spatial comparison.

## Context rules

- ACS facts with MOE gates; disclose when comparison is not supported.
- Phoenix local canopy may use the OHR shade-study plantable-ground semantics.
- Cross-city canopy (later) must never silently substitute Phoenix local canopy.

## Preparedness rules

- Inventory language: identified / not identified in available inventory / unknown.
- No “no row” / “no cooling site” first-read wording.

## Action / first-read rules

- Direction is evidence-responsive verify-next, not prescription.
- First viewport: brand, one support line, selected area + key °C, pattern, map — no operator chrome.
- Mobile section nav: Previous hidden at 01/05; Next hidden at 05/05.
- Historical unavailable disclosure label: **Why unavailable?**

## Visual reference

Canonical screenshots live under `docs/judge-experience/screenshots/` and are listed in `APPROVED_SCREENSHOTS.md`. That set is the Phoenix visual reference contract.

## Explicit non-goals (Phoenix freeze)

Correlation, regression, clustering, causal AI, scores, city rankings, forecast, WBGT, HeatDose, AfterHeat, month/season explorer, broad IA redesign.
