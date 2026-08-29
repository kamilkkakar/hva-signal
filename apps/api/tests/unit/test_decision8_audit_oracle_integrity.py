"""Integrity of the tracked Decision 8 audit oracle.

The expected SHA-256 is the already-reviewed local Gate 0 Decision 8
policy-impact CSV (ignored, local-only). It is not computed from production
output or from the tracked copy at authoring time. CI must verify the
fixture without that ignored directory.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ORACLE_CSV = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "decision8"
    / "decision8_policy_impact_by_timestamp.csv"
)

EXPECTED_ORACLE_SHA256 = (
    "febd0cdd11451eff16e01fe59d26ffeaf94456d94e422ac45045431de1e0a651"
)


def test_tracked_decision8_oracle_matches_reviewed_source_sha256() -> None:
    assert ORACLE_CSV.is_file(), f"missing tracked Decision 8 oracle {ORACLE_CSV}"
    posix = ORACLE_CSV.as_posix()
    assert "/workforce/" not in posix
    assert not posix.endswith("/workforce")
    digest = hashlib.sha256(ORACLE_CSV.read_bytes()).hexdigest()
    assert digest == EXPECTED_ORACLE_SHA256
