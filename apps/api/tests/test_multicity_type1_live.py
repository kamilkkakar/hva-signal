from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.hosted_live_policy import HostedLiveDisabledError, hosted_live_defaults_are_off
from app.domain.multicity.city_catalog import resolve_city_aoi
from app.domain.multicity.cross_city_canopy import (
    CROSS_CITY_CANOPY_CONTRACT_V1,
    CROSS_CITY_CANOPY_STATUS,
    cross_city_canopy_contract,
)
from app.domain.multicity.type1_live import (
    Type1LiveClientRequest,
    build_type1_request,
    construct_vendor_stage,
    dry_run_type1_preflight,
    run_type1_live,
    seed_type1_live_cache,
)
from app.domain.multicity.validation_package import (
    CALLS_ACTUALLY_MADE,
    build_cross_city_validation_package,
    render_cross_city_validation_package_markdown,
)
from app.integrations.fortyguard.cache import FortyGuardCache


def test_live_defaults_off() -> None:
    assert hosted_live_defaults_are_off() is True
    preflight = dry_run_type1_preflight(
        {"city": "Phoenix", "target_local": datetime(2024, 7, 8, 15, 0, 0)}
    )
    assert preflight["hosted_live_enabled"] is False
    assert preflight["real_vendor_enabled"] is False
    assert preflight["vendor_stage"] == "disabled_refuse_real_vendor"


def test_vendor_cannot_construct_when_refused() -> None:
    with pytest.raises(HostedLiveDisabledError):
        construct_vendor_stage()


def test_dry_run_preflight_shape() -> None:
    preflight = dry_run_type1_preflight(
        {
            "city": "Las Vegas",
            "target_local": datetime(2024, 7, 8, 15, 0, 0),
            "key_alias": "VALIDATION_B",
        }
    )
    assert preflight["city"] == "Las Vegas"
    assert preflight["city_config_version"] == "MULTICITY_CITY_CONFIG_V1"
    assert preflight["resolution"] == "100m"
    assert preflight["metric"] == "TCM mean"
    assert preflight["key_alias"] == "VALIDATION_B"
    assert preflight["local_complexity_estimate"]["label"] == "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS"
    assert preflight["partition_count"] >= 1
    assert preflight["expected_tiles_estimate"] >= preflight["partition_count"]
    assert "UTC" in preflight["provider_resolved_time"]["note"]


def test_cache_hit_path_skips_vendor(tmp_path) -> None:
    cache = FortyGuardCache(tmp_path / "multicity-cache")
    request = Type1LiveClientRequest(
        city="Phoenix",
        target_local=datetime(2024, 7, 8, 15, 0, 0),
    )
    seed_type1_live_cache(
        request,
        payload={
            "vendor_url": "https://api.fortyguard.com/v1/heatmap",
            "key": "should-not-leak",
            "summary": {"status": "cached_ok"},
        },
        cache=cache,
    )
    result = run_type1_live(request, cache=cache)
    blob = json.dumps(result, sort_keys=True)
    assert result["status"] == "cache_hit"
    assert result["vendor_attempted"] is False
    assert result["result"]["payload"]["summary"]["status"] == "cached_ok"
    assert "fortyguard.com" not in blob
    assert "should-not-leak" not in blob


def test_city_aoi_is_server_owned() -> None:
    request = Type1LiveClientRequest(
        city="Phoenix",
        target_local=datetime(2024, 7, 8, 15, 0, 0),
    )
    built = build_type1_request(request)
    assert built["aoi_owner"] == "server"
    assert built["polygon_aoi"] == resolve_city_aoi("Phoenix").polygon_aoi


def test_arbitrary_polygon_rejected() -> None:
    with pytest.raises(ValidationError, match="client-owned fields"):
        Type1LiveClientRequest.model_validate(
            {
                "city": "Phoenix",
                "target_local": "2024-07-08T15:00:00",
                "polygon_aoi": {"type": "Polygon", "coordinates": []},
            }
        )


def test_key_never_returned() -> None:
    preflight = dry_run_type1_preflight(
        {
            "city": "Tucson",
            "target_local": datetime(2024, 7, 8, 15, 0, 0),
            "key_alias": "PRIMARY",
        }
    )
    blob = json.dumps(preflight, sort_keys=True)
    assert preflight["key_alias"] == "PRIMARY"
    assert "fortyguard_api_key" not in blob
    assert '"key"' not in blob


def test_provider_url_never_returned() -> None:
    preflight = dry_run_type1_preflight(
        {"city": "LA", "target_local": datetime(2024, 7, 8, 15, 0, 0)}
    )
    blob = json.dumps(preflight, sort_keys=True)
    assert "provider_url" not in blob
    assert "base_url" not in blob
    assert "fortyguard.com" not in blob


def test_cross_city_canopy_contract_is_ready_without_phoenix_local_substitute() -> None:
    sys.modules.pop("app.services.vulnerability_preparedness.canopy", None)
    module = importlib.import_module("app.domain.multicity.cross_city_canopy")
    module = importlib.reload(module)
    contract = cross_city_canopy_contract()
    assert module.CROSS_CITY_CANOPY_CONTRACT_V1 == CROSS_CITY_CANOPY_CONTRACT_V1
    assert contract["contract_version"] == CROSS_CITY_CANOPY_CONTRACT_V1
    assert contract["status"] == CROSS_CITY_CANOPY_STATUS
    assert contract["silent_substitute_forbidden"] is True
    assert "app.services.vulnerability_preparedness.canopy" not in sys.modules


def test_validation_package_is_preflight_only() -> None:
    package = build_cross_city_validation_package()
    markdown = render_cross_city_validation_package_markdown(package)
    assert package["calls_actually_made"] == CALLS_ACTUALLY_MADE == 0
    assert package["package_version"] == "CROSS_CITY_VALIDATION_PACKAGE_V2"
    assert package["total_new_calls_required"] == 4
    assert package["phoenix_reuse_proof"]["reusable"] == "NO"
    assert "PROPOSED new Type-1" in markdown
    assert "local complexity units" in markdown.lower()
