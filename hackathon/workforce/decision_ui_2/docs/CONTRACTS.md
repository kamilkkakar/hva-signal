# Typed contracts

All public temporal fields use `BoundField<T>`:

- `pending_temporal_program` — value is `null`, bind note required
- `unavailable` — value is `null`, reason required
- `ready` — value present (only after a real contract binds)

## Public factory

`src/data/publicSurface.ts` is the only data module the production route may use. Every story magnitude, chart series, and map fill is pending.

## Test-only fixtures

| File | Mark | Allowed importers |
|---|---|---|
| `src/fixtures/TEST_ONLY.ts` | `TEST_ONLY` | tests only |
| `src/fixtures/story.fixture.ts` | `__testOnly` | tests only |
| `src/fixtures/temporal.fixture.ts` | `__testOnly` | tests only |
| `src/fixtures/areas.fixture.ts` | `TEST-ONLY-` GEOID prefix | tests only |

`src/data/isolation.test.ts` fails if production modules import fixtures.

## Chart chrome (required)

Every temporal visual must carry: **unit**, **period**, **baseline**, **coverage**, **source**.

Unlabeled sparklines are not allowed.

## Map modes

Selected time, Daily profile summary, Summer mean, Seasonal difference, Year-over-year, Persistence, Intervention change, Vulnerability context.

Each mode carries legend, unit, period, baseline. Fills stay pending until a layer binds.

## Intentionally empty

No invented °C series, no live clock, no chance-of-harm number, no wet-bulb globe number, no accumulated-exposure number, no treatment-success number.
