# HVA-Signal

**Heat, Vulnerability & Action Signal** · 3K Labs

HVA-Signal is a map-first decision-support tool for urban heat resilience. It helps a city team answer a simple but important question:

> **Does the thermal evidence actually justify treating particular zones differently?**

If the answer is yes, the product helps the user inspect where the difference is. If the answer is no, HVA-Signal does not manufacture a hotspot ranking. It keeps the thermal finding visible, adds local context, and points to the next evidence or operational checks that may matter.

**Public web:** https://urban-thermal-web.onrender.com  
**API:** https://urban-thermal-api.onrender.com  
**Health:** https://urban-thermal-api.onrender.com/health  
**Readiness:** https://urban-thermal-api.onrender.com/ready

---

## What the product does

The interface follows one decision loop:

**HEAT → CONTEXT → ACTION → OUTLOOK**

- **Heat** — inspect a selected-time thermal observation and determine whether the spatial differences are meaningful enough to support a zone ordering.
- **Context** — inspect variables such as tree canopy, median household income and older housing without combining them into a synthetic vulnerability score.
- **Action** — surface a small number of evidence-linked checks, with a reason for why each one is shown.
- **Outlook** — identify what should be observed or compared next.

The central design choice is deliberate: **a map is not automatically a ranking**. A zone that is a fraction of a degree warmer than its neighbour is not presented as a priority area unless the analysis supports that interpretation.

## Cities and published evidence

The current product supports four comparison geographies, each with 25 zones:

| City | Published selected-time comparison | Local context |
| --- | --- | --- |
| Phoenix, AZ | 8 Jul 2024 · 15:00 local | Yes |
| Las Vegas, NV | 8 Jul 2024 · 15:00 local | Yes |
| Tucson, AZ | 8 Jul 2024 · 15:00 local | Yes |
| Los Angeles, CA | 8 Jul 2024 · 15:00 local | Yes |

The four-city comparison therefore covers **100 zones on one shared absolute temperature scale**.

Phoenix also has a deeper local evidence package. It includes a matched 03:00 reference panel for the 30 June–30 July window in 2022, 2023 and 2024: **93 matched timestamps × 25 zones = 2,325 zone observations**. Across the Phoenix analysis geography, the matched-window mean at 03:00 was 32.83 °C in 2022, 33.90 °C in 2023 and 34.35 °C in 2024.

That historical comparison is intentionally described as **matched nighttime conditions across years**. It is not an overnight cooling curve, a measure of overnight recovery, or a climate-trend estimate.

## The two thermal signals

HVA-Signal keeps two different questions separate.

### Selected-time thermal snapshot

A selected observation is shown as **absolute zone-mean temperature in °C**. The thermal map uses a fixed shared display scale; it is not stretched to the minimum and maximum of the visible city.

This layer is descriptive. It is not a probability, risk score, anomaly score or priority ranking.

### Nighttime historical position

For the Phoenix reference analysis, each zone can be compared with its own matched-time historical distribution at 03:00. This produces `q_A`, a historical-position measure.

`q_A` answers **“where does this observation sit relative to this zone's own matched history?”** It does not answer **“which zone is absolutely hottest?”**

The spatial-differentiation policy then checks whether the field contains enough separation to support an ordering. When it does not, ranking colours are withheld rather than replaced with a weak guess.

The current frozen policy is versioned as:

`PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10`

That threshold is a product decision policy, not a health-outcome calibration. Sensitivity analysis and alternative full-field spread statistics are part of the next methodological iteration rather than claims made by this version.

## Architecture

```mermaid
flowchart LR
    UI[React + TypeScript\nMapLibre workspace]
    API[FastAPI API]
    CITY[City + geometry catalog]
    FG[FortyGuard Type-1 TCM]
    CACHE[Cache + replay evidence]
    AGG[Zone aggregation]
    THERMAL[Selected-time absolute °C]
    HIST[Matched-time historical position]
    D8[Spatial differentiation gate]
    CTX[ACS + canopy context]
    ACTION[Evidence-linked actions]

    UI --> API
    API --> CITY
    API --> CACHE
    FG --> CACHE
    CACHE --> AGG
    CITY --> AGG
    AGG --> THERMAL
    AGG --> HIST
    HIST --> D8
    THERMAL --> UI
    D8 --> UI
    CTX --> UI
    THERMAL --> ACTION
    D8 --> ACTION
    CTX --> ACTION
    ACTION --> UI
```

The frontend is a React/TypeScript application with MapLibre for geographic interaction. The API is FastAPI. Published observations and their provenance are served through replay/cache paths so the default public experience is reproducible and does not create an uncontrolled vendor request simply because somebody opens the page.

## FortyGuard usage

FortyGuard is the primary thermal-data provider. HVA-Signal uses **Type-1 TCM heatmaps at 100 m** for selected-time urban temperature observations. Vendor tiles are aggregated into the fixed analysis zones before they reach the decision layer.

The integration is deliberately cache-first. Repeating an identical request should reuse the existing evidence rather than submit the same paid request again.

The public product also exposes one narrowly scoped Live path:

`POST /api/v1/live/selected-time`

Live is limited to the four supported city geographies. The browser sends only a supported city and city-local hourly timestamp; AOI geometry, resolution, metric, provider configuration and credentials remain server-owned. A successful result is aggregated into the same 25-zone geography used by the map. The general arbitrary-vendor path remains refused by design.

Published mode remains replay-backed. A paid/provider request can occur only when a user explicitly chooses **Live** and runs a supported selected-time observation; opening or navigating the product does not trigger one.

## Context data

Context is kept separate from thermal evidence. The current product uses:

- **US Census Bureau TIGER/Line 2025** for tract geometry;
- **ACS 2020–2024 5-year estimates** for socioeconomic and housing context;
- **2021 national tree-canopy context** for the cross-city comparison;
- **Phoenix-specific canopy evidence** where the deeper local Phoenix contract supports it.

These context layers are structural reference datasets, not live measurements. When a selected-time Live thermal observation is requested, HVA-Signal joins the thermal result and the context values by the same Census tract while preserving each dataset's own reference date. It does **not** pretend that 2021 canopy or ACS 2020–2024 estimates were measured at the requested thermal timestamp.

Context layers may use a relative colour range within the displayed comparison geography. The legend labels that behaviour explicitly and preserves the underlying numeric values. Context variables are not collapsed into a composite vulnerability score.

## Interpretation boundaries

The product intentionally does **not** claim:

- individual heat harm or medical risk;
- a calibrated probability of harm;
- WBGT where it has not been validated;
- overnight recovery from isolated 03:00 observations;
- a climate trend from the three matched summer windows;
- intervention effectiveness;
- a forecast when the provider contract does not support one;
- causation from cross-city or canopy correlations.

Missing evidence remains unknown. It is not converted to zero or a favourable assumption.

## Data flow and provenance

A simplified request path is:

```text
city + observation
        │
        ▼
fixed server-owned geography
        │
        ▼
FortyGuard observation / verified cache
        │
        ▼
zone aggregation
        │
        ├──► absolute selected-time °C
        │
        └──► historical-position analysis where a valid reference exists
                    │
                    ▼
            spatial differentiation gate
                    │
                    ▼
thermal finding + context + evidence-linked next checks
```

Cross-city acquisitions retain provider activity/provenance records and request fingerprints. The Phoenix historical reference panel is versioned and checksum-protected; its matched-time interpretation is deliberately narrower than a continuous overnight series.

## Repository layout

```text
apps/
  api/                  FastAPI service, analytics, provider integration
  web/                  React/TypeScript product UI
data/
  acquisitions/         acquisition records and reproducible evidence
  context/              contextual datasets and contracts
  phoenix/              Phoenix reference evidence
  cross-city/           cross-city comparison packages
docs/                   analytical, release, provenance and internal notes
infra/                   Render deployment blueprint
scripts/                 validation and operational utilities
```

The deployed product UI lives under `apps/web/src/features/workspace/`. Internal implementation plans and operational notes live under `docs/`, not at the repository root.

## Run locally

### API

Python 3.12 or newer is required.

```bash
cd apps/api
python -m venv .venv
# activate the virtual environment for your shell
pip install -e ".[dev]"
DATA_MODE=replay uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell, set replay mode with:

```powershell
$env:DATA_MODE="replay"
uvicorn app.main:app --reload --port 8000
```

### Web

Node 22 is used in CI.

```bash
cd apps/web
npm ci
npm run dev
```

The production build is:

```bash
npm run build
```

## Tests

The CI pipeline runs the API suite, web unit tests, the production web build and Playwright end-to-end checks.

```bash
# API
cd apps/api
pytest

# Web
cd apps/web
npm test
npm run build

# End-to-end (with API and web preview running)
cd ../..
npm ci
npm run test:e2e
```

Regression coverage includes the frozen Phoenix Decision 8 historical panel, fail-closed vendor behaviour, four-city geometry/data joins, cross-city comparison contracts and browser-level product flows.

## Deployment

Render deployment is defined in `infra/render.yaml` (with the required root blueprint copy where applicable). The public services are:

- Web: https://urban-thermal-web.onrender.com
- API: https://urban-thermal-api.onrender.com

Published mode is replay-backed and deterministic. Bounded selected-time Live is opt-in and limited to the four supported server-owned city geographies; general arbitrary vendor access remains disabled.

## What we are shipping next

The near-term product direction is to make the same evidence discipline useful over more observations, not to add a synthetic score.

1. **Matched observed instants across cities** — compare the same local observation times across all four city geographies once the evidence package is acquired and validated.
2. **Live hardening and monitoring** — continue validating cache reuse, spend controls and clear provenance for bounded selected-time observations without opening a general arbitrary-vendor path.
3. **Stronger event-level thermal context** — make severe or persistent matched-time conditions clear without confusing event severity with spatial differentiation.
4. **Method validation** — run sensitivity analysis on the current spatial-differentiation threshold and compare it with robust full-field alternatives before changing the frozen V1 policy.
5. **More operational context** — add preparedness/resource evidence only where source coverage and provenance support it.

The principle stays the same: **show what the evidence supports, and make the absence of defensible spatial differentiation explicit rather than inventing precision.**

## License

See [LICENSE](LICENSE).
