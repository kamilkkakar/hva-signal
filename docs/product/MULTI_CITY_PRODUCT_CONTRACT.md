# Multi-City Product Contract

Status: additive to the frozen Phoenix baseline.

## Scope

The Cross-City Explorer is a public comparison surface appended after the Phoenix local story in the judge experience shell. It does not replace the Phoenix hero, map, temporal charts, context, preparedness, or verify-next flow.

## City access

- Public city access is a curated allowlist only: Phoenix, AZ; Las Vegas, NV; Tucson, AZ; Los Angeles, CA.
- Live city search stays off by default.
- Place-search flags remain off unless a separate product decision enables them.

## Comparison rules

- Fetch comparison data from `GET /api/v1/cross-city/metrics`.
- Default encodings are fixed for v1: X = selected-time temperature (deg C), Y = median household income, Size = population, Fill = tree canopy, Outline = city color.
- Bubble area must remain proportional to population, which means radius scales with the square root of population.
- Tree canopy fill uses one global scale across all supported cities in the payload.
- Missing tree canopy stays visible with a hollow or hatched treatment.
- Missing X or Y values keep the area off the plot and must be disclosed as an omitted count.
- Comparison clock disclosure is fixed to the same local date and time: `2024-07-08 15:00`.

## Language rules

- Keep copy descriptive and non-causal.
- Do not say a metric causes heat, drives heat, proves need, or justifies a city judgment.
- Do not convert cross-city comparison into a need ranking or intervention ranking.

## Capability rules

- Phoenix may link back to the published local area analysis already present in the shell.
- Non-Phoenix cities stay clearly labeled as Level-1 comparison only until a deeper local workflow is published.
