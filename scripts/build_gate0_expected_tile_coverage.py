#!/usr/bin/env python3
"""Rebuild or verify the Phoenix expected-tile-coverage evidence package.

This script reads tracked replay/cached artifacts only. It never imports a
FortyGuard client, performs HTTP, or spends credits.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.core.gate0_coverage_registry import (  # noqa: E402
    PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH,
    build_phoenix_expected_tile_coverage_evidence,
    render_phoenix_expected_tile_coverage_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build replay-only Phoenix Gate 0 tile-coverage evidence."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing the tracked Phoenix sources.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path; defaults to the canonical data/gate0 location.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the canonical artifact differs from a deterministic rebuild.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output or (root / PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH)
    rendered = render_phoenix_expected_tile_coverage_evidence(
        build_phoenix_expected_tile_coverage_evidence(root)
    )

    print("SOURCE_MODE: tracked_replay_and_cache")
    print("LIVE_HTTP: forbidden")
    print("CREDITS_SPENT: 0")
    print("COVERAGE_THRESHOLD_AUTHORIZED: false")
    if args.check:
        if not output.is_file() or output.read_bytes() != rendered:
            print(f"ERROR: stale coverage evidence: {output}", file=sys.stderr)
            return 1
        print(f"VERIFIED: {output}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)
    print(f"WROTE: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
