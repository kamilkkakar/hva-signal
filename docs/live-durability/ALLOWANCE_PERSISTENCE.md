# ALLOWANCE PERSISTENCE

LIVE-F / HVA-SIGNAL. Local durable ledger for demo reservations and consumes.

This is not a vendor client. It does not call FortyGuard. It does not claim
mathematical exactly-once delivery.

## Defaults

| Control | Default | Who may set it |
|---|---|---|
| Hosted live / `demo_allowance_enabled` | **OFF** | Operator / process settings only |
| `demo_allowance_store_path` | empty → J0 in-memory | Operator only |
| `demo_allowance_max_total_units` | `0` | Operator only |
| Reservation TTL | `900` seconds | Operator only |
| Max open reservations | `8` | Operator only |

Enabling a SQLite path does **not** enable hosted live. Spend still requires a
server-side `DemoAllowancePolicy` with `enabled=true` and a positive cap.

## Store

- J0: `InMemoryDemoAllowanceLedger` — process local. Restart drops remaining.
- J3: `SqliteDemoAllowanceStore` — WAL + `synchronous=FULL`, separate file from
  the job store (LIVE-B). Reservations, consumes, and fingerprint-bound cached
  payloads persist across process restart.

Factory: `demo_allowance_ledger_from_settings`. Empty path keeps J0.

## Invariants

1. **Reserve is not consume.** A persisted `RESERVED` row holds capacity. It
   does not increment `consumed_units`.
2. **Consume is terminal** on `consume()`. A second `consume()` raises. Recovery
   uses `consume_after_cached_result`, which is idempotent.
3. **Crash after reserve** does not auto-consume and does not resume paid work.
   Stale `RESERVED` rows expire at `min(policy.valid_until, created+ttl)`.
   `max_open_reservations` stops an unbounded reserved-row pile-up.
4. **Crash after cache before consume** recovers the cached payload and consumes
   at most once. The cache write is a separate commit from consume so a crash
   between them cannot lose the result.
5. **Join before new reserve.** The same fingerprint + geometry + units joins
   the open reservation after restart. Join is not a new spend.
6. **Client cannot set:** allowance cap, budget, key, `force_live`, operator
   approval, or reservation state. Rejection is denylist + `extra=forbid` on
   public request models. The store constructor never accepts a client state.
7. **Hosted live default OFF.**

## Recovery

| Crash point | Restart behavior | Spend risk |
|---|---|---|
| After reserve, before vendor | Reservation remains `RESERVED` until TTL; then `EXPIRED`. Capacity returns. No consume. | Held capacity until TTL. No double-consume. |
| After cache, before consume | Cache row is present. `consume_after_cached_result` consumes once. Replay is a no-op. | At-most-one consume. No second submit from this module. |
| After consume | `CONSUMED` survives. Further `consume()` fails. | No double-count. |

`recover_after_restart` never sets `auto_consumed` or `auto_resumed_paid_work`.

## Client / public safety

Forbidden request keys live in `allowance_client_denylist.CLIENT_NEVER_SET_ALLOWANCE_KEYS`
and are also rejected by `TwoSignalPublicationRequest`, `AnalysisRequest`,
`spend_threat_guards`, and the public serializer denylist.

Remaining units, reservation ids, and reservation state are internal. Do not
serialize them on public job bodies.

## Gaps

- **Local file only.** Deleting the SQLite file resets consumes. Render-style
  ephemeral disks lose durability. Multi-instance deploy does not share the file.
- **Not production-authoritative.** No HMAC, no replica, no operator sealed log.
- **Consume timing in the current worker path.** `recheck_demo_reservation_before_paid_submission`
  still consumes *before* paid submit (J0 defense). LIVE-H/C own moving consume
  to after cache. This store supports both: `consume()` now, or
  `persist_cached_result` then `consume_after_cached_result`.
- **TTL vs late cache.** If TTL expires after cache is written but before
  consume, recovery refuses `consume_after_cached_result` so we do not invent a
  consume on an `EXPIRED` row. The cached payload is kept. That can under-count
  spend if a vendor call already happened — worker/activity recovery (LIVE-D)
  must treat that as already-submitted, not as a new reserve.
- **In-memory default.** Restart of the default process still drops J0 remaining
  (`restart_resets_remaining=true`).
- **No mathematical exactly-once** at a vendor that lacks idempotency. This
  ledger only guarantees at-most-one consume *count* and join-on-fingerprint.
