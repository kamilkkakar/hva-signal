# Zero-context testing notes

Audience: a reviewer who has not read the repo and does not know Signal names.

## First ten seconds

1. The page title is a product name plus **Decision**, not an internal job id.
2. Eight questions are readable in plain language.
3. The ledger states what happened, relative to what, over what period, why it matters, and a direction — even if each cell says the series is not bound.
4. The first question explains the 25 analysis areas once.

## Infer without a briefing

| Must infer | Where it lives |
|---|---|
| Question | Large heading + left spine |
| Period | Ledger + every chart chrome row |
| Baseline | Ledger “Relative to” + chart “Baseline” |
| Result | Story card magnitude (pending until bound) |
| Direction | Right rail + ledger last cell |

## Pass / fail probes

- Can a reviewer find “at this time” without seeing a live-now claim? **Pass if** chips say dated window / selected time.
- Can they name the spatial unit? **Pass if** they say “analysis area,” not a tract code.
- Do they invent a ranking from empty charts? **Fail if** empty plots look like a zero series. Empty plots have no polyline and a pending stamp.
- After clicking a cell, do charts mention that analysis area? **Pass if** the selected label appears in chart copy.

## Not in scope for this surface

Teaching internal indices, treatment success, or a scored vulnerability model.
