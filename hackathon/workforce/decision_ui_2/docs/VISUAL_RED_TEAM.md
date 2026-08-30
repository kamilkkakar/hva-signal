# Visual red-team notes

Reviewed against the hard gates and the “static copy dominates” failure.

## Attacks and responses

| Attack | Finding | Mitigation |
|---|---|---|
| Desktop horizontal scroll | Shell uses `max-width: 100%`, `min-width: 0`, `overflow-x: hidden` on the document. Playwright checks `scrollWidth ≈ clientWidth` at 1440 and 390. | Keep three-column grid only above 1100px. |
| GEOID-first map | Cells are numbered 1–25. Primary label is “Analysis area N”. | GEOID string is null on the public area list. |
| Fake temporal hero number | Public story cards render “Not published”. Isolation test blocks fixture imports. | Fixture `+0.8°C` lives only under `src/fixtures`. |
| Traffic-light risk | Action rail is five text blocks. No red/amber/green score. | Copy forbids “low risk” / “high risk”. |
| Unlabeled sparkline | `ChartFrame` always prints unit, period, baseline, coverage, source. | Pending charts use an empty plotter, not a flat zero line. |
| Hard-coded essay | Body copy is labels + pending stamps. Longer explanation sits behind Why? / Method / Evidence. | Area explanation appears once on question 01. |
| “Current” as live | Chips: “Dated window. Not live.” / “Selected time. Not a live now reading.” | No live poller. |
| Treatment success | Intervention stamp: “Not a treatment result.” | `efficacyClaim: false` on the contract. |
| Vulnerability score | Stamp: “Context only. Not a score.” | Factor list has no numbers. |
| Technical IDs | Question ids are URL-safe slugs in code only. Visible text is the prompt. | Forbidden-token tests on published copy and rendered body. |

## Residual risk

When real series bind, a large magnitude could again dominate the page. Keep the ledger and chrome rows adjacent to the number so comparison context cannot be cropped on a laptop.
