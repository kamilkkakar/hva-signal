# RETRY / TIMEOUT — HVA-SIGNAL LIVE-I

**Worktree:** `F:/cursor/hackathon-live-i`  
**Branch:** `feat/live-i-retry-timeout`  
**Policy version:** `hva-signal-retry-timeout-v1`  
**Date:** 2026-08-30  
**Owner:** LIVE-I  

This document is the retry and timeout contract for J3/J4 live acquisition. It does not authorize a vendor call. The Temporal program still owns the one authorized live call. This policy only decides whether a worker may *retry*, *poll*, *fetch a result*, or *hold*.

There is no mathematical exactly-once. The best achievable guarantee is **at-most-one-submit**.

---

## Hard rules

1. **No blind paid retry.** A new vendor submit is never authorized after submit may have occurred, after consume, or from an unknown vendor state.
2. **Pre-submit retries** are allowed only when submit certainty is `IMPOSSIBLE` (the process never entered the submit window and has no `activity_id`).
3. **Post-submit / `UNKNOWN_VENDOR_STATE`:** reconcile via `activity_id` only. **Never automatic resubmit.**
4. **Three timeout classes** are distinct and must not be collapsed:
   - `SUBMIT_TIMEOUT` — unknown whether the vendor accepted the call
   - `PROCESSING_TIMEOUT` — `activity_id` known; status poll deadline
   - `RESULT_TIMEOUT` — result fetch deadline after the vendor has a result
5. **Retry budgets are operator / server-side only.** Clients cannot set them (body, query, or headers).

`vendor_submit_authorized` is true only for **the first submit** from `ALLOWANCE_RESERVED`. That is not a retry.

---

## Policy table

| Case | Durable state | `activity_id` | Timeout | Action | Next state | Vendor submit? |
|---|---|---|---|---|---|---|
| Client sets budget / force-retry / timeout | any | any | any | `REJECT_CLIENT_CONTROL` | (request rejected) | no |
| Validation / local fail, budget left | `FAILED_PRE_SUBMIT` | none | — | `RETRY_PRE_SUBMIT` | `REQUESTED` | no (re-enter before reserve) |
| Pre-submit budget exhausted | `FAILED_PRE_SUBMIT` | none | — | `FAIL_CLOSED_NO_RETRY` | `FAILED_PRE_SUBMIT` | no |
| Claimed pre-submit fail but submit started | `FAILED_PRE_SUBMIT` | none / yes | — | `HOLD_UNKNOWN` | `UNKNOWN_VENDOR_STATE` | no |
| Reserved, submit never started | `ALLOWANCE_RESERVED` | none | — | `PROCEED_FIRST_SUBMIT` | `SUBMITTING` | **first submit only** |
| During / after submit, id missing | `SUBMITTING` / `SUBMITTED` | none | — | `HOLD_UNKNOWN` | `UNKNOWN_VENDOR_STATE` | no |
| Submit I/O or wait timed out | `SUBMITTING` | none | `SUBMIT_TIMEOUT` | `HOLD_UNKNOWN` | `UNKNOWN_VENDOR_STATE` | no |
| `activity_id` persisted | `ACTIVITY_ID_PERSISTED` / `PROCESSING` | yes | — | `RECONCILE_VIA_ACTIVITY_ID` | `PROCESSING` | no |
| Poll cycle timed out, polls left | `PROCESSING` | yes | `PROCESSING_TIMEOUT` | `CONTINUE_POLL` | `PROCESSING` | no |
| Poll budget exhausted | `PROCESSING` | yes | `PROCESSING_TIMEOUT` | `FAIL_CLOSED_NO_RETRY` | `FAILED_POST_SUBMIT` | no |
| Processing timeout, id missing | `PROCESSING` | none | `PROCESSING_TIMEOUT` | `HOLD_UNKNOWN` | `RECOVERY_REQUIRED` | no |
| Result fetch timed out, fetches left | `RESULT_RECEIVED` | yes | `RESULT_TIMEOUT` | `CONTINUE_RESULT_FETCH` | `RESULT_RECEIVED` | no |
| Result-fetch budget exhausted | `RESULT_RECEIVED` | yes | `RESULT_TIMEOUT` | `FAIL_CLOSED_NO_RETRY` | `FAILED_POST_SUBMIT` | no |
| Unknown vendor, no id | `UNKNOWN_VENDOR_STATE` | none | — | `HOLD_UNKNOWN` | `RECOVERY_REQUIRED` | no |
| Unknown vendor, id known | `UNKNOWN_VENDOR_STATE` | yes | — | `RECONCILE_VIA_ACTIVITY_ID` | `PROCESSING` | no |
| Operator recovery hold | `RECOVERY_REQUIRED` | none | — | `HOLD_UNKNOWN` | `RECOVERY_REQUIRED` | no |
| Post-submit failure | `FAILED_POST_SUBMIT` | any | — | `FAIL_CLOSED_NO_RETRY` | `FAILED_POST_SUBMIT` | no |
| Already consumed | `CONSUMED` | any | — | `NO_ACTION` | `CONSUMED` | no |
| Cache hit / joined / happy path | `CACHE_HIT` / `JOINED` / `REQUESTED` / `VALIDATED` | — | — | `NO_ACTION` | same | no |

Every decision sets `automatic_resubmit=false` and `paid_retry_authorized=false`.

---

## Timeout classes

| Class | When it applies | What the worker may do | What it must not do |
|---|---|---|---|
| **Submit-timeout** | Submit window, no `activity_id`, elapsed > `submit_timeout_s` | Mark `UNKNOWN_VENDOR_STATE`; later operator/LIVE-D reconcile if an id appears | Resubmit, assume the vendor never saw it |
| **Processing-timeout** | `activity_id` known; status poll elapsed > `processing_timeout_s` | Continue polling while `poll_count < max_status_polls`; else fail closed | Start a second submit |
| **Result-timeout** | Result is believed ready; fetch elapsed > `result_timeout_s` | Retry **GET result** while `result_fetch_count < max_result_fetches`; else fail closed | POST / submit again |

A single poll I/O timeout is not a license to resubmit. Exhausting the poll budget fails closed as `FAILED_POST_SUBMIT`.

---

## Submit certainty

| Certainty | Meaning | Retry of submit |
|---|---|---|
| `IMPOSSIBLE` | Never entered `SUBMITTING`+; no `activity_id`; `submit_started=false` | Pre-submit re-enter only |
| `POSSIBLE` | Submit window, `submit_started`, or any post-submit / unknown / recovery state | **Forbidden** |
| `CONFIRMED` | `activity_id` present | **Forbidden** (poll/fetch only) |

Labels are not trusted. A worker that writes `FAILED_PRE_SUBMIT` after `submit_started` or with an `activity_id` is treated as unknown, not as a safe retry.

---

## Budgets (operator / server only)

Defaults (fail-closed caps in parentheses):

| Budget | Default | Cap | Env key |
|---|---|---|---|
| `max_pre_submit_retries` | 2 | 8 | `HVA_LIVE_MAX_PRE_SUBMIT_RETRIES` |
| `max_status_polls` | 8 | 32 | `HVA_LIVE_MAX_STATUS_POLLS` |
| `max_result_fetches` | 3 | 16 | `HVA_LIVE_MAX_RESULT_FETCHES` |
| `submit_timeout_s` | 30 | 120 | `HVA_LIVE_SUBMIT_TIMEOUT_S` |
| `processing_timeout_s` | 120 | 900 | `HVA_LIVE_PROCESSING_TIMEOUT_S` |
| `result_timeout_s` | 30 | 180 | `HVA_LIVE_RESULT_TIMEOUT_S` |

Frozen flags: `automatic_paid_retry=false`, `resubmit_without_activity_id=false`, `client_may_set_budget=false`.

Load path: `app.services.retry_timeout.server_retry_timeout_budget()`.  
Client-looking env names (`max_retries`, `RETRY_BUDGET`, `force_retry`) are **ignored**.

Clients cannot raise these caps. A payload that includes any forbidden field is `REJECT_CLIENT_CONTROL` even if the worker would otherwise retry.

Forbidden client fields (normalized): `retry_budget`, `retry_policy`, `timeout_policy`, `max_retries`, `force_retry`, `resubmit`, `submit_timeout_s`, `poll_timeout_s`, `result_timeout_s`, `max_status_polls`, `x_retry_budget`, and the rest of `CLIENT_FORBIDDEN_RETRY_FIELDS`.

---

## Integration hooks

| Sibling | Hook |
|---|---|
| LIVE-C worker SM | Call `decide_retry_timeout` before any submit and on every failure/timeout. Honor `next_worker_state`. |
| LIVE-D activity-id | `RECONCILE_VIA_ACTIVITY_ID` / `CONTINUE_POLL` / `CONTINUE_RESULT_FETCH` are the only post-submit progress paths. |
| LIVE-E crash matrix | Crash during submit ≡ `SUBMIT_TIMEOUT` / `UNKNOWN_VENDOR_STATE`. Never test an auto-resubmit path. |
| LIVE-F allowance | `RETRY_PRE_SUBMIT` must not create a second reservation. `PROCEED_FIRST_SUBMIT` uses the existing reserve. |
| LIVE-J / request layer | Merge `CLIENT_FORBIDDEN_RETRY_FIELDS` into public request rejection. This module does not edit `AnalysisRequest`. |
| LIVE-K | Poll/result budgets here are not rate-limit substitutes. |
| LIVE-L mock | Inject the three timeout classes; do not add a real vendor. |
| LIVE-O | Operator env keys above; clients never set them. |

---

## Module map

| File | Role |
|---|---|
| `apps/api/app/domain/retry_timeout_policy.py` | Policy types, certainty, classify, decide |
| `apps/api/app/services/retry_timeout.py` | Operator budget loader for workers |
| `apps/api/tests/unit/test_retry_timeout_policy.py` | Unit tests |
| `docs/live-durability/RETRY_TIMEOUT.md` | This contract |

`app/domain/__init__.py` is **not** modified (package owned elsewhere).

---

## Gaps

1. **Not wired** into the J3/J4 worker (LIVE-C), activity reconciler (LIVE-D), or HTTP middleware. This is a decision module plus tests.
2. **`AnalysisRequest` / OpenAPI** do not yet reject the forbidden retry fields. LIVE-J should merge the set; until then, workers must pass `client_payload` into `PolicyContext`.
3. **`Settings` / `config.py`** do not expose the `HVA_LIVE_*` keys. Intentional isolation so LIVE-O can add them to the deploy contract without a second live path.
4. **No durable persistence** of `pre_submit_attempts` / `poll_count` / `result_fetch_count` (LIVE-A/B).
5. **Hosted-live-prevendor** already has a simpler `VendorRetryPolicy` / `VendorTimeoutPolicy` with a single `on_timeout=fail_closed_consume_no_retry`. This v1 policy supersedes that for J3/J4 but is not merged into that worktree.
6. **FortyGuard `polling.py`** still uses one timeout. Out of scope; this program does not call FortyGuard.
7. **Operator runbook** for `RECOVERY_REQUIRED` (manual `activity_id` lookup) is LIVE-O, not implemented here.
8. **Exactly-once is not claimed.** Vendor idempotency is unknown. At-most-one-submit is the honest ceiling.
