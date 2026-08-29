# Production deploy (Render Starter, replay-only)

HVA-Signal (3K Labs) public always-on hosting is **not** created by this repository alone. A human owner
must connect a Git remote, apply the Blueprint, and accept Render billing.

## What this repo encodes

- `infra/render.yaml` and root `render.yaml`: two **Starter** (paid, non-sleeping) Docker web services
  (`urban-thermal-web`, `urban-thermal-api`). Do **not** use Render Free as the judges URL
  (spin-down after 15 minutes idle; Free services cannot receive private-network requests).
- `DATA_MODE=replay` on the API. `FORTYGUARD_API_KEY` is dashboard-only (`sync: false`).
- Frontend uses relative `/api`, `/health`, and `/ready`. nginx proxies those to the API.
- No deploy hook, cron, or health check POSTs `/v1/heatmap`.

## Human steps (billing and secrets)

1. Create a GitHub (or GitLab/Bitbucket) repository and push this product tree.
   This working copy currently has **no git remotes and no commits**.
2. In Render, add a payment method and apply the Blueprint (`render.yaml` or
   `infra/render.yaml`) on a workspace that can create **Starter** web services.
   Applying the Blueprint **incurs Render charges**. Do not use `plan: free`.
3. When prompted, set `FORTYGUARD_API_KEY` in the dashboard. For the replay demo it
   may be left empty. Do not put the key in source.
4. Confirm both services stay on Starter (not Free). Confirm `DATA_MODE=replay`.
5. After the first deploy, copy the public `WEB_PUBLIC_URL` and `API_PUBLIC_URL`
   (`*.onrender.com` unless a custom domain is attached). Custom domains are optional
   and also require human DNS/Render dashboard action.
6. Verify with GET only (never POST `/v1/heatmap`):

   ```bash
   WEB_PUBLIC_URL='https://<web>' API_PUBLIC_URL='https://<api>' bash scripts/verify-public-deploy.sh
   ```

7. In the dashboard, trigger a Manual Deploy (or restart) and re-run the same script.

## Local production images (not Milestone 0 pass)

```bash
docker compose -f infra/docker-compose.yml up --build
```

Then `WEB_PUBLIC_URL=http://127.0.0.1:8080 API_PUBLIC_URL=http://127.0.0.1:8000 bash scripts/verify-public-deploy.sh` (use port **18080** for the web URL if host port 8080 is already bound).

Local compose health/ready is restart evidence only. Milestone 0 still requires
public always-on URLs.
