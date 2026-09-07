# HVA-Signal

**Heat, Vulnerability & Action Signal · 3K Labs**

A map-based tool for exploring urban heat evidence and local context.

[Open the app](https://urban-thermal-web.onrender.com) · [API health](https://urban-thermal-api.onrender.com/health)

## Features

- Explore Phoenix, Las Vegas, Tucson and Los Angeles, with 25 analysis zones per city.
- Compare published temperatures on a shared scale and inspect Phoenix's nighttime historical reference.
- View tree canopy, income and housing context alongside thermal observations.
- Request selected-time FortyGuard observations through the opt-in Live mode.

Thermal data comes from FortyGuard; geography and context use Census, ACS and canopy datasets. Published mode uses retained evidence. Live requests use server-held credentials and check the cache before acquisition.

Results describe thermal conditions. They do not establish health-risk probabilities, forecasts or intervention effectiveness. Zone rankings are withheld when the evidence does not support them.

## Run locally

Requires Python 3.12+ and Node.js 22.

API:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
DATA_MODE=replay uvicorn app.main:app --reload --port 8000
```

On Windows, activate `.venv\Scripts\Activate.ps1` and set `$env:DATA_MODE="replay"` before running Uvicorn.

Web, in a second terminal:

```bash
cd apps/web
npm ci
npm run dev
```

## Development

React, TypeScript and MapLibre power the web app; FastAPI serves the API.

- API tests: `cd apps/api && pytest`
- Web tests and build: `cd apps/web && npm test && npm run build`
- Browser tests: [tests/e2e/README.md](tests/e2e/README.md)
- Render deployment: [infra/DEPLOY.md](infra/DEPLOY.md)

## License

See [LICENSE](LICENSE).
