# HVA-Signal Decision UI 2.0

Question-first decision surface for HVA-Signal. **Frontend only.** This package does not modify core analytics, does not call FortyGuard, and does not invent temporal values.

Workforce output path:

`hackathon/workforce/decision_ui_2/`

Base: `integration/judge-ready-product` @ `103158ca2249a10c10ab4556387c26276270fb84`

## Design rule

**DATA → MEANING → DIRECTION**

Static copy explains once. Dynamic data tells the story. Until the temporal program binds real contracts, the public face stays **pending**.

Every result answers:

1. What happened?
2. Relative to what?
3. Over what period?
4. Why does it matter?
5. What direction does it suggest?

## Run

```powershell
cd hackathon/workforce/decision_ui_2
npm install
npm run dev
```

Open `http://127.0.0.1:5174`

## Test

```powershell
npm test
npx playwright install chromium
npm run test:e2e
```

Screenshots write to `screenshots/`.

## What is published

- Question-first navigation (eight decision questions)
- Evidence ledger (what / relative to / period / why / direction)
- Data story cards with typed pending fields
- Temporal chart frames (unit, period, baseline, coverage, source)
- Schematic 25-area map; click updates supporting charts
- Intervention verification without treatment-success claims
- Vulnerability context without a score
- Action / direction panel
- Method / provenance behind Why?, Method, Evidence

## What is intentionally pending

- All temporal series (24-hour, monthly, seasonal, year-over-year, cumulative anomaly, persistence, treated-vs-comparison)
- Map fills for every mode
- Story-card magnitudes
- Geography GEOID bind
- Live / now readings
- FortyGuard
- Core analytics changes

## Fixtures

`src/fixtures/*.fixture.ts` are **TEST_ONLY**. Production routes (`App.tsx`, `publicSurface.ts`) do not import them. Fixture magnitudes such as `+0.8°C` must not appear on the public face.

## Docs

- `docs/IA.md`
- `docs/CONTRACTS.md`
- `docs/ZERO_CONTEXT_TESTING.md`
- `docs/VISUAL_RED_TEAM.md`
- `docs/HARD_GATES.md`
