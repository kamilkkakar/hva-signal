"""Census place-search runtime: fixtures only. Fetch default OFF. No live Census GET."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from app.core.geography_paths import (
    GeographyPathError,
    gazetteer_source_path,
    gazetteer_zip_path,
    geography_cache_dir,
    packages_cache_dir,
    repository_root,
    tiger_state_dir,
    vendor_cache_dir,
)
from app.domain.census_place import PLACE_IDENTITY_VINTAGE, PlaceIdentityFailure
from app.services.census_runtime import (
    GazetteerUnavailable,
    TractGeoidError,
    geography_cache_identity,
    geography_cache_key,
    get_place_index,
    load_gazetteer_index,
    load_gazetteer_source_pin,
    require_resolve_tract_geoids,
    reset_place_index_cache,
    search_census_place,
    validate_tract_geoid,
)
from app.services.national_resolver_cache import (
    DEFAULT_CENSUS_VINTAGE,
    FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
    tiger_place_zip_url,
    tiger_tract_zip_url,
)
from app.services.tiger_state_cache import (
    CENSUS_FETCH_DISABLED,
    CensusFetchDisabled,
    CensusHttpResponse,
    CensusSourceMismatch,
    CensusSourceUnavailable,
    census_fetch_enabled,
    ensure_state_tiger,
)

EXCERPT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "census_place_gazetteer_2025_excerpt.txt"
)
EXCERPT_ROWS = 25
_GAZ_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2025_Gazetteer/2025_Gaz_place_national.zip"
)


@pytest.fixture(autouse=True)
def _fetch_off_and_reset_index(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HVA_CENSUS_FETCH", "0")
    reset_place_index_cache()
    yield
    reset_place_index_cache()


def _zip_bytes(members: dict[str, bytes], *, stored: bool = False) -> bytes:
    buf = io.BytesIO()
    compression = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(buf, "w", compression=compression) as zf:
        for name, payload in members.items():
            zf.writestr(name, payload)
    return buf.getvalue()


def _gazetteer_tree(
    root: Path,
    text: str,
    *,
    sha256: str | None | object = "auto",
    content_length: int | None = None,
    row_count: int | None = EXCERPT_ROWS,
) -> bytes:
    dest = root / "data" / "census" / "2025"
    dest.mkdir(parents=True)
    raw = _zip_bytes({"2025_Gaz_place_national.txt": text.encode("utf-8")})
    (dest / "2025_Gaz_place_national.zip").write_bytes(raw)
    pin = {
        "artifact": "2025_Gaz_place_national.zip",
        "identity_vintage": PLACE_IDENTITY_VINTAGE,
        "url": _GAZ_URL,
        "content_length": len(raw) if content_length is None else content_length,
        "sha256": hashlib.sha256(raw).hexdigest() if sha256 == "auto" else sha256,
        "row_count_national": row_count,
        "scope_default": "conus_plus_dc",
    }
    (dest / "SOURCE.json").write_text(
        json.dumps(pin, indent=2) + "\n", encoding="utf-8"
    )
    return raw


def _tiger_zip(state_fips: str, kind: str) -> bytes:
    shp = f"tl_2025_{state_fips}_{kind}.shp"
    return _zip_bytes({shp: b"FAKE-SHP", "pad.bin": b"x" * 2048}, stored=True)


class RecordingTransport:
    def __init__(self, bodies: dict[str, bytes]) -> None:
        self.bodies = bodies
        self.urls: list[str] = []

    def get(self, url: str) -> CensusHttpResponse:
        self.urls.append(url)
        if url not in self.bodies:
            return CensusHttpResponse(404, b"", {"Content-Length": "0"})
        data = self.bodies[url]
        return CensusHttpResponse(200, data, {"Content-Length": str(len(data))})


def test_census_fetch_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HVA_CENSUS_FETCH", raising=False)
    assert census_fetch_enabled({}) is False
    assert census_fetch_enabled() is False
    assert census_fetch_enabled({"HVA_CENSUS_FETCH": "0"}) is False
    assert census_fetch_enabled({"HVA_CENSUS_FETCH": "1"}) is True


def test_import_does_not_load_gazetteer_or_fetch() -> None:
    assert get_place_index.__module__ == "app.services.census_runtime"
    reset_place_index_cache()
    # Process cache stays empty until an explicit load.
    from app.services import census_runtime as runtime

    assert runtime._INDEX is None


def test_shipped_source_json_pins_url_and_length_without_zip() -> None:
    pin = load_gazetteer_source_pin(gazetteer_source_path())
    assert pin.url == _GAZ_URL
    assert pin.content_length == 1_214_053
    assert pin.identity_vintage == PLACE_IDENTITY_VINTAGE
    assert pin.sha256 is None
    assert pin.row_count_national == 32_350
    assert not gazetteer_zip_path().is_file()
    with pytest.raises(GazetteerUnavailable, match="not present"):
        load_gazetteer_index()


def test_gazetteer_loads_when_zip_matches_pin(tmp_path: Path) -> None:
    text = EXCERPT.read_text(encoding="utf-8")
    _gazetteer_tree(tmp_path, text)
    index = load_gazetteer_index(repo_root=tmp_path)
    result = search_census_place("Chicago, IL", index=index)
    assert result.ok
    assert result.identity is not None
    assert result.identity.place_geoid == "1714000"


def test_missing_zip_fails_closed(tmp_path: Path) -> None:
    dest = tmp_path / "data" / "census" / "2025"
    dest.mkdir(parents=True)
    dest.joinpath("SOURCE.json").write_text(
        json.dumps(
            {
                "artifact": "2025_Gaz_place_national.zip",
                "identity_vintage": PLACE_IDENTITY_VINTAGE,
                "url": _GAZ_URL,
                "content_length": 1214053,
                "sha256": "ab" * 32,
                "row_count_national": 32350,
                "scope_default": "conus_plus_dc",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(GazetteerUnavailable) as exc:
        load_gazetteer_index(repo_root=tmp_path)
    assert exc.value.code == "GEOGRAPHY_INDEX_INVALID"


def test_length_and_sha_mismatch_fail_closed(tmp_path: Path) -> None:
    text = EXCERPT.read_text(encoding="utf-8")
    raw = _gazetteer_tree(tmp_path, text, content_length=999)
    with pytest.raises(GazetteerUnavailable, match="length"):
        load_gazetteer_index(repo_root=tmp_path)
    _gazetteer_tree(
        tmp_path / "other",
        text,
        sha256="00" * 32,
        content_length=len(raw),
        row_count=EXCERPT_ROWS,
    )
    with pytest.raises(GazetteerUnavailable, match="sha256"):
        load_gazetteer_index(repo_root=tmp_path / "other")


def test_present_zip_with_unpinned_sha_fails_closed(tmp_path: Path) -> None:
    text = EXCERPT.read_text(encoding="utf-8")
    _gazetteer_tree(tmp_path, text, sha256=None)
    with pytest.raises(GazetteerUnavailable, match="not pinned"):
        load_gazetteer_index(repo_root=tmp_path)


def test_ambiguous_springfield_from_fixture_zip(tmp_path: Path) -> None:
    _gazetteer_tree(tmp_path, EXCERPT.read_text(encoding="utf-8"))
    result = search_census_place(
        "Springfield",
        index=load_gazetteer_index(repo_root=tmp_path),
    )
    assert not result.ok
    assert result.failure is PlaceIdentityFailure.AMBIGUOUS_PLACE


def test_geography_cache_dir_is_not_vendor_cache(tmp_path: Path) -> None:
    env = {
        "GEOGRAPHY_CACHE_DIR": str(tmp_path / "geo"),
        "CACHE_DIR": str(tmp_path / "fortyguard"),
    }
    geo = geography_cache_dir(environ=env, repo_root=tmp_path)
    vendor = vendor_cache_dir(environ=env, repo_root=tmp_path)
    assert geo != vendor
    assert "fortyguard" not in geo.as_posix().lower()
    assert "workforce" not in geo.as_posix().lower()
    assert packages_cache_dir(environ=env, repo_root=tmp_path) == geo / "packages"


def test_default_geography_cache_is_local_dot_cache(tmp_path: Path) -> None:
    geo = geography_cache_dir(environ={}, repo_root=tmp_path)
    assert geo == tmp_path / ".cache" / "geography"
    vendor = vendor_cache_dir(environ={}, repo_root=tmp_path)
    assert vendor == tmp_path / ".cache" / "fortyguard"
    render = geography_cache_dir(environ={"RENDER": "true"}, repo_root=tmp_path)
    assert render == Path("/tmp/hva-geography")


def test_geography_cache_refuses_vendor_and_workforce_roots(tmp_path: Path) -> None:
    with pytest.raises(GeographyPathError, match="vendor"):
        geography_cache_dir(
            environ={"GEOGRAPHY_CACHE_DIR": ".cache/fortyguard"},
            repo_root=tmp_path,
        )
    with pytest.raises(GeographyPathError, match="workforce"):
        geography_cache_dir(
            environ={"GEOGRAPHY_CACHE_DIR": str(tmp_path / "workforce" / "cache")},
            repo_root=tmp_path,
        )


def test_cache_key_is_place_vintage_policy_not_historical_sha() -> None:
    key = geography_cache_key(place_geoid="0455000")
    other = geography_cache_key(
        place_geoid="0455000",
        census_vintage="TIGER2025",
        resolver_policy_version=FROZEN_CANDIDATE_RESOLVER_POLICY_VERSION,
    )
    assert key == other
    assert len(key) == 64
    identity = geography_cache_identity(place_geoid="0455000")
    assert set(identity) == {
        "identity_version",
        "canonical_place_geoid",
        "census_vintage",
        "resolver_policy_version",
    }
    assert identity["census_vintage"] == DEFAULT_CENSUS_VINTAGE
    names = geography_cache_key.__code__.co_varnames
    assert "reference_sha256" not in names
    assert "historical" not in names
    with pytest.raises(TypeError):
        geography_cache_key(  # type: ignore[call-arg]
            place_geoid="0455000",
            reference_sha256="00" * 32,
        )
    assert geography_cache_key(place_geoid="1714000") != key
    assert (
        geography_cache_key(
            place_geoid="0455000",
            resolver_policy_version="NATIONAL_PLACE_GEOGRAPHY_V2",
        )
        != key
    )


def test_r5_f2_tract_geoid_must_be_11_digits_and_match_place_state() -> None:
    assert validate_tract_geoid("04013107800", place_geoid="0455000") == "04013107800"
    with pytest.raises(TractGeoidError, match="11-digit"):
        validate_tract_geoid("04013", place_geoid="0455000")
    with pytest.raises(TractGeoidError, match="11-digit"):
        validate_tract_geoid("not-a-geoid")
    with pytest.raises(TractGeoidError, match="STATEFP"):
        validate_tract_geoid("17031000000", place_geoid="0455000")
    cleaned = require_resolve_tract_geoids(
        [{"GEOID": f"0401310{i:04d}"} for i in range(25)],
        place_geoid="0455000",
    )
    assert len(cleaned) == 25
    assert cleaned[0] == "04013100000"
    with pytest.raises(TractGeoidError, match="missing GEOID"):
        require_resolve_tract_geoids([{"name": "x"}], place_geoid="0455000")


def test_fetch_off_cache_miss_does_not_call_transport(tmp_path: Path) -> None:
    transport = RecordingTransport({})

    def boom(url: str) -> CensusHttpResponse:
        raise AssertionError(f"live Census GET attempted: {url}")

    transport.get = boom  # type: ignore[method-assign]
    with pytest.raises(CensusFetchDisabled) as exc:
        ensure_state_tiger(
            "10",
            cache_root=tmp_path / "geo",
            transport=transport,
        )
    assert exc.value.code == CENSUS_FETCH_DISABLED
    assert transport.urls == []


def test_fetch_off_never_constructs_httpx_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("httpx.Client constructed")

    monkeypatch.setattr("httpx.Client", boom)
    with pytest.raises(CensusFetchDisabled):
        ensure_state_tiger("10", cache_root=tmp_path / "geo")


def test_fetch_on_uses_injected_transport_and_writes_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HVA_CENSUS_FETCH", "1")
    tract = _tiger_zip("10", "tract")
    place = _tiger_zip("10", "place")
    transport = RecordingTransport(
        {
            tiger_tract_zip_url(census_vintage="TIGER2025", state_fips="10"): tract,
            tiger_place_zip_url(census_vintage="TIGER2025", state_fips="10"): place,
        }
    )
    cache = tmp_path / "geo"
    artifacts = ensure_state_tiger(
        "10",
        cache_root=cache,
        transport=transport,
        enforce_known_lengths=False,
    )
    assert artifacts.tract_zip.is_file()
    assert artifacts.place_zip.is_file()
    assert artifacts.source_path.is_file()
    assert artifacts.tract_zip.parent == tiger_state_dir("10", cache_root=cache)
    document = json.loads(artifacts.source_path.read_text(encoding="utf-8"))
    assert document["census_vintage"] == "TIGER2025"
    assert document["artifacts"]["tract"]["sha256"] == hashlib.sha256(tract).hexdigest()
    assert "reference" not in json.dumps(document).lower()
    first_urls = list(transport.urls)

    again = ensure_state_tiger(
        "10",
        cache_root=cache,
        transport=transport,
        fetch=False,
    )
    assert again.tract_zip == artifacts.tract_zip
    assert transport.urls == first_urls


def test_known_length_mismatch_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HVA_CENSUS_FETCH", "1")
    transport = RecordingTransport(
        {
            tiger_tract_zip_url(census_vintage="TIGER2025", state_fips="04"): _tiger_zip(
                "04", "tract"
            ),
            tiger_place_zip_url(census_vintage="TIGER2025", state_fips="04"): _tiger_zip(
                "04", "place"
            ),
        }
    )
    with pytest.raises(CensusSourceMismatch, match="pinned"):
        ensure_state_tiger(
            "04",
            cache_root=tmp_path / "geo",
            transport=transport,
            enforce_known_lengths=True,
        )


def test_missing_content_length_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HVA_CENSUS_FETCH", "1")

    class NoLength:
        def get(self, url: str) -> CensusHttpResponse:
            return CensusHttpResponse(200, _tiger_zip("10", "tract"), {})

    with pytest.raises(CensusSourceUnavailable, match="Content-Length"):
        ensure_state_tiger(
            "10",
            cache_root=tmp_path / "geo",
            transport=NoLength(),
            enforce_known_lengths=False,
        )


def test_runtime_modules_have_no_vendor_or_workforce_defaults() -> None:
    root = repository_root()
    paths = [
        root / "apps" / "api" / "app" / "services" / "census_runtime.py",
        root / "apps" / "api" / "app" / "services" / "tiger_state_cache.py",
        root / "apps" / "api" / "app" / "core" / "geography_paths.py",
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "from app.integrations.fortyguard" not in source
        assert "fortyguard_api_key" not in source
        assert "national_resolver/_cache" not in source
        assert "workforce/national_resolver" not in source
        assert ".cache/fortyguard" not in source or path.name == "geography_paths.py"
    geo_source = paths[2].read_text(encoding="utf-8")
    assert "DEFAULT_VENDOR_CACHE" in geo_source
    assert "DEFAULT_LOCAL_GEOGRAPHY_CACHE" in geo_source
