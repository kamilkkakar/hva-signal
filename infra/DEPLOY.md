# Deployment

The Render Blueprint is `infra/render.yaml`; root `render.yaml` must match it.
Both services use Free compute and may take about a minute to wake after inactivity.
The web proxy connects to the API's public HTTPS URL. Published analysis uses
`DATA_MODE=replay`; the bounded selected-time endpoint reads its FortyGuard
credential from the server environment.

## Shared acquisition storage

This capability is off by default and does not provision infrastructure.
Use PostgreSQL 16+ with a direct or session-pooled connection. Transaction
pooling is unsupported because acquisition ownership uses session locks.

Set these server-only values on every participating API instance:

- `ACQUISITION_DATABASE_URL`: database connection string; keep it secret.
- `ACQUISITION_ACCOUNT_SCOPE`: stable account label, default `primary`.
- `SHARED_ACQUISITION_ENABLED=true`.
- The same `APP_ENV`, `FORTYGUARD_BASE_URL` and `BOUNDED_SELECTED_TIME_DAILY_LIMIT`.

Before enabling shared acquisition, initialize the database from `apps/api`:

```bash
python -m app.core.postgres_acquisition --migrate
```

Pause new live submissions during rollout; drain existing calls and update all
instances together. Preserve existing vendor caches. The database cannot recover
legacy purchases that were never recorded in it; reconcile these before batch
acquisition or replacing the old runtime.

New acquisitions commit reservations before submission and activity IDs before
polling. Completed raw responses remain in PostgreSQL and rebuild local caches.
Transient polling failures resume the saved activity on the next matching request.
An uncertain submission without an activity ID requires reconciliation; it is
never automatically repurchased. The daily limit counts reserved POST attempts,
not vendor credits. Operational refreshes retain each completed generation.

Enable database backups and test restoration before unattended production use.
If storage fails, new acquisition fails closed. Rollback should disable the live
endpoint while preserving the database; do not switch to process-local purchasing.
This release does not add a background worker or automated unknown-ID resolution.

## Checks

```bash
WEB_PUBLIC_URL='https://<web>' API_PUBLIC_URL='https://<api>' bash scripts/verify-public-deploy.sh
```

For database integration tests, set `HVA_TEST_POSTGRES_DSN` to a disposable test
database and run `cd apps/api && pytest tests/integration/test_postgres_acquisition.py`.
CI provisions PostgreSQL automatically. Local Docker setup:

```bash
docker compose -f infra/docker-compose.yml up --build
```
