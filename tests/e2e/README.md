# Playwright e2e — Agent J owns this tree.

Smoke tests live in `health.spec.ts`. They expect:

- Web preview at `WEB_BASE_URL` (default `http://127.0.0.1:4173`)
- API at `API_BASE_URL` (default `http://127.0.0.1:8000`) with `DATA_MODE=replay`

Local run (starts API + preview via `playwright.config.ts` webServer):

```bash
cd apps/web && npm ci && npm run build
cd ../.. && npm ci && npx playwright install chromium
npm run test:e2e
```

CI installs browsers via `microsoft/playwright-github-action` and starts servers explicitly.
