# Cross-City Explorer

## Purpose

Cross-City Explorer extends the judge experience with a compact comparison view across four curated cities while preserving Phoenix as the published local analysis baseline.

## What it shows

- Selected-time temperature on the X axis
- Median household income on the Y axis
- Population through bubble area
- Tree canopy through fill
- City identity through outline color

## Interaction

- A curated city selector sets the focus city for the section.
- The city legend supports toggle, isolate, and show-all actions.
- Hover or focus reveals tooltip details for city, area label, values, and missing-data disclosures.
- The Open area analysis control routes Phoenix back to the local story and keeps other cities in Level-1 comparison mode.

## Guardrails

- No live place search
- No causal claims
- No intervention ranking
- No Phoenix screenshot replacement
- Graceful empty or error state when the comparison API is unavailable
