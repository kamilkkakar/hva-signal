"""Shared selected-time reservations and recovery; never blindly repeat a POST."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.domain.activity_reconciliation import DurableLivePhase as Phase
from app.integrations.fortyguard.cache import redact_secrets, ttl_for_heatmap_payload
from app.integrations.fortyguard.exceptions import AcquisitionAllowanceExceeded, TaskFailedError


class AcquisitionInProgress(RuntimeError):
    """Another database session owns this acquisition."""


class AcquisitionNeedsRecovery(RuntimeError):
    """A prior POST may have succeeded; a second POST is not safe."""


class AcquisitionStorageUnavailable(RuntimeError):
    """Durability was configured but cannot be established."""


class AcquisitionIdentityMismatch(RuntimeError):
    """A caller-supplied durable identity does not match its saved request."""


def _lock_key(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)


def acquisition_fingerprint(path: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps([path, payload], sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _saved_request_identity(document: Any) -> dict[str, Any] | None:
    """Extract only the fields that define a durable acquisition request."""
    if not isinstance(document, dict) or "path" not in document or "payload" not in document:
        return None
    return {"path": document["path"], "payload": document["payload"]}


class PostgresAcquisitionStore:
    def __init__(self, dsn: str, *, scope: str, daily_limit: int) -> None:
        if not dsn.strip() or not scope.strip():
            raise AcquisitionStorageUnavailable("Shared acquisition storage is not configured.")
        self._dsn = dsn
        self.scope = scope
        self.daily_limit = max(0, daily_limit)

    def _connect(self):
        # A dedicated session is required: transaction-pooling proxies are unsupported.
        return psycopg.connect(
            self._dsn, autocommit=True, row_factory=dict_row, connect_timeout=5,
            options="-c statement_timeout=5000 -c lock_timeout=5000",
        )

    def migrate(self) -> None:
        with self._connect() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_lock_key("hva-acquisition-schema-v1"),))
            conn.execute(Path(__file__).with_name("sql").joinpath("shared_acquisition.sql").read_text())

    def run(
        self, path: str, payload: dict[str, Any], *,
        submit: Callable[[], str], poll: Callable[[str], dict[str, Any]],
        request_fingerprint: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        fingerprint = request_fingerprint or acquisition_fingerprint(path, payload)
        if (
            len(fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in fingerprint)
        ):
            raise AcquisitionIdentityMismatch(
                "Durable acquisition fingerprint must be a lowercase SHA-256 digest."
            )
        request_document = redact_secrets({"path": path, "payload": payload})
        try:
            with self._connect() as conn:
                locked = conn.execute(
                    "SELECT pg_try_advisory_lock(%s) AS locked",
                    (_lock_key(f"request:{self.scope}:{fingerprint}"),),
                ).fetchone()["locked"]
                if not locked:
                    raise AcquisitionInProgress("Acquisition is running. No duplicate was submitted.")
                # Closing this dedicated connection releases its session lock even on failure.
                return self._run_locked(
                    conn,
                    fingerprint,
                    path,
                    payload,
                    request_document,
                    submit,
                    poll,
                )
        except psycopg.Error:
            raise AcquisitionStorageUnavailable(
                "Shared acquisition storage is unavailable. No fallback purchase is allowed."
            ) from None

    def _run_locked(
        self, conn, fingerprint, path, payload, request_document, submit, poll,
    ):
        row = conn.execute(
            """SELECT *, expires_at IS NOT NULL AND expires_at <= clock_timestamp() AS expired
               FROM hva_acquisitions WHERE scope = %s AND fingerprint = %s
               ORDER BY generation DESC LIMIT 1""",
            (self.scope, fingerprint),
        ).fetchone()
        if row and _saved_request_identity(row["request_payload"]) != request_document:
            raise AcquisitionIdentityMismatch(
                "Saved acquisition fingerprint belongs to a different request."
            )
        if row and row["state"] == Phase.RESULT_RECEIVED.value and not row["expired"]:
            return self._with_expiry(row["result_payload"], row["expires_at"]), "durable_replay"
        if row and row["state"] in {Phase.SUBMITTING.value, Phase.UNKNOWN_VENDOR_STATE.value}:
            self._update(conn, fingerprint, row["generation"], Phase.UNKNOWN_VENDOR_STATE)
            raise AcquisitionNeedsRecovery("Previous submission has no saved activity ID; reconciliation is required.")
        if row and row["state"] == Phase.FAILED_POST_SUBMIT.value:
            raise AcquisitionNeedsRecovery("The saved vendor activity failed; review is required before another purchase.")

        if row and row["state"] == Phase.ACTIVITY_ID_PERSISTED.value:
            generation, activity_id = row["generation"], row["activity_id"]
            source = "durable_resume"
        else:
            generation = row["generation"] + 1 if row else 1
            # Serialize only the short allowance transaction; vendor I/O holds no row locks.
            with conn.transaction():
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (_lock_key(f"allowance:{self.scope}"),))
                day = conn.execute("SELECT (clock_timestamp() AT TIME ZONE 'UTC')::date AS day").fetchone()["day"]
                used = conn.execute(
                    "SELECT count(*) AS used FROM hva_acquisitions WHERE scope = %s AND reserved_day = %s",
                    (self.scope, day),
                ).fetchone()["used"]
                if used >= self.daily_limit:
                    raise AcquisitionAllowanceExceeded(used, self.daily_limit)
                conn.execute(
                    """INSERT INTO hva_acquisitions
                       (scope, fingerprint, generation, reservation_id, reserved_day, request_payload, state)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (self.scope, fingerprint, generation, uuid4(), day,
                     Jsonb(request_document), Phase.SUBMITTING.value),
                )
            # Commit SUBMITTING and its reservation BEFORE the network can accept the POST.
            try:
                activity_id = submit()
            except Exception:
                self._update(conn, fingerprint, generation, Phase.UNKNOWN_VENDOR_STATE)
                raise
            if not activity_id or not activity_id.strip():
                self._update(conn, fingerprint, generation, Phase.UNKNOWN_VENDOR_STATE)
                raise AcquisitionNeedsRecovery("Submission returned no usable activity ID.")
            conn.execute(
                """UPDATE hva_acquisitions SET state = %s, activity_id = %s, updated_at = clock_timestamp()
                   WHERE scope = %s AND fingerprint = %s AND generation = %s""",
                (Phase.ACTIVITY_ID_PERSISTED.value, activity_id, self.scope, fingerprint, generation),
            )
            source = "live"

        try:
            result = poll(activity_id)
        except TaskFailedError:
            self._update(conn, fingerprint, generation, Phase.FAILED_POST_SUBMIT)
            raise
        # Poll timeouts/transient failures leave the activity ID available for recovery.
        bundled = redact_secrets({"activity_id": activity_id, "result": result})
        ttl = ttl_for_heatmap_payload(payload)
        saved = conn.execute(
            """UPDATE hva_acquisitions SET state = %s, result_payload = %s,
               expires_at = CASE WHEN %s::integer IS NULL THEN NULL
                   ELSE clock_timestamp() + %s::integer * interval '1 second' END,
               updated_at = clock_timestamp()
               WHERE scope = %s AND fingerprint = %s AND generation = %s RETURNING expires_at""",
            (Phase.RESULT_RECEIVED.value, Jsonb(bundled), ttl, ttl, self.scope, fingerprint, generation),
        ).fetchone()
        return self._with_expiry(bundled, saved["expires_at"]), source

    @staticmethod
    def _with_expiry(bundled, expires_at):
        if expires_at is None:
            return bundled
        return {**bundled, "_hva_expires_at": expires_at.isoformat()}

    def _update(self, conn, fingerprint, generation, phase):
        conn.execute(
            """UPDATE hva_acquisitions SET state = %s, updated_at = clock_timestamp()
               WHERE scope = %s AND fingerprint = %s AND generation = %s""",
            (phase.value, self.scope, fingerprint, generation),
        )


def store_from_settings(settings) -> PostgresAcquisitionStore | None:
    if not settings.shared_acquisition_enabled:
        return None
    return PostgresAcquisitionStore(
        settings.acquisition_database_url,
        scope=f"{settings.acquisition_account_scope}:{settings.app_env}:{settings.fortyguard_base_url.rstrip('/')}",
        daily_limit=settings.bounded_selected_time_daily_limit,
    )


if __name__ == "__main__":
    import argparse
    from app.core.config import Settings

    parser = argparse.ArgumentParser(description="Initialize shared acquisition tables.")
    parser.add_argument("--migrate", action="store_true", required=True)
    parser.parse_args()
    current = Settings()
    PostgresAcquisitionStore(current.acquisition_database_url, scope="migration", daily_limit=0).migrate()
    print("Shared acquisition schema is ready.")
