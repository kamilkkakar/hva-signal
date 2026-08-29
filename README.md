# HVA-Signal

**3K Labs**

HVA-Signal — Heat, Vulnerability & Action Signal

HVA-Signal combines thermal evidence with vulnerability and preparedness context to support defensible urban heat decisions. When thermal evidence does not support a defensible spatial ranking, HVA-Signal suppresses the ranking rather than manufacturing one.

This repository contains the runnable product, runtime data, tests, and deployment configuration. Architecture, research, prompts, agent coordination, and secrets live locally under `workforce/` and are not committed.

## Status

Milestone 0 is **blocked** until a verified always-on public deployment exists. Architecture Gate 0 is **not ready for final close**.

HVA-Signal does **not** currently predict individual harm probability, emit a calibrated heat-event probability, prove intervention effectiveness, or validate 100 m localization. `Action` in HVA means decision/action support, not validated intervention efficacy. `q_A` is not a probability.

## Quick start (replay)

```bash
cp .env.example .env
# Backend
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend (Vite dev — http://localhost:5173, proxies /api to :8000)
cd apps/web
npm install
npm run dev
```

Docker Compose serves the production nginx image at **http://localhost:8080** (and **http://localhost:18080** if 8080 is already taken; API on **:8000**; nginx proxies `/api`, `/health`, and `/ready`):

```bash
docker compose -f infra/docker-compose.yml up --build
```

Public always-on hosting (Render Starter, not Free) is a **human** dashboard/billing step. See `infra/DEPLOY.md`. Do not use a sleeping free-tier service as the judges URL.

End-to-end (repo root, API venv installed): `npx playwright install chromium` then `npm run test:e2e`.

## Core rules

- FortyGuard API keys stay on the backend. The frontend never receives them.
- Replay/fixtures are the default for local development and CI (`DATA_MODE=replay`).
- Missing data is unknown, never safe. Insufficient evidence is a valid outcome.
- Do not manufacture thermal ranking when hazard spread is below the configured floor.

## API

- `GET /health`
- `GET /ready`
- `POST /api/v1/analysis/jobs`
- `GET /api/v1/analysis/jobs/{job_id}`

Unknown job IDs return `UNKNOWN_JOB` so the UI can resubmit after a restart.

## Layout

```text
apps/api    FastAPI modular monolith
apps/web    React + TypeScript command center
data/demo   Legally distributable demo datasets
data/phoenix/reference  Frozen Decision 1B runtime panel
infra       Docker / deploy config
scripts     Maintenance and sanitization
tests/e2e   Playwright
```
