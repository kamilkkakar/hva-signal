# Pre-live guided UI rollback

Recorded at the start of the HVA-Signal guided-live finish sprint (LEAD-RC).  
Purpose: recover the human-approved production UI without force-push or history rewrite.

## Known-good baseline

| Field | Value |
|-------|-------|
| Known-good SHA | `f664f4e2a087044c34dc4d1c7d64a1701d543a73` |
| Commit subject | Stabilize area selection ownership and ship AREA_IDENTITY_V1 geographic labels. |
| `origin/main` at checkpoint | **Equals** known-good SHA (verified after `git fetch origin main`) |
| Local safety ref | `safety/pre-live-guided-ui-f664f4e` |
| Safety ref points to | `f664f4e2a087044c34dc4d1c7d64a1701d543a73` (exact) |

### Safety ref rules

- **DO NOT** move, rewrite, delete, force-update, or reuse `safety/pre-live-guided-ui-f664f4e`.
- Verify anytime: `git rev-parse safety/pre-live-guided-ui-f664f4e`  
  Expected: `f664f4e2a087044c34dc4d1c7d64a1701d543a73`
- This ref is local. It is the recoverable pointer if main or feature work diverges.

### Feature work location

| Item | Value |
|------|-------|
| Feature branch | `feat/guided-live-finish` |
| Dedicated worktree | `F:\cursor\hackathon-guided-live-finish` |
| Base | Known-good SHA above |
| Untouched | Main worktree, `feat/multicity-explorer` worktree, Phoenix safety refs, other branches/worktrees |

All guided-live finish work happens in the dedicated worktree until the release gate passes.

## Public URLs (production)

| Service | URL | Checkpoint observation |
|---------|-----|------------------------|
| Web | https://urban-thermal-web.onrender.com | HTTP 200; HTML shell loads; asset `index-DptUEsko.js` / `index-CM8-7nR2.css` |
| API | https://urban-thermal-api.onrender.com | `/health` → `{"status":"ok"}`; `/ready` → `{"status":"ready","data_mode":"replay"}` |

Deployed commit SHA is **not** exposed by public API/web responses. At checkpoint, `origin/main` equals known-good; treat production as that baseline unless Render dashboard shows otherwise.

## Render services (blueprint)

Canonical blueprint: `infra/render.yaml` (byte-identical root `render.yaml`).

| Service name | Role | Plan (blueprint) | Health path |
|--------------|------|------------------|-------------|
| `urban-thermal-api` | FastAPI Docker | free | `/health` |
| `urban-thermal-web` | Vite static via Docker/nginx | free | `/` |

### Replay / live config at checkpoint (observable + blueprint)

| Gate | Checkpoint value | Notes |
|------|------------------|-------|
| `DATA_MODE` | `replay` (from `/ready`) | Public path is replay-first |
| `HOSTED_LIVE_ENABLED` | `false` (blueprint) | Hosted live off |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` (blueprint) | Real vendor off |
| `DEMO_ALLOWANCE_ENABLED` | `false` (blueprint) | Allowance closed |
| `DEMO_ALLOWANCE_MAX_TOTAL_UNITS` | `0` (blueprint) | No spend units |
| `FORTYGUARD_API_KEY` | sync:false on API only | Never on web; never print value |
| Public cities | Phoenix, Las Vegas, Tucson, Los Angeles | Via `GET /api/v1/cities` |

Catalog may report `type1_live: READY_FOR_ACQUISITION` as geography readiness metadata. That does **not** mean hosted live acquisition is enabled on the public path.

## Public / vendor state summary

- Default product: accountless, **replay**, cache/fixture reads.
- FortyGuard credentials (if configured) belong only on **`urban-thermal-api`**.
- Web must never receive `FORTYGUARD_API_KEY` or server live/allowance gates.
- Current production UI at known-good is the **human-approved fallback**.

## Rollback procedure (normal revert / forward fix — NO force push)

Prefer restoring known-good behavior with normal git history.

### A. Feature branch only (before merge)

```bash
cd F:\cursor\hackathon-guided-live-finish
git checkout feat/guided-live-finish
git reset --hard safety/pre-live-guided-ui-f664f4e
# or: git revert <bad-commits>   # preferred if branch already pushed/shared
```

Do **not** delete or move the safety ref.

### B. After merge to `main` (preferred)

```bash
git checkout main
git pull origin main
git revert <merge-or-bad-commit-sha(s)>   # creates forward commit(s)
git push origin main                     # normal push only — NO --force
```

Then redeploy Render from the reverted `main` tip (or pin deploy to known-good SHA in the Render dashboard without rewriting git history).

### C. Emergency: redeploy known-good without rewriting remote history

1. Confirm local: `git rev-parse safety/pre-live-guided-ui-f664f4e`  
   → `f664f4e2a087044c34dc4d1c7d64a1701d543a73`
2. In Render: deploy **`urban-thermal-api`** and **`urban-thermal-web`** from commit `f664f4e2a087044c34dc4d1c7d64a1701d543a73` (or from a forward commit that restores that tree).
3. Smoke:
   - Web: https://urban-thermal-web.onrender.com → 200
   - API: https://urban-thermal-api.onrender.com/ready → `data_mode":"replay"`
   - Phoenix demo path + Cross-City still load
4. Keep live/vendor flags fail-closed unless an explicit post-rollback release decision says otherwise.

### Hard stops — when to roll back

Stop and restore known-good if finish work causes regression in:

- Phoenix demo / Cross-City
- Area selection (`selectedAreaId` SSOT) / `AREA_IDENTITY_V1`
- Mobile / a11y / core UX comprehension
- Live/secret handling (key leakage, unintended paid calls)
- Deploy / smoke failure

### Forbidden

- Force push to `main` / `master`
- Rewriting published `main` history
- Moving or deleting `safety/pre-live-guided-ui-f664f4e`
- Printing or committing FortyGuard API keys

## Paid call rule (sprint)

Maximum **1** new FortyGuard Type-1 request this sprint. Prefer mock/cache. Validate cache-hit path = **0** vendor calls before any paid call.

## Checkpoint verification log

| Check | Result |
|-------|--------|
| Repo | `F:\cursor\hackathon-multicity-explorer` → origin `https://github.com/kamilkkakar/hva-signal` |
| SHA exists locally | Yes (`commit`) |
| `origin/main` == known-good | Yes |
| Safety ref created | Yes |
| `git rev-parse safety/pre-live-guided-ui-f664f4e` | `f664f4e2a087044c34dc4d1c7d64a1701d543a73` |
| Worktree | `F:\cursor\hackathon-guided-live-finish` @ `feat/guided-live-finish` |
| Web 200 / API ready replay | Yes |
