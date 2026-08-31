"""FortyGuard adapter orchestration (LIVE / REPLAY / AUTO)."""

from __future__ import annotations

import time
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx

from app.integrations.fortyguard.assembly import assemble_partitions
from app.integrations.fortyguard.cache import FortyGuardCache, ttl_for_heatmap_payload
from app.integrations.fortyguard.client import DEFAULT_BASE_URL, FortyGuardHttpClient
from app.integrations.fortyguard.exceptions import (
    FortyGuardAdapterError,
    MissingApiKeyError,
)
from app.integrations.fortyguard.fingerprints import heatmap_fingerprint
from app.integrations.fortyguard.mapper import map_heatmap_result
from app.integrations.fortyguard.partitioning import plan_partitions
from app.integrations.fortyguard.replay import ReplayStore
from app.integrations.fortyguard.temporal_modes import build_heatmap_payload
from app.integrations.fortyguard.transport_models import (
    ADAPTER_VERSION,
    AssemblyResult,
    DataMode,
    HeatmapFetchRequest,
    PartitionFetch,
    ThermalDataSource,
)

_DEFAULT_FIXTURE_DIR = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "fortyguard"
)


class FortyGuardAdapter:
    """All FortyGuard traffic goes through this adapter. Frontend never sees the key."""

    version = ADAPTER_VERSION

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        fixture_dir: str | Path | None = None,
        cache: FortyGuardCache | None = None,
        cache_dir: str | Path | None = None,
        transport: httpx.BaseTransport | None = None,
        poll_interval: float = 3.0,
        poll_timeout: float = 600.0,
        sleep: Callable[[float], None] = time.sleep,
        http_client: FortyGuardHttpClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.transport = transport
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self._sleep = sleep
        self._http_client = http_client
        self.cache = cache or FortyGuardCache(cache_dir or ".cache/fortyguard")
        self.replay = ReplayStore(fixture_dir or _DEFAULT_FIXTURE_DIR)

    def _has_key(self) -> bool:
        return bool(self.api_key and str(self.api_key).strip())

    def _ensure_http(self) -> FortyGuardHttpClient:
        if not self._has_key():
            raise MissingApiKeyError(
                "LIVE FortyGuard access requires FORTYGUARD_API_KEY on the backend."
            )
        if self._http_client is None:
            self._http_client = FortyGuardHttpClient(
                api_key=str(self.api_key).strip(),
                base_url=self.base_url,
                transport=self.transport,
            )
        return self._http_client

    def _fetch_live(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = self._ensure_http()
        return client.submit_and_wait(
            "/v1/heatmap",
            payload,
            poll_interval=self.poll_interval,
            timeout=self.poll_timeout,
            sleep=self._sleep,
        )

    def _from_replay_doc(self, doc: dict[str, Any]) -> dict[str, Any]:
        result = doc.get("result", doc)
        return {"activity_id": doc.get("activity_id"), "result": result}

    def _resolve(
        self,
        mode: DataMode,
        fingerprint: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], ThermalDataSource]:
        mode_value = mode.value if hasattr(mode, "value") else str(mode)

        # Cache-first for LIVE and AUTO. Identical fingerprint must never
        # re-submit Type-1 / heatmap; DataMode.LIVE previously bypassed cache
        # and always called _fetch_live (duplicate-spend failure mode).
        if mode_value in (DataMode.LIVE.value, DataMode.AUTO.value):
            cached = self.cache.get(fingerprint)
            if cached is not None:
                body, _layer = cached
                return body, ThermalDataSource.FORTYGUARD_CACHED

        if mode_value == DataMode.LIVE.value:
            bundled = self._fetch_live(payload)
            self.cache.put(
                fingerprint,
                bundled,
                ttl_seconds=ttl_for_heatmap_payload(payload),
            )
            return bundled, ThermalDataSource.FORTYGUARD_LIVE

        if mode_value == DataMode.REPLAY.value:
            doc = self.replay.require(fingerprint)
            return self._from_replay_doc(doc), ThermalDataSource.REPLAY

        # AUTO: miss path (cache already checked above)
        if self._has_key():
            try:
                bundled = self._fetch_live(payload)
                self.cache.put(
                    fingerprint,
                    bundled,
                    ttl_seconds=ttl_for_heatmap_payload(payload),
                )
                return bundled, ThermalDataSource.FORTYGUARD_LIVE
            except FortyGuardAdapterError:
                pass

        doc = self.replay.get(fingerprint)
        if doc is not None:
            return self._from_replay_doc(doc), ThermalDataSource.REPLAY
        raise MissingApiKeyError(
            "AUTO mode could not reach FortyGuard and no replay fixture matched."
        ) from None

    def fetch_heatmap(self, request: HeatmapFetchRequest) -> AssemblyResult:
        payload = build_heatmap_payload(request)
        plans = plan_partitions(request.polygon_aoi)
        fetches: list[PartitionFetch] = []
        fingerprints: list[str] = []
        for plan in plans:
            part_payload = deepcopy(payload)
            part_payload["polygon_aoi"] = plan.geometry
            fingerprint = heatmap_fingerprint(request, aoi=plan.geometry)
            fingerprints.append(fingerprint)
            bundled, source = self._resolve(request.data_mode, fingerprint, part_payload)
            result_body = bundled.get("result") or {}
            tiles = map_heatmap_result(
                result_body,
                request=request,
                source=source,
                partition_id=plan.partition_id,
            )
            fetches.append(
                PartitionFetch(
                    partition_id=plan.partition_id,
                    tiles=tiles,
                    source=source,
                    stats_data=result_body.get("stats_data") or {},
                )
            )
        return assemble_partitions(
            fetches,
            expected_partition_ids=[plan.partition_id for plan in plans],
            data_mode_requested=request.data_mode,
            upstream_payload=payload,
            fingerprint=fingerprints[0] if fingerprints else "",
        )
