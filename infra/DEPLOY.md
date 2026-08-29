# Production deploy (Render Free validation, then optional Starter)

HVA-Signal (3K Labs) public hosting is applied from a HUMAN-controlled Render workspace.

## Encoded topology

- `infra/render.yaml` and root `render.yaml`: two **Free** Docker web services
  (`urban-thermal-web`, `urban-thermal-api`) for $0 public validation.
- Free services sleep when idle. That is expected. Do not add keepalive jobs.
- Free cannot receive private-network `hostport` traffic. Web nginx proxies
  same-origin `/api`, `/health`, and `/ready` to the API **public HTTPS** URL
  (`RENDER_EXTERNAL_URL`), not to a private hostport.
- `DATA_MODE=replay` on the API. `FORTYGUARD_API_KEY` is dashboard-only
  (`sync: false`) and must stay empty for replay validation.
- No deploy hook, cron, or health check POSTs `/v1/heatmap`.
- No persistent disk.

Free is validation infrastructure. It is not assumed suitable as the final
judged-demo plan. After validation, HUMAN may upgrade services to Starter.

## Human steps (Free validation)

1. In workspace **3K-Labs**, apply the Blueprint from private `main`.
2. When prompted, leave `FORTYGUARD_API_KEY` empty.
3. Confirm both services are Free. Confirm `DATA_MODE=replay`.
4. Copy the assigned public URLs (`*.onrender.com`). Do not invent hostnames.
5. First request may wait for both services to wake.
6. Verify with GET only (never POST `/v1/heatmap`):

   ```bash
   WEB_PUBLIC_URL='https://<web>' API_PUBLIC_URL='https://<api>' bash scripts/verify-public-deploy.sh
   ```

Then exercise default `2022-07-01 03:00` AOI-local replay from the UI.

If a Free build fails on memory/CPU, report a Free-tier resource finding. Do
not strip frozen runtime evidence to fit Free.

## Local production images

```bash
docker compose -f infra/docker-compose.yml up --build
```

Local compose uses `API_UPSTREAM=api:8000` (HTTP). Render Free injects
`https://<api-host>`. The web entrypoint accepts both forms.
