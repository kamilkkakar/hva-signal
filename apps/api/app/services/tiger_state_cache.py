"""On-demand one-state TIGER/Line fetch + cache. Default OFF.

HVA_CENSUS_FETCH defaults to 0. No live Census GET unless the flag is enabled
and a caller invokes ensure_state_tiger. Tests inject a transport; they must
not hit www2.census.gov.

Cache root is GEOGRAPHY_CACHE_DIR, never vendor CACHE_DIR or workforce/.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import threading
import time
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.core.geography_paths import (
    CENSUS_VINTAGE_TOKEN,
    assert_runtime_path_allowed,
    geography_cache_dir,
    tiger_state_dir,
    tiger_vintage_dir,
)
from app.services.national_resolver_cache import (
    DEFAULT_CENSUS_VINTAGE,
    tiger_place_zip_url,
    tiger_tract_zip_url,
)

HVA_CENSUS_FETCH_ENV = "HVA_CENSUS_FETCH"
CENSUS_FETCH_DISABLED = "CENSUS_FETCH_DISABLED"
CENSUS_SOURCE_UNAVAILABLE = "CENSUS_SOURCE_UNAVAILABLE"
CENSUS_SOURCE_MISMATCH = "CENSUS_SOURCE_MISMATCH"
GEOGRAPHY_CACHE_IO = "GEOGRAPHY_CACHE_IO"

CENSUS_USER_AGENT = "HVA-Signal/0.1 (geography)"
MAX_TIGER_ZIP_BYTES = 40 * 1024 * 1024
MIN_TIGER_ZIP_BYTES = 1024
UNCOMPRESSED_CAP_PER_STATE = 80 * 1024 * 1024
LRU_MAX_STATES = 2
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 60.0
READ_TIMEOUT_LARGE_S = 90.0
TOTAL_FETCH_WALL_S = 120.0
RETRY_BACKOFF_S = (1.0, 4.0, 16.0)
LARGE_READ_THRESHOLD = 12 * 1024 * 1024

# Measured HEAD sizes 2026-08-30. Optional pin for known states.
KNOWN_TIGER_CONTENT_LENGTHS: dict[tuple[str, str], int] = {
    ("04", "tract"): 8_521_817,
    ("04", "place"): 2_821_601,
    ("17", "tract"): 10_107_245,
    ("17", "place"): 6_140_463,
    ("36", "tract"): 8_952_181,
    ("36", "place"): 3_380_697,
    ("06", "tract"): 32_558_476,
    ("06", "place"): 9_885_068,
    ("48", "tract"): 32_785_064,
    ("48", "place"): 9_782_040,
}

_STATE_FIPS_RE = re.compile(r"^[0-9]{2}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_STATE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


class TigerCacheError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class CensusFetchDisabled(TigerCacheError):
    def __init__(self, message: str = "HVA_CENSUS_FETCH is off; refusing Census HTTP") -> None:
        super().__init__(CENSUS_FETCH_DISABLED, message)


class CensusSourceUnavailable(TigerCacheError):
    def __init__(self, message: str) -> None:
        super().__init__(CENSUS_SOURCE_UNAVAILABLE, message)


class CensusSourceMismatch(TigerCacheError):
    def __init__(self, message: str) -> None:
        super().__init__(CENSUS_SOURCE_MISMATCH, message)


class GeographyCacheIO(TigerCacheError):
    def __init__(self, message: str) -> None:
        super().__init__(GEOGRAPHY_CACHE_IO, message)


@dataclass(frozen=True)
class CensusHttpResponse:
    status_code: int
    content: bytes
    headers: Mapping[str, str]


class CensusTransport(Protocol):
    def get(self, url: str) -> CensusHttpResponse:
        """Return a response. Must not be used unless fetch is enabled."""


@dataclass(frozen=True)
class TigerStateArtifacts:
    state_fips: str
    census_vintage: str
    tract_zip: Path
    place_zip: Path
    source_path: Path


def census_fetch_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Default OFF. Only 1/true/yes/on enable live or injected fetch."""
    env = os.environ if environ is None else environ
    raw = str(env.get(HVA_CENSUS_FETCH_ENV, "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _state_lock(state_fips: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _STATE_LOCKS.setdefault(state_fips, threading.Lock())


def _header(headers: Mapping[str, str], name: str) -> str | None:
    want = name.lower()
    for key, value in headers.items():
        if key.lower() == want:
            text = str(value).strip()
            return text or None
    return None


def _require_state_fips(state_fips: str) -> str:
    text = state_fips.strip()
    if not _STATE_FIPS_RE.fullmatch(text):
        raise TigerCacheError("INVALID_STATE_FIPS", "state_fips must be two digits")
    return text


def _kind_filename(state_fips: str, kind: str, *, year: int = 2025) -> str:
    return f"tl_{year}_{state_fips}_{kind}.zip"


def _required_shp(state_fips: str, kind: str, *, year: int = 2025) -> str:
    return f"tl_{year}_{state_fips}_{kind}.shp"


def _validate_tiger_zip_bytes(data: bytes, *, state_fips: str, kind: str) -> None:
    if len(data) < MIN_TIGER_ZIP_BYTES:
        raise CensusSourceMismatch(
            f"{kind} zip is below the {MIN_TIGER_ZIP_BYTES} byte floor"
        )
    if len(data) > MAX_TIGER_ZIP_BYTES:
        raise CensusSourceMismatch(
            f"{kind} zip exceeds the {MAX_TIGER_ZIP_BYTES} byte cap"
        )
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise CensusSourceMismatch(f"{kind} payload is not a valid zip") from exc
    with zf:
        if zf.testzip() is not None:
            raise CensusSourceMismatch(f"{kind} zip is corrupt")
        want = _required_shp(state_fips, kind)
        names = [Path(name.replace("\\", "/")).name for name in zf.namelist()]
        if want not in names:
            raise CensusSourceMismatch(f"{kind} zip is missing {want}")
        uncompressed = sum(info.file_size for info in zf.infolist())
        if uncompressed > UNCOMPRESSED_CAP_PER_STATE:
            raise CensusSourceMismatch(
                f"{kind} zip uncompressed size exceeds the per-state cap"
            )


def _artifact_record(
    *,
    url: str,
    content: bytes,
    fetched_at: str,
) -> dict[str, object]:
    return {
        "url": url,
        "census_vintage": CENSUS_VINTAGE_TOKEN,
        "content_length": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "fetched_at": fetched_at,
    }


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise GeographyCacheIO(f"failed to write {path.as_posix()}") from exc


def _delete_partial(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _load_state_source(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CensusSourceMismatch("TIGER SOURCE.json is not valid JSON") from exc
    if not isinstance(document, dict):
        raise CensusSourceMismatch("TIGER SOURCE.json must be a JSON object")
    return document


def _cached_artifacts(
    state_dir: Path,
    state_fips: str,
    *,
    census_vintage: str,
) -> TigerStateArtifacts | None:
    tract = state_dir / _kind_filename(state_fips, "tract")
    place = state_dir / _kind_filename(state_fips, "place")
    source = state_dir / "SOURCE.json"
    if not (tract.is_file() and place.is_file() and source.is_file()):
        return None
    document = _load_state_source(source)
    if document is None:
        return None
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, dict):
        raise CensusSourceMismatch("TIGER SOURCE.json missing artifacts")
    for kind, path in (("tract", tract), ("place", place)):
        record = artifacts.get(kind)
        if not isinstance(record, dict):
            raise CensusSourceMismatch(f"TIGER SOURCE.json missing {kind} pin")
        sha = record.get("sha256")
        length = record.get("content_length")
        data = path.read_bytes()
        if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
            raise CensusSourceMismatch(f"cached {kind} sha256 pin is invalid")
        if hashlib.sha256(data).hexdigest() != sha:
            _delete_partial(path)
            raise CensusSourceMismatch(f"cached {kind} zip sha256 does not match pin")
        if isinstance(length, int) and length != len(data):
            _delete_partial(path)
            raise CensusSourceMismatch(f"cached {kind} zip length does not match pin")
        _validate_tiger_zip_bytes(data, state_fips=state_fips, kind=kind)
    return TigerStateArtifacts(
        state_fips=state_fips,
        census_vintage=census_vintage,
        tract_zip=tract,
        place_zip=place,
        source_path=source,
    )


def _content_length(headers: Mapping[str, str]) -> int:
    raw = _header(headers, "Content-Length")
    if raw is None:
        raise CensusSourceUnavailable("Census response omitted Content-Length")
    try:
        length = int(raw)
    except ValueError as exc:
        raise CensusSourceUnavailable("Census Content-Length is not an integer") from exc
    if length < MIN_TIGER_ZIP_BYTES or length > MAX_TIGER_ZIP_BYTES:
        raise CensusSourceMismatch(
            f"Census Content-Length {length} is outside the allowed zip range"
        )
    return length


def _download_one(
    url: str,
    *,
    transport: CensusTransport,
    state_fips: str,
    kind: str,
    enforce_known_lengths: bool,
    deadline: float,
) -> bytes:
    last_error: Exception | None = None
    for attempt, backoff in enumerate((0.0, *RETRY_BACKOFF_S)):
        if time.monotonic() > deadline:
            raise CensusSourceUnavailable("Census fetch exceeded the 120s wall budget")
        if backoff:
            time.sleep(backoff)
        try:
            response = transport.get(url)
        except CensusSourceUnavailable:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= len(RETRY_BACKOFF_S):
                break
            continue
        if response.status_code == 404:
            raise CensusSourceUnavailable(f"Census 404 for {url}")
        if response.status_code >= 500:
            last_error = CensusSourceUnavailable(
                f"Census {response.status_code} for {url}"
            )
            continue
        if response.status_code != 200:
            raise CensusSourceUnavailable(
                f"Census HTTP {response.status_code} for {url}"
            )
        expected = _content_length(response.headers)
        known = KNOWN_TIGER_CONTENT_LENGTHS.get((state_fips, kind))
        if enforce_known_lengths and known is not None and expected != known:
            raise CensusSourceMismatch(
                f"{kind} Content-Length {expected} does not match pinned {known}"
            )
        data = response.content
        if len(data) != expected:
            raise CensusSourceMismatch(
                f"{kind} body length {len(data)} does not match Content-Length {expected}"
            )
        _validate_tiger_zip_bytes(data, state_fips=state_fips, kind=kind)
        return data
    if last_error is not None:
        raise CensusSourceUnavailable(str(last_error)) from last_error
    raise CensusSourceUnavailable(f"Census fetch failed for {url}")


class _HttpxTransport:
    """Real Census GET. Constructed only when HVA_CENSUS_FETCH is on."""

    def get(self, url: str) -> CensusHttpResponse:
        import httpx

        timeout = httpx.Timeout(READ_TIMEOUT_S, connect=CONNECT_TIMEOUT_S)
        try:
            with httpx.Client(
                timeout=timeout,
                headers={"User-Agent": CENSUS_USER_AGENT},
                follow_redirects=True,
            ) as client:
                with client.stream("GET", url) as response:
                    headers = {k: v for k, v in response.headers.items()}
                    length_raw = _header(headers, "Content-Length")
                    cap = MAX_TIGER_ZIP_BYTES
                    if length_raw is not None:
                        try:
                            declared = int(length_raw)
                        except ValueError:
                            declared = cap
                        if declared > LARGE_READ_THRESHOLD:
                            response.close()
                            return self._read_large(url, declared)
                        cap = min(cap, declared)
                    buf = bytearray()
                    for chunk in response.iter_bytes():
                        buf.extend(chunk)
                        if len(buf) > cap:
                            raise CensusSourceMismatch(
                                "Census body exceeded Content-Length or the 40 MiB cap"
                            )
                    return CensusHttpResponse(
                        status_code=response.status_code,
                        content=bytes(buf),
                        headers=headers,
                    )
        except httpx.TimeoutException as exc:
            raise CensusSourceUnavailable(f"Census timeout for {url}") from exc
        except httpx.HTTPError as exc:
            raise CensusSourceUnavailable(f"Census HTTP error for {url}") from exc

    def _read_large(self, url: str, declared: int) -> CensusHttpResponse:
        import httpx

        timeout = httpx.Timeout(READ_TIMEOUT_LARGE_S, connect=CONNECT_TIMEOUT_S)
        with httpx.Client(
            timeout=timeout,
            headers={"User-Agent": CENSUS_USER_AGENT},
            follow_redirects=True,
        ) as client:
            with client.stream("GET", url) as response:
                headers = {k: v for k, v in response.headers.items()}
                buf = bytearray()
                for chunk in response.iter_bytes():
                    buf.extend(chunk)
                    if len(buf) > MAX_TIGER_ZIP_BYTES:
                        raise CensusSourceMismatch("Census body exceeded the 40 MiB cap")
                return CensusHttpResponse(
                    status_code=response.status_code,
                    content=bytes(buf),
                    headers=headers,
                )


def _lru_evict(cache_root: Path, *, keep_state: str, census_vintage: str) -> None:
    vintage = tiger_vintage_dir(census_vintage=census_vintage, cache_root=cache_root)
    if not vintage.is_dir():
        return
    states: list[tuple[float, str, Path, int]] = []
    for child in vintage.iterdir():
        if not child.is_dir() or not _STATE_FIPS_RE.fullmatch(child.name):
            continue
        source = _load_state_source(child / "SOURCE.json")
        fetched = 0.0
        if isinstance(source, dict):
            artifacts = source.get("artifacts")
            if isinstance(artifacts, dict):
                for record in artifacts.values():
                    if isinstance(record, dict) and isinstance(record.get("fetched_at"), str):
                        try:
                            fetched = max(
                                fetched,
                                datetime.fromisoformat(record["fetched_at"]).timestamp(),
                            )
                        except ValueError:
                            pass
        size = 0
        for zip_path in child.glob("*.zip"):
            try:
                size += zip_path.stat().st_size
            except OSError:
                pass
        states.append((fetched, child.name, child, size))
    if len(states) <= LRU_MAX_STATES:
        total = sum(item[3] for item in states)
        if total <= UNCOMPRESSED_CAP_PER_STATE:
            return
    states.sort(key=lambda item: item[0])
    kept = 0
    used = 0
    # Prefer the just-written state, then newest.
    ordered = [item for item in states if item[1] == keep_state] + [
        item for item in reversed(states) if item[1] != keep_state
    ]
    retain: set[str] = set()
    for _fetched, name, _path, size in ordered:
        if kept >= LRU_MAX_STATES:
            break
        if used + size > UNCOMPRESSED_CAP_PER_STATE and kept:
            break
        retain.add(name)
        kept += 1
        used += size
    for _fetched, name, path, _size in states:
        if name not in retain:
            for child in path.glob("*"):
                _delete_partial(child)
            try:
                path.rmdir()
            except OSError:
                pass


def ensure_state_tiger(
    state_fips: str,
    *,
    cache_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
    transport: CensusTransport | None = None,
    fetch: bool | None = None,
    enforce_known_lengths: bool = True,
    census_vintage: str = DEFAULT_CENSUS_VINTAGE,
) -> TigerStateArtifacts:
    """Return cached one-state TIGER zips, or fetch when HVA_CENSUS_FETCH is on.

    Cache hits never touch the network. Cache misses fail closed when fetch is
    off (the default).
    """
    ss = _require_state_fips(state_fips)
    if census_vintage != CENSUS_VINTAGE_TOKEN and census_vintage != "2025":
        raise CensusSourceMismatch("only TIGER2025 is supported")
    vintage = CENSUS_VINTAGE_TOKEN
    root = cache_root or geography_cache_dir(environ=environ, repo_root=repo_root)
    assert_runtime_path_allowed(root, label="GEOGRAPHY_CACHE_DIR")
    state_dir = tiger_state_dir(
        ss,
        census_vintage=vintage,
        cache_root=root,
    )
    allow_fetch = census_fetch_enabled(environ) if fetch is None else fetch
    with _state_lock(ss):
        cached = _cached_artifacts(state_dir, ss, census_vintage=vintage)
        if cached is not None:
            return cached
        if not allow_fetch:
            raise CensusFetchDisabled(
                f"TIGER {vintage} state {ss} is not cached and HVA_CENSUS_FETCH is off"
            )
        active = transport if transport is not None else _HttpxTransport()
        deadline = time.monotonic() + TOTAL_FETCH_WALL_S
        tract_url = tiger_tract_zip_url(census_vintage=vintage, state_fips=ss)
        place_url = tiger_place_zip_url(census_vintage=vintage, state_fips=ss)
        tract_bytes = _download_one(
            tract_url,
            transport=active,
            state_fips=ss,
            kind="tract",
            enforce_known_lengths=enforce_known_lengths,
            deadline=deadline,
        )
        place_bytes = _download_one(
            place_url,
            transport=active,
            state_fips=ss,
            kind="place",
            enforce_known_lengths=enforce_known_lengths,
            deadline=deadline,
        )
        if sum(
            info.file_size
            for data in (tract_bytes, place_bytes)
            for info in zipfile.ZipFile(io.BytesIO(data)).infolist()
        ) > UNCOMPRESSED_CAP_PER_STATE:
            raise CensusSourceMismatch("state TIGER uncompressed size exceeds 80 MiB")
        fetched_at = datetime.now(timezone.utc).isoformat()
        tract_path = state_dir / _kind_filename(ss, "tract")
        place_path = state_dir / _kind_filename(ss, "place")
        source_path = state_dir / "SOURCE.json"
        try:
            _write_atomic(tract_path, tract_bytes)
            _write_atomic(place_path, place_bytes)
            document = {
                "census_vintage": vintage,
                "state_fips": ss,
                "artifacts": {
                    "tract": _artifact_record(
                        url=tract_url, content=tract_bytes, fetched_at=fetched_at
                    ),
                    "place": _artifact_record(
                        url=place_url, content=place_bytes, fetched_at=fetched_at
                    ),
                },
            }
            _write_atomic(
                source_path,
                (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )
        except Exception:
            _delete_partial(tract_path)
            _delete_partial(place_path)
            _delete_partial(source_path)
            raise
        _lru_evict(root, keep_state=ss, census_vintage=vintage)
        return TigerStateArtifacts(
            state_fips=ss,
            census_vintage=vintage,
            tract_zip=tract_path,
            place_zip=place_path,
            source_path=source_path,
        )
