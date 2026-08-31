# Approved Phoenix Screenshots

These PNG files are the **approved Phoenix visual reference contract**.  
They document the frozen judge experience after Phase 0 polish. Multi-city visual QA must **not** mix into this folder.

| Field | Value |
|---|---|
| Approved HEAD (design direction) | `6a82515` |
| Capture HEAD | see freeze commit on `feat/judge-experience-overhaul` |
| Capture date | 2026-08-31 |
| Build command | `cd apps/web && npm run build` then Playwright preview via `npx playwright test tests/e2e/judge-experience.spec.ts` |
| Primary viewport | 1440×900 (desktop); 1024×768 (laptop); 390×844 (mobile) |
| Runtime thermal snapshots touched | **NO** |

## Contract statement

These thirteen images are the only approved Phoenix UI visual references under `docs/judge-experience/screenshots/`. Obsolete aliases (`01-…`, `1440x900-…`, TEST_ONLY fixture cards, broken-basemap, API KEY, operator-chrome, bar-chart leftovers) are removed. Do not add exploratory screenshots here.

## Manifest

| File | Viewport | Purpose | Surface | SHA256 |
|---|---|---|---|---|
| `phoenix-landing-1440x900.png` | 1440×900 | First-read landing | desktop | `242b0e92fa8428c3c9dfdf859dd5e505465003d6bf337ff79e7ca6bcd2036e77` |
| `phoenix-thermal-map.png` | 1440×900 | Thermal map stage | desktop | `79cc26e9aec52b1c58fd0063e7d1ee15b40dabfa605c699730423bbbcc261baa` |
| `phoenix-canopy-map.png` | 1440×900 | Tree canopy map mode | desktop | `1b825cd7b8baf495c04ad4958ab226c2f3a27599d6dc64b462e104e730e18ace` |
| `phoenix-income-map.png` | 1440×900 | Income map mode | desktop | `d48a02d8aca931ecc28ee1dd3949233b149f218fe0b17b5ac0988811f3c714e5` |
| `phoenix-older-housing-map.png` | 1440×900 | Older housing map mode | desktop | `62968ddfbc39826f2cc52c1a848374beea18ecdd4f4c96ff83bac52b14cc1bdf` |
| `phoenix-matched-night.png` | 1440×900 | Matched nighttime chart | desktop | `43dacdcfe916f66111d4ea545ce38bee809ec31e9e8373ff15dafdb2e182591d` |
| `phoenix-observed-instants.png` | 1440×900 | Observed instants chart | desktop | `204cbb585a88043ca8e51b5d77bfc9fedb920f2d3b0d86cee5102026d6de72e7` |
| `phoenix-context.png` | 1440×900 | Local context panel | desktop | `c800743409806c91bfc5e75602d05e932d93d181d31f72e4a2cc46e7c86eeae4` |
| `phoenix-preparedness.png` | 1440×900 | Preparedness panel | desktop | `ca5f98708d2f90f7f8c5000da773155c25a0cc29072a38c1fcf107d56b962347` |
| `phoenix-direction.png` | 1440×900 | Direction / verify-next | desktop | `31f36490a418a4a287f83c08243f0a749c9d89b60a79a7d750b2dabcd186b082` |
| `phoenix-method-provenance.png` | 1440×900 | Method / provenance disclosure | desktop | `50f5fc49ba5fdeddea51ab4dd1939a8e06d94d8c74c1f5cc65e80680eac126d6` |
| `phoenix-1024.png` | 1024×768 | Laptop first-read | desktop | `01b285bc294300e60e7a38af8abf137e0af1e717f9dbc3ce10b5d86851f3f01c` |
| `phoenix-mobile-390x844.png` | 390×844 | Mobile first-read + compact nav | mobile | `20d1723d9bc96d1bb0020adebb8559c5231631f951cf6d7973f08653bed0d7f3` |
