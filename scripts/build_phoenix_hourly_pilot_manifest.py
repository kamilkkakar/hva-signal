#!/usr/bin/env python3
"""Build or verify the preregistered Phoenix hourly pilot artifacts.

This command is deterministic and local-only. It does not load a credential,
construct an HTTP client, or call FortyGuard.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.core.hourly_thermal_pilot_registry import (  # noqa: E402
    PHOENIX_HOURLY_PILOT_MANIFEST_RELATIVE_PATH,
    PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH,
    build_phoenix_hourly_thermal_pilot_manifest,
    render_phoenix_hourly_pilot_provider_aoi,
    render_phoenix_hourly_thermal_pilot_manifest,
)


def _check(path: Path, expected: bytes, label: str) -> bool:
    if not path.is_file() or path.read_bytes() != expected:
        print(f"ERROR: stale {label}: {path}", file=sys.stderr)
        return False
    print(f"VERIFIED: {path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the no-network Phoenix hourly Type-1 pilot manifest."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when either tracked pilot artifact differs from its rebuild.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    provider_path = root / PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH
    manifest_path = root / PHOENIX_HOURLY_PILOT_MANIFEST_RELATIVE_PATH
    provider = render_phoenix_hourly_pilot_provider_aoi(root)

    print("SOURCE_MODE: tracked_inputs")
    print("LIVE_HTTP: forbidden")
    print("CREDENTIAL_LOAD: forbidden")
    print("CREDITS_SPENT: 0")

    if args.check:
        provider_ok = _check(provider_path, provider, "provider AOI")
        if not provider_ok:
            return 1
        manifest = render_phoenix_hourly_thermal_pilot_manifest(
            build_phoenix_hourly_thermal_pilot_manifest(root)
        )
        manifest_ok = _check(manifest_path, manifest, "pilot manifest")
        if manifest_ok:
            print(f"MANIFEST_SHA256: {hashlib.sha256(manifest).hexdigest()}")
        return 0 if manifest_ok else 1

    provider_path.parent.mkdir(parents=True, exist_ok=True)
    provider_path.write_bytes(provider)
    manifest = render_phoenix_hourly_thermal_pilot_manifest(
        build_phoenix_hourly_thermal_pilot_manifest(root)
    )
    manifest_path.write_bytes(manifest)
    print(f"WROTE: {provider_path}")
    print(f"WROTE: {manifest_path}")
    print(f"MANIFEST_SHA256: {hashlib.sha256(manifest).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
