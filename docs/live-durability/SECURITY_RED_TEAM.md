# HVA-SIGNAL — SECURITY / RED TEAM (LIVE-N)

**Date:** 30 August 2026  
**Worktree:** `f:\cursor\hackathon-live-n`  
**Branch:** `feat/live-n-red-team` (kept; not pushed)  
**Vendor:** none. No FortyGuard calls. No real network to a live provider.  
**Exactly-once:** **not claimed.** Best achievable posture is *at-most-one-submit* plus activity-id reconcile. A vendor that is not idempotent can still double-charge if a second submit is ever issued.

This program does not own Temporal analytics or frontend. The Temporal program owns the one authorized live call. LIVE-N attacks the *safety envelope* that must keep hosted live off and un-forceable from the client.

---

## 1. Scope

Adversarial review and executable tests for:

| Class | Attack |
|---|---|
| Privilege injection | Client sets allowance cap, budget, key, `force_live`, operator approval, reservation state |
| Hosted-live enable | Client turns hosted live on via body / query / header / nested extras |
| Cache / identity | Cache-bust, replay, forged `activity_id`, stolen reservation |
| Spend | Double-consume, paid retry after consume / post-submit |
| Recovery | `UNKNOWN_VENDOR_STATE` forced resubmit |

---

## 2. What was broken (failing), then fixed

These holes were real on `ee56131` before LIVE-N. Tests were written to fail first; the following changes made them pass.

### 2.1 Nested `scenario` extras (`extra="allow"`)

`ScenarioRequest` accepted arbitrary extras. A client could POST:

```json
{ "area_id": "phoenix-demo", "...": "...", "scenario": { "force_live": true, "key": "x", "allowance": 99 } }
```

Pydantic stored the extras. `create_analysis_job` echoed `job.request` on GET. Privilege fields survived into stored job documents.

**Fix:** `ScenarioRequest` now rejects the same unpublished / privilege names as `AnalysisRequest`.

### 2.2 Silently ignored privilege names on `AnalysisRequest`

`AnalysisRequest` does not use `extra="forbid"`. Names **not** on the unpublished list were dropped without error: `key`, `budget`, `activity_id`, `reservation_state`, `hosted_live_enabled`, `operator_approval`, `cache_bust`, …

`force_live` was already rejected. The rest were not.

**Fix:** unpublished set is unioned with `CLIENT_NEVER_SET_FIELDS` in `app.domain.client_privilege`.

### 2.3 Query / header enablement

Job POST handlers validated JSON bodies only. `?force_live=1` and `X-Force-Live: true` / `X-Hosted-Live-Enabled: 1` were ignored (not applied — but also not rejected). Future workers that read those surfaces would have a ready-made bypass.

**Fix:** `create_analysis_job` and `create_two_signal_job` call `reject_client_privilege_surfaces` on query + headers.

### 2.4 Incomplete authorization / leak lists

`spend_threat_guards`, P2 `_LEAK_REQUEST_FIELDS`, and secret-boundary walks missed `budget`, `key`, `reservation_state`, `activity_id`, `hosted_live_enabled`, `operator_approval`.

**Fix:** those modules now include the LIVE-N set (serializer denylist adds only names that do not collide with public OpenAPI keys).

### 2.5 No `UNKNOWN_VENDOR_STATE` / activity-id attack surface

J3/J4 durable worker states are not on this branch. There was no executable policy that refused client-forced resubmit or client-minted `activity_id`.

**Fix:** isolated `hosted_live_redteam` policy + in-process `ServerActivityRegistry`. This is the contract sibling worker streams must honor. It is **not** a second job system and is **not** wired to FortyGuard.

---

## 3. Attack results

Executable suite: `apps/api/tests/unit/test_hosted_live_redteam.py`  
**74 tests, all passing.** Related spend/public/allowance/OpenAPI suites also passed in the same worktree (301 tests across those files, 0 failures).

| # | Attack | Result | Notes |
|---|---|---|---|
| A1 | Body sets allowance / budget / key / `force_live` / operator approval / reservation state | **BLOCKED** | `AnalysisRequest` + P2 publication + HTTP 422 |
| A2 | Nested `scenario` privilege extras | **BLOCKED** | Was stored+echoed; now 422 |
| A3 | Query `force_live` / `hosted_live_enabled` / `budget` | **BLOCKED** | Job POST only |
| A4 | Headers `X-Force-Live`, `X-Hosted-Live-Enabled`, `X-Reservation-Id` | **BLOCKED** | Job POST only |
| B1 | Enable hosted live via privilege fields | **BLOCKED** | Settings defaults remain `demo_allowance_enabled=False`, cap `0` |
| B2 | P2 `data_mode=live` | **BLOCKED** | Literal `replay` \| `auto` |
| B3 | Legacy `data_mode=live` | **DOES NOT GRANT** | Field still accepted on `AnalysisRequest`; orchestrator refuses LIVE fetch; not a spend grant |
| C1 | Cache-bust (`cache_bust`, `nocache`, `bypass_cache`, …) | **BLOCKED** | Request + scanner |
| C2 | Replay same fingerprint | **JOIN, no second reserve** | Ledger `JOIN_EXISTING_RESERVATION` |
| C3 | Forge `activity_id` | **BLOCKED** | Unknown / client-minted / cross-fingerprint steal |
| C4 | Steal reservation by id | **BLOCKED** | Client-supplied id rejected; identity mismatch still fails consume |
| D1 | Double consume | **BLOCKED** | Second consume raises; remaining units intact |
| D2 | Reuse grant on other fingerprint | **BLOCKED** | `fingerprint_mismatch` |
| D3 | Client paid retry after consume / post-submit | **BLOCKED** | Policy `paid_retry_allowed` is false |
| D4 | Distinct request after cap=1 | **EXHAUSTED** | No extra reserve |
| E1 | `UNKNOWN_VENDOR_STATE` auto-resubmit | **REFUSED** | `may_submit=False` → `RECOVERY_REQUIRED` or `RECONCILE_ONLY` |
| E2 | Client `force_resubmit` in any state | **REFUSED** | All `WorkerRecoveryState` values |
| E3 | Crash during `SUBMITTING` (submit may have occurred) | **NO RESUBMIT** | Treat as unknown; reconcile only |

**Verdict:** public client cannot set the listed spend/live/reservation controls on the hardened surfaces. Hosted live remains **default OFF**. Forced resubmit is not a client action.

---

## 4. Exactly-once honesty

Do **not** write “exactly-once delivery” or “exactly-once spend” in judge copy.

| Guarantee | Status |
|---|---|
| Client cannot authorize spend | Yes (server grant / demo reservation only) |
| Same fingerprint does not double-reserve in-process | Yes (J0 ledger lock) |
| Consume is terminal | Yes |
| `UNKNOWN_VENDOR_STATE` does not auto-resubmit | Yes (policy module) |
| At-most-one-submit if every worker honors the policy | **Intended**, not proven against a real vendor |
| Vendor idempotency | **Unknown / not assumed** |
| Crash after submit, before `activity_id` persist | Residual: one in-flight vendor job may exist with no local handle → reconcile, never a second submit |
| Process restart (InMemory ledger) | Residual: reservations reset; must not auto-resume paid work (J0 documented) |

A second submit after an unknown submit is how double-spend happens. The policy forbids that second submit. That is *at-most-one-submit*, not mathematical exactly-once.

---

## 5. Residual risks (honest)

1. **J3/J4 worker is not on this branch.** Recovery policy is tested against the LIVE-N module. Production worker (LIVE-C/D/I) must call the same rules. If a future path submits on `UNKNOWN_VENDOR_STATE`, these tests will not stop that binary.

2. **InMemory allowance is J0.** Restart drops reserved/consumed counts. Under-count can allow extra reserves after crash; over-count of “lost” reserved units is also possible depending on recovery. LIVE-F durability is a sibling. Until then, hosted live must stay off.

3. **`AnalysisRequest.data_mode=live` is still a legal field.** It does not enable demo allowance and Gate 0 refuses LIVE FortyGuard fetch. It is still a live-*intent* knob on the legacy route. Residual: a later orchestrator change could honor it.

4. **Unpublished `TwoSignalPublicRequest` still accepts `acquisition_preference=allow_hosted_live_demo` and `data_mode=live`.** That candidate is not the P2 public DTO. Residual: if someone mounts it without the P2 leak list, preference becomes a live request (still not a grant).

5. **Header/query rejection is only on job POST.** Places, geographies, GET job, and health do not run the scanner. Privilege headers there are ignored, not applied — but also not 422.

6. **`ScenarioRequest` remains `extra="allow"`** for non-privilege keys. Unknown scenario fields still persist into `job.request`.

7. **Rate-limit client class is spoofable** (`X-Forwarded-For`). Availability guard, not a spend grant. An attacker can rotate classes to stampede *if* hosted live were on.

8. **`Settings.fortyguard_api_key` exists in process config.** LIVE-N does not read it. Residual: any new code path that constructs a vendor from settings creates a second live path (forbidden). Temporal program owns the one authorized call.

9. **Join returns the same `reservation_id` in-process.** If a future public serializer emits `reservation_id`, steal attacks become targeting, not discovery. Consume still requires matching fingerprint *and* forbids client-supplied ids — both must stay.

10. **Serializer denylist is not the full privilege set.** Generic names (`demo`, `operator`, `reservation`) were omitted so public OpenAPI key-walks do not false-positive. Response leak of those exact names is a residual if a DTO adds them.

11. **No durable `activity_id` store here.** `ServerActivityRegistry` is process-local, for attacks. LIVE-D must persist bindings before acknowledging submit.

12. **GET `/analysis/jobs/{id}` still returns stored `request`.** After the scenario fix, privilege keys should not be in new jobs. Old documents (if any) are out of scope.

---

## 6. Files changed

| Path | Role |
|---|---|
| `apps/api/app/domain/client_privilege.py` | **New.** Canonical never-set names, privilege headers, cache-bust / enable sets |
| `apps/api/app/services/hosted_live_redteam.py` | **New.** Surface scanner, activity registry, reservation-steal gate, recovery / paid-retry policy |
| `apps/api/tests/unit/test_hosted_live_redteam.py` | **New.** 74 adversarial tests |
| `docs/live-durability/SECURITY_RED_TEAM.md` | **New.** This report |
| `apps/api/app/domain/requests.py` | Privilege union + nested scenario reject |
| `apps/api/app/schemas/two_signal_public.py` | P2 leak list ∪ never-set |
| `apps/api/app/services/spend_threat_guards.py` | Client flag set ∪ never-set |
| `apps/api/app/services/secret_boundary.py` | `key`, `budget`, activity/reservation names |
| `apps/api/app/core/anonymous_guards.py` | Serializer denylist: budget, reservation_state, activity_id, hosted_live_enabled, operator_approval |
| `apps/api/app/api/routes/analysis_jobs.py` | Query/header reject on POST |
| `apps/api/app/api/routes/two_signal_jobs.py` | Query/header reject on POST |

---

## 7. Coordination

- **LIVE-J** owns broader secret/API hardening. Additive denylist unions should merge cleanly.
- **LIVE-C / LIVE-D / LIVE-I** must treat `UNKNOWN_VENDOR_STATE` as reconcile-only. Import or clone `decide_unknown_vendor_recovery` / `paid_retry_allowed`.
- **LIVE-F** must make reserve/consume crash-safe. This report does not claim J0 is durable.
- **LIVE-O** deploy: hosted live default OFF; this worktree must not be read as a go-live.
- **Do not merge a second vendor path.**

---

## 8. Readiness (LIVE-N only)

| Item | LIVE-N |
|---|---|
| Client cannot set cap / budget / key / force_live / approval / reservation state (tested surfaces) | Pass |
| Hosted live default OFF | Pass |
| Cache-bust / forge activity / steal reservation (policy + ledger) | Pass |
| Double-spend / paid-retry policy | Pass |
| `UNKNOWN_VENDOR_STATE` forced resubmit | Pass (policy; worker not on branch) |
| Mathematical exactly-once | **No. Do not claim.** |
| Safe to enable hosted live in production | **No.** J0 ledger, missing durable worker, residual live-intent field. |

**LIVE-N recommendation:** keep hosted live **OFF**. Merge red-team tests with sibling durability work before any operator enablement.
