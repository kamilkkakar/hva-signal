"""Runtime geography paths. Separate from vendor CACHE_DIR. No workforce roots.

Gazetteer lives under data/census/2025/. Process cache lives under
GEOGRAPHY_CACHE_DIR (default .cache/geography locally, /tmp/hva-geography
on Render). Neither default may point at workforce/ or FortyGuard cache.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

GAZETTEER_RELATIVE = Path("data") / "census" / "2025"
GAZETTEER_ZIP_NAME = "2025_Gaz_place_national.zip"
GAZETTEER_SOURCE_NAME = "SOURCE.json"
DEFAULT_LOCAL_GEOGRAPHY_CACHE = Path(".cache") / "geography"
DEFAULT_RENDER_GEOGRAPHY_CACHE = Path("/tmp/hva-geography")
DEFAULT_VENDOR_CACHE = Path(".cache") / "fortyguard"
CENSUS_VINTAGE_TOKEN = "TIGER2025"
_WORKFORCE_TOKEN = "workforce"
_VENDOR_TOKEN = "fortyguard"


class GeographyPathError(ValueError):
    """Illegal geography or vendor cache path."""


def repository_root() -> Path:
    """Hackathon repo root (apps/api/app/core → parents[4])."""
    return Path(__file__).resolve().parents[4]


def _environ(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def _is_render(environ: Mapping[str, str]) -> bool:
    return bool(environ.get("RENDER") or environ.get("RENDER_SERVICE_ID"))


def _as_posix_lower(path: Path) -> str:
    return path.as_posix().replace("\\", "/").lower()


def assert_runtime_path_allowed(path: Path, *, label: str = "geography path") -> Path:
    """Refuse workforce trees and path tokens that must not be runtime roots."""
    posix = _as_posix_lower(path)
    parts = {part.lower() for part in path.parts}
    if _WORKFORCE_TOKEN in posix or _WORKFORCE_TOKEN in parts:
        raise GeographyPathError(
            f"{label} must not use workforce/; refused {path.as_posix()!r}"
        )
    return path


def resolve_repo_or_absolute(
    raw: str,
    *,
    repo_root: Path | None = None,
) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (repo_root or repository_root()) / path


def vendor_cache_dir(
    *,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
) -> Path:
    """FortyGuard / vendor CACHE_DIR. Geography must not share this tree."""
    env = _environ(environ)
    raw = env.get("CACHE_DIR", "").strip()
    if raw:
        return resolve_repo_or_absolute(raw, repo_root=repo_root)
    return (repo_root or repository_root()) / DEFAULT_VENDOR_CACHE


def assert_geography_cache_separate(
    geography_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
) -> Path:
    """GEOGRAPHY_CACHE_DIR must not be vendor CACHE_DIR or nested inside it."""
    assert_runtime_path_allowed(geography_root, label="GEOGRAPHY_CACHE_DIR")
    geo = geography_root if geography_root.is_absolute() else geography_root
    try:
        geo_resolved = geo.resolve()
    except OSError:
        geo_resolved = geo
    posix = _as_posix_lower(geo_resolved)
    if _VENDOR_TOKEN in posix:
        raise GeographyPathError(
            "GEOGRAPHY_CACHE_DIR must not use the vendor FortyGuard cache tree"
        )
    vendor = vendor_cache_dir(environ=environ, repo_root=repo_root)
    try:
        vendor_resolved = vendor.resolve()
    except OSError:
        vendor_resolved = vendor
    if geo_resolved == vendor_resolved:
        raise GeographyPathError(
            "GEOGRAPHY_CACHE_DIR must not equal vendor CACHE_DIR"
        )
    try:
        geo_resolved.relative_to(vendor_resolved)
    except ValueError:
        return geography_root
    raise GeographyPathError(
        "GEOGRAPHY_CACHE_DIR must not be inside vendor CACHE_DIR"
    )


def gazetteer_dir(*, repo_root: Path | None = None) -> Path:
    root = repo_root or repository_root()
    path = root / GAZETTEER_RELATIVE
    return assert_runtime_path_allowed(path, label="gazetteer dir")


def gazetteer_zip_path(*, repo_root: Path | None = None) -> Path:
    path = gazetteer_dir(repo_root=repo_root) / GAZETTEER_ZIP_NAME
    return assert_runtime_path_allowed(path, label="gazetteer zip")


def gazetteer_source_path(*, repo_root: Path | None = None) -> Path:
    path = gazetteer_dir(repo_root=repo_root) / GAZETTEER_SOURCE_NAME
    return assert_runtime_path_allowed(path, label="gazetteer SOURCE.json")


def geography_cache_dir(
    *,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Ephemeral geography cache. Not vendor CACHE_DIR. Not workforce/."""
    env = _environ(environ)
    root = repo_root or repository_root()
    raw = env.get("GEOGRAPHY_CACHE_DIR", "").strip()
    if raw:
        path = resolve_repo_or_absolute(raw, repo_root=root)
    elif _is_render(env):
        path = DEFAULT_RENDER_GEOGRAPHY_CACHE
    else:
        path = root / DEFAULT_LOCAL_GEOGRAPHY_CACHE
    return assert_geography_cache_separate(path, environ=env, repo_root=root)


def tiger_vintage_dir(
    *,
    census_vintage: str = CENSUS_VINTAGE_TOKEN,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    cache_root: Path | None = None,
) -> Path:
    root = cache_root or geography_cache_dir(environ=environ, repo_root=repo_root)
    path = root / "tiger" / census_vintage
    return assert_runtime_path_allowed(path, label="TIGER cache")


def tiger_state_dir(
    state_fips: str,
    *,
    census_vintage: str = CENSUS_VINTAGE_TOKEN,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    cache_root: Path | None = None,
) -> Path:
    if len(state_fips) != 2 or not state_fips.isdigit():
        raise GeographyPathError("state_fips must be two digits")
    path = (
        tiger_vintage_dir(
            census_vintage=census_vintage,
            environ=environ,
            repo_root=repo_root,
            cache_root=cache_root,
        )
        / state_fips
    )
    return assert_runtime_path_allowed(path, label="TIGER state cache")


def national_resolver_cache_dir(
    *,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    cache_root: Path | None = None,
) -> Path:
    root = cache_root or geography_cache_dir(environ=environ, repo_root=repo_root)
    path = root / "national_resolver"
    return assert_runtime_path_allowed(path, label="resolver cache")


def packages_cache_dir(
    *,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    cache_root: Path | None = None,
) -> Path:
    root = cache_root or geography_cache_dir(environ=environ, repo_root=repo_root)
    path = root / "packages"
    return assert_runtime_path_allowed(path, label="package cache")
