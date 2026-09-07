# Playwright end-to-end tests

Smoke tests live in `health.spec.ts`. With externally started servers in CI, they expect:

- Web preview at `WEB_BASE_URL` (default `http://127.0.0.1:4173`)
- API at `API_BASE_URL` (default `http://127.0.0.1:8000`) with `DATA_MODE=replay`

Local runs start isolated API and preview servers on ports 18031 and 14191 through `playwright.config.ts` (`PLAYWRIGHT_API_PORT` and `PLAYWRIGHT_WEB_PORT` override these):

```bash
cd apps/web && npm ci && npm run build
cd ../.. && npm ci && npx playwright install chromium
npm run test:e2e
```

CI installs Chromium with `npx playwright install chromium --with-deps` and starts servers explicitly.
