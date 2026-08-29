"""Replay mode never calls the network. LIVE without a key raises a typed error."""

from __future__ import annotations

import httpx
import pytest

from app.integrations.fortyguard.adapter import FortyGuardAdapter
from app.integrations.fortyguard.exceptions import MissingApiKeyError
from app.integrations.fortyguard.transport_models import DataMode

from .helpers import request_from_fixture


def test_replay_never_calls_httpx(
    monkeypatch: pytest.MonkeyPatch, hourly_tcm_fixture: dict, fixture_dir
) -> None:
    def _boom(*_args, **_kwargs):
        raise AssertionError("httpx must not be used in REPLAY mode")

    monkeypatch.setattr(httpx.Client, "request", _boom)
    monkeypatch.setattr(httpx.Client, "send", _boom)
    monkeypatch.setattr(httpx, "request", _boom)
    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "post", _boom)

    adapter = FortyGuardAdapter(api_key=None, fixture_dir=fixture_dir)
    req = request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.REPLAY)
    result = adapter.fetch_heatmap(req)
    assert result.tiles


def test_live_without_key_raises_typed_error(hourly_tcm_fixture: dict, fixture_dir) -> None:
    adapter = FortyGuardAdapter(api_key=None, fixture_dir=fixture_dir)
    req = request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.LIVE)
    with pytest.raises(MissingApiKeyError):
        adapter.fetch_heatmap(req)


def test_live_with_empty_key_raises_typed_error(hourly_tcm_fixture: dict, fixture_dir) -> None:
    adapter = FortyGuardAdapter(api_key="   ", fixture_dir=fixture_dir)
    req = request_from_fixture(hourly_tcm_fixture, data_mode=DataMode.LIVE)
    with pytest.raises(MissingApiKeyError):
        adapter.fetch_heatmap(req)
