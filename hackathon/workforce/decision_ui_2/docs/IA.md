# Information architecture — question first

Navigation is organized around questions a reviewer can ask without knowing the internals.

Do not organize the primary face around technical nouns.

## Questions

| # | Question | Map mode | Charts |
|---|---|---|---|
| 01 | What is happening at this time? | Selected time | 24-hour curve |
| 02 | Is this unusual for this place? | Selected time | Year-over-year |
| 03 | How did heat change over the day? | Daily profile | 24-hour curve, persistence |
| 04 | How did this month / season behave? | Seasonal difference | Monthly trend, seasonal comparison |
| 05 | Is this area getting warmer or cooler over years? | Year-over-year | Year-over-year, cumulative anomaly |
| 06 | Did conditions improve after an intervention? | Intervention change | Treated vs comparison |
| 07 | Who / what may have less capacity to cope? | Vulnerability context | None (context only) |
| 08 | What does the evidence support doing next? | Selected time | None (direction panel) |

## Spatial language

- **Primary:** Analysis area 1 … Analysis area 25
- **Secondary:** Census tract GEOID (not bound on the public face until geography binds)
- **Explained once:** HVA-Signal divides the selected geography into 25 consistent analysis areas so thermal conditions can be compared across place and time.

## Shell

```
[ Banner: HVA-Signal Decision ]
[ Evidence ledger: What / Relative to / Period / Why / Direction ]
[ Questions | Question canvas + map + charts | Direction ]
[ Method: Why? Method Evidence ]
```

## Signature

The evidence ledger stays visible so a zero-context reviewer always sees the five decision cells, even while temporal series are pending.
