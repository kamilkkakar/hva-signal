"""Analysis zone and upstream partition contracts."""

from typing import Any

from pydantic import BaseModel

GeoJSONGeometry = dict[str, Any]


class AnalysisZone(BaseModel):
    zone_id: str
    area_id: str
    geometry: GeoJSONGeometry
    geometry_version: str
    display_name: str | None = None
    source: str
    source_resolution: str | None = None
    area_km2: float


class UpstreamPartition(BaseModel):
    partition_id: str
    geometry: GeoJSONGeometry
    request_fingerprint: str
    expected_zone_ids: list[str]
