# Visual comparison gate notes (Part 38)

Compared guided captures (Playwright production build) vs known-good `f664f4e` approved Phoenix screenshots.

Artifacts (local only, not for merge as approved contract):
- `docs/release/visual-gate/guided/`
- `docs/release/visual-gate/known-good/`

Approved contract PNGs under `docs/judge-experience/screenshots/` were restored to known-good after capture.

## Explicit answers (1–10)

1. **First-read text materially reduced?** **NO / mixed.** Downstream sections are shorter, but first viewport gains a full Decision Brief (pattern + chips + 3 bullet columns). Net first-read text load is **higher**.
2. **Visuals at least as prominent?** **WORSE on first viewport.** Large °C metrics and map are pushed below the Decision Brief. Known-good led with 33.7 °C / +1.54 °C.
3. **Main finding easier?** **BETTER.** Pattern title + summary are elevated immediately.
4. **Suggested direction easier to find?** **BETTER.** Brief “Suggested direction” + guided links.
5. **Phoenix still coherent?** **SAME / BETTER.** Same editorial civic language; no retheme.
6. **Cross-City still coherent?** **SAME.** Explorer preserved; guided interpretation line only.
7. **Decision Brief improves comprehension?** **YES for framing**, but at the cost of visual-first first read.
8. **Page less busy?** **WORSE on first read** (busy brief grid); **BETTER** in hero (duplicate pattern removed) and matched/context compression.
9. **Mobile easier to scan?** **WORSE.** 390×844 first screen is Brief text; known-good showed glanceable °C cards.
10. **Strong known-good aspect lost?** **YES.** Glanceable thermal numbers + pattern-after-metrics first composition; map proximity to first read.

## Gate decision

**FAIL for first-read Decision Brief placement / density.**

Do **not** merge the guided first-read visual change as-is. Keep known-good presentation for the first viewport until Brief is refined (e.g. lean pattern+chips only above metrics, or Brief after hero metrics/map).

Compressed matched/context/prep language and bounded-live API can remain on the feature branch for a follow-up visual fix, but **release merge/push/deploy is STOPPED**.
