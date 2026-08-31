# Pre-final HVA product rollback

Recorded at the start of the HVA-Signal final product + live + temporal + outlook pass (LEAD-RC).  
Purpose: recover the protected production baseline without force-push or history rewrite.

## Known-good baseline

| Field | Value |
|-------|-------|
| Known-good SHA | `6bfde4afd081386d16aa900093e251d27a0f312b` |
| Commit subject | Merge branch `feat/final-dynamic-city-workspace` — Playwright test updates for dynamic city workspace |
| `origin/main` at checkpoint | **Equals** known-good SHA (verified after `git fetch origin`) |
| Local safety ref | `safety/pre-final-hva-product-6bfde4a` |
| Safety ref points to | `6bfde4afd081386d16aa900093e251d27a0f312b` (exact) |

### Preserved older safety ref

| Field | Value |
|-------|-------|
| Ref | `safety/pre-live-guided-ui-f664f4e` |
| Points to | `f664f4e2a087044c34dc4d1c7d64a1701d543a73` |
| Rule | **DO NOT** move, rewrite, delete, or reuse |

### Safety ref rules (`safety/pre-final-hva-product-6bfde4a`)

- **DO NOT** move, rewrite, delete, force-update, or reuse this ref.
- Verify anytime: `git rev-parse safety/pre-final-hva-product-6bfde4a`  
  Expected: `6bfde4afd081386d16aa900093e251d27a0f312b`
- This ref is local. It is the recoverable pointer if main or feature work diverges.

### Feature work location

| Item | Value |
|------|-------|
| Feature branch | `feat/final-hva-product-pass` |
| Dedicated worktree | `F:\cursor\hackathon-final-hva-product-pass` |
| Base | Known-good SHA above |
| Untouched | `feat/multicity-explorer` worktree, other worktrees, all safety refs |

All final-product work happens in the dedicated worktree until the release gate passes.

## Public URLs (production)

| Service | URL | Notes |
|---------|-----|-------|
| Web | https://urban-thermal-web.onrender.com | Keep on current release until candidate fully green |
| API | https://urban-thermal-api.onrender.com | Prefer `/ready` → `data_mode: replay` |

### Desired live flags after explicit activation (NOT during UI/dev)

| Gate | Desired |
|------|---------|
| `DATA_MODE` | `replay` |
| `HOSTED_LIVE_ENABLED` | `false` |
| `HOSTED_LIVE_REAL_VENDOR_ENABLED` | `false` (**never** `true`) |
| `BOUNDED_SELECTED_TIME_LIVE_ENABLED` | `true` (only after human activation) |
| Daily limit | `40` |

Keep `BOUNDED_SELECTED_TIME_LIVE_ENABLED` **off** during UI/dev/zero-spend tests.

## Rollback procedure (normal revert / forward fix — NO force push)

### A. Feature branch only (before merge)

```bash
cd F:\cursor\hackathon-final-hva-product-pass
git checkout feat/final-hva-product-pass
git reset --hard safety/pre-final-hva-product-6bfde4a
# or: git revert <bad-commits>   # preferred if branch already pushed/shared
```

Do **not** delete or move the safety ref. Do **not** delete the worktree/branch as cleanup.

### B. After merge to `main` (preferred)

```bash
git checkout main
git pull origin main
git revert <merge-or-bad-commit-sha(s)>   # creates forward commit(s)
git push origin main                     # normal push only — NO --force
```

Then observe Render redeploy from the reverted `main` tip (or pin deploy to known-good SHA in the Render dashboard without rewriting git history).

### C. Emergency: redeploy known-good without rewriting remote history

1. Confirm: `git rev-parse safety/pre-final-hva-product-6bfde4a`  
   → `6bfde4afd081386d16aa900093e251d27a0f312b`
2. In Render: deploy **`urban-thermal-api`** and **`urban-thermal-web`** from that commit (or a forward commit that restores that tree).
3. Smoke:
   - Web: https://urban-thermal-web.onrender.com → 200
   - API: https://urban-thermal-api.onrender.com/ready → `data_mode":"replay"`
   - Explore City + Compare Cities + selected-zone / `selectedAreaId` SSOT still load
4. Keep live/vendor flags fail-closed unless an explicit post-rollback release decision says otherwise.

### Hard stops — when to roll back

Stop and restore known-good if finish work causes regression in:

- Workspace / ExploreCity / CompareCities / ZonePanel / CityControls / map architecture
- `selectedAreaId` SSOT
- Core Playwright shell / product comprehension
- Live/secret handling (key leakage, unintended paid calls, `HOSTED_LIVE_REAL_VENDOR_ENABLED=true`)
- Deploy / smoke failure / core UI lost

### Forbidden

- Force push to `main` / `master`
- Rewriting published `main` history
- Moving or deleting `safety/pre-final-hva-product-6bfde4a` or `safety/pre-live-guided-ui-f664f4e`
- Printing, logging, or committing FortyGuard API keys
- Enabling `HOSTED_LIVE_REAL_VENDOR_ENABLED=true`
- Deleting the feature branch, worktree, or safety refs as “cleanup”

## Paid call rule (this pass)

Maximum **14** new FortyGuard Type-1 requests (12 temporal + up to 2 forecast).  
Sole **ACQUISITION-OWNER** may execute paid calls — no parallel paid execution.  
Persist after each request. No blind retry. Circuit breakers: debit >5000 STOP; wrong geometry/time/metric/coverage STOP; duplicate spend → turn live OFF.

## Checkpoint verification log

| Check | Result |
|-------|--------|
| Repo | `F:\cursor\hackathon-multicity-explorer` → origin `https://github.com/kamilkkakar/hva-signal` |
| SHA exists locally | Yes (`commit`) |
| `origin/main` == known-good | Yes (`6bfde4afd081386d16aa900093e251d27a0f312b`) |
| Safety ref created | Yes |
| `git rev-parse safety/pre-final-hva-product-6bfde4a` | `6bfde4afd081386d16aa900093e251d27a0f312b` |
| Older safety preserved | `safety/pre-live-guided-ui-f664f4e` → `f664f4e2a087044c34dc4d1c7d64a1701d543a73` |
| Worktree | `F:\cursor\hackathon-final-hva-product-pass` @ `feat/final-hva-product-pass` |
