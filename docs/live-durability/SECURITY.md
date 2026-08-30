# HVA-SIGNAL — LIVE-J PUBLIC SAFETY / SECURITY

Date: 2026-08-30  
Program: J3/J4 Live Execution & Durability  
Owner: LIVE-J (backend / API / config only)  
Worktree: `F:\cursor\hackathon-live-j` (`feat/live-j-security`)

This document is the SECURITY deliverable for a **safe hosted demo**.  
No FortyGuard calls. No real vendor. Frontend is out of scope.

## Invariants

A **client** (header, query string, JSON/form body, nested objects) can **never** set:

| Category | Examples rejected |
|---|---|
| Allowance cap | `allowance_cap`, `authorized_max_units`, `max_total_acquisition_units`, `demo_allowance_max_total_units` |
| Budget | `budget`, `demo_budget`, `allowance`, `allowance_remaining` |
| Key | `key`, `api_key`, `fortyguard_api_key`, `internal_key`, `Authorization` |
| force_live | `force_live`, `hosted_live_enabled`, `allow_hosted_live_demo`, `demo_allowance_enabled` |
| Operator approval | `operator_approval`, `approved`, `skip_approval`, `spend_authorized` |
| Reservation state | `reservation_id`, `reservation_state`, `reserved`, `consumed_units` |

**Hosted live default: OFF.**  
`hosted_live_enabled=False`, `hosted_live_real_vendor_enabled=False`, `demo_allowance_enabled=False`, cap `0`.

**Operator approval is server-side only.** Default denied.

**Secrets are never logged or returned.** Rejection bodies carry field *names* and categories, never values.

This program **refuses real vendor construction**. The Temporal program owns the one authorized live call.

## Threat mitigations

| Threat | Mitigation |
|---|---|
| Client sets cap / budget / key / force_live / approval / reservation | Canonical denylist + alias fold (kebab, camel, `X-*`). Request models reject. Middleware rejects body, query, and headers with HTTP 422 `CLIENT_FORBIDDEN_FIELD`. |
| Silent ignore of unknown fields on `AnalysisRequest` | Union with `CLIENT_CONTROL_FIELD_NAMES` so these names raise instead of being dropped. |
| Client enables hosted live via header/query/body | `resolve_hosted_live()` deletes client surfaces. Middleware rejects the names. Defaults stay off. `may_construct_real_vendor()` is always `False`. |
| Client self-approves spend | `resolve_operator_approval()` ignores client. Request validation rejects approval names. |
| Client forges reservation state | Names rejected on every public surface. Ledger remains server-owned (LIVE-F). |
| Secret echo in 422 / OpenAPI / `/ready` | Rejection payload is names-only. `/ready` returns `{status, data_mode}` only. Serializer denylist + `strip_secrets_from_public`. |
| Secret in logs | `redact_for_log`, `SecretLogFilter`, known-value scrub. |
| Demo config mistaken for vendor enablement | `acquisition_preference` / `allow_hosted_live_demo` is intent, not a gate. `refuse_real_vendor()` always raises. |
| Rate-limit middleware opt-in used as the only gate | Public-safety middleware is **default ON** and mounted on the app. Rate limits stay a separate opt-in. |

## Operator vs client

| Surface | Who sets it | Client |
|---|---|---|
| `hosted_live_enabled` | Process env / `Settings` | Rejected if sent |
| `hosted_live_real_vendor_enabled` | Process env (still refused here) | Rejected if sent |
| `demo_allowance_*` | Process env | Rejected if sent |
| `operator_approval_enabled` | Process env | Rejected if sent |
| `fortyguard_api_key` | Process env (do not commit) | Rejected if sent; never returned |
| Reservation / ledger | Server | Rejected if sent |
| `HVA_PUBLIC_SAFETY_MIDDLEWARE` | Process env (default on) | Cannot disable |

## Code map

| Module | Role |
|---|---|
| `app/domain/public_safety_fields.py` | Canonical names, aliases, categories |
| `app/core/public_safety.py` | Scan body / query / header; rejection payload |
| `app/core/public_safety_middleware.py` | Always-on ASGI guard |
| `app/core/hosted_live_policy.py` | Hosted live OFF; real vendor refused |
| `app/core/operator_approval.py` | Server-side approval only |
| `app/services/secret_redaction.py` | Log / response redaction |
| `app/core/config.py` | Operator defaults |
| `app/domain/requests.py` | Analysis POST reject list |
| `app/schemas/two_signal_public.py` | Publication POST reject list |
| `app/services/spend_threat_guards.py` | Client flags are not grants |
| `app/core/anonymous_guards.py` | Public serializer denylist |
| `app/services/secret_boundary.py` | Public DTO secret names |
| `app/main.py` | Mounts `PublicSafetyMiddleware` |

## Residual risks

1. **Operator env misconfiguration.** An operator can set `hosted_live_enabled=true`. This program still refuses real vendor construction, but a future merge that honors the flag could spend.
2. **`HVA_PUBLIC_SAFETY_MIDDLEWARE=0`.** Schema-level rejects remain; header/query scanning would stop. Treat disable as an incident.
3. **Non-JSON bodies.** Form-urlencoded is scanned. Arbitrary binary / multipart field names are not walked. Residual bypass if a future route reads multipart control fields.
4. **Unpublished `public_contract.TwoSignalPublicRequest`** still allows `acquisition_preference=allow_hosted_live_demo` as *intent*. It must never be wired as a vendor gate (existing contract test). Published P2 schema rejects the name.
5. **`data_mode=live`** is a fetch-mode enum on legacy analysis, not `force_live`. Spend guards already treat it as non-authorization. Do not confuse the two.
6. **Process memory** still holds `fortyguard_api_key` if the operator set it. Redaction covers logs and responses, not RAM or crash dumps.
7. **Loggers attached before `SecretLogFilter`** can emit secrets if a caller logs settings or headers directly. Call `redact_for_log` at the edge.
8. **Sibling streams** (allowance durability, worker SM, red team) own spend races, exactly-once, and crash recovery. This stream does not claim mathematical exactly-once.
9. **Denylist drift** if a new control field is added without updating `public_safety_fields.py`.
10. **CORS `allow_headers=["*"]`** lets browsers *send* custom headers; this middleware rejects them. The packets still reach the process.

## Tests

`apps/api/tests/unit/test_public_safety_live_j.py` plus additive cases in `test_analysis_request_rejects_signal_b.py`.

## Honest verdict

Public control-plane injection of cap / budget / key / force_live / approval / reservation is rejected on the hosted API path. Hosted live stays **OFF** unless an operator changes process settings, and even then this program will not construct a live vendor. Residual risk is operator error, future wiring of the unpublished preference, and non-JSON body parsers — not a client checkbox.
