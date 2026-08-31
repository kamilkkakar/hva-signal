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
| `phoenix-landing-1440x900.png` | 1440×900 | First-read landing | desktop | `754e1480606a4c4b859b9cfe2d783b04ce722612f42a971c9b729a35a0e80a60` |
| `phoenix-thermal-map.png` | 1440×900 | Thermal map stage | desktop | `327da2cfc6dc38390f940850ad5ac80efa736d7f434f0275ad5d0ed7553042db` |
| `phoenix-canopy-map.png` | 1440×900 | Tree canopy map mode | desktop | `e7e58cb99fd9a896e4cbb373e367655816c4ef9c95ad1e1d91c17ffda65281d9` |
| `phoenix-income-map.png` | 1440×900 | Income map mode | desktop | `ead8bc3ba21697f93862d932d2616e3d0069b058a5f9d2fbcf4d7c5bd81b1f12` |
| `phoenix-older-housing-map.png` | 1440×900 | Older housing map mode | desktop | `e123adf80685faaf7d7678f79f8e48e16a16e6b3ed3978f01bfc0b5ddf1cf8ec` |
| `phoenix-matched-night.png` | 1440×900 | Matched nighttime chart | desktop | `716bda0a8834c113df8575ebc3988c1184d5a6e25123ca08a246d22984846f58` |
| `phoenix-observed-instants.png` | 1440×900 | Observed instants chart | desktop | `8465a9e41e1cdc8162a1b7b1a72cd88129ab1a2b620438c231649e2fae9fed90` |
| `phoenix-context.png` | 1440×900 | Local context panel | desktop | `8e323265eccb1b52008177e652b37dd0873c32128fcf528f1601f7901c1506e1` |
| `phoenix-preparedness.png` | 1440×900 | Preparedness panel | desktop | `25461b547f330a74593ee69b25be4fab615e66fa26f0ab1c4fdc114b0d0dcfb4` |
| `phoenix-direction.png` | 1440×900 | Direction / verify-next | desktop | `c9525e3a12a7ec1810d276bc39c872d8aff2f342c8e093b88a218e04667b1cac` |
| `phoenix-method-provenance.png` | 1440×900 | Method / provenance disclosure | desktop | `8606d494b6b54594bd7694825da4a31250561f23e452cd3c6616e7365651d317` |
| `phoenix-1024.png` | 1024×768 | Laptop first-read | desktop | `a0b540625ef3f1e32ed17b430e49f4450b54e90c44a1ab2351757c1b882a7fa4` |
| `phoenix-mobile-390x844.png` | 390×844 | Mobile first-read + compact nav | mobile | `6d1fa3af3f23a8fd4aab67408d87d35a5b11c2481d8b61a53bf1d6b7a4b892fe` |
