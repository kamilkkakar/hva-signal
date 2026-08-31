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
| `phoenix-landing-1440x900.png` | 1440×900 | First-read landing | desktop | `2bd4bd63ea61790a47c74df6e96e9010777d19120f2faf09e92f0ddc8c9eab80` |
| `phoenix-thermal-map.png` | 1440×900 | Thermal map stage | desktop | `02bbec98d3201959ebdd50dcbec3ae937990de2e8798945660f4c07048b0c5e8` |
| `phoenix-canopy-map.png` | 1440×900 | Tree canopy map mode | desktop | `bdd7123056464db57745989feec42a1d012bcaaaff02cd1373bdc949b795c955` |
| `phoenix-income-map.png` | 1440×900 | Income map mode | desktop | `1ab69549088d39dba100893045ffdee0e2c1c5fe1cf020c308481dbd65e69b24` |
| `phoenix-older-housing-map.png` | 1440×900 | Older housing map mode | desktop | `b20d390abfe4bfeb04ad11ba12490e8cc78ab4725fd5cee4fb13e58e4a17eba6` |
| `phoenix-matched-night.png` | 1440×900 | Matched nighttime chart | desktop | `9828ca514a92219527032ff9234b85f814971362b57996a21545973d313fe5c4` |
| `phoenix-observed-instants.png` | 1440×900 | Observed instants chart | desktop | `e1c9811e8ce519f117be24e28dbcf5d07ee8488a7f576d4f9f1d6f0a4ed19ddd` |
| `phoenix-context.png` | 1440×900 | Local context panel | desktop | `a19c60aa18a85d7d17be3e0f7b8f0d53c80ddd3027a5e31c25f8509681b95a62` |
| `phoenix-preparedness.png` | 1440×900 | Preparedness panel | desktop | `bb97be109d611977e086c1c8c7507e7e34475283e283bb872805dfc7145e32ee` |
| `phoenix-direction.png` | 1440×900 | Direction / verify-next | desktop | `2c8d5207cc0323a0a61f49ea9347e9f05ab5ebb9367121d6cae264c1cee37d5b` |
| `phoenix-method-provenance.png` | 1440×900 | Method / provenance disclosure | desktop | `150b06ab492ebb2a69b8c9cc5db2aae2bf4c7c09b0ee2bfd308069ccbefffb30` |
| `phoenix-1024.png` | 1024×768 | Laptop first-read | desktop | `92821e12cb4db3671e228257d06bb83c8082c0d0deb005e98b721327c92049c1` |
| `phoenix-mobile-390x844.png` | 390×844 | Mobile first-read + compact nav | mobile | `d70bf3c627434c104a0bb7b0fecc4fd94988573ba386ec2886c45f70f92efed4` |
