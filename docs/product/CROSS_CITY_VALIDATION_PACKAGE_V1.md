# CROSS_CITY_VALIDATION_PACKAGE_V1

- Target local timestamp: `2024-07-08T15:00:00`
- Calls actually made: `0`
- Credits label: `ESTIMATE_NOT_VENDOR_QUOTE`
- Heuristic: `partition_count + ceil(expected_tiles_estimate / 5000)`

## City Plan

- Phoenix: reuse activity `92086c4c-1550-4263-8ac8-9a6c9e030bc4`; no new Type-1 call.
- Las Vegas: PROPOSED new Type-1 preflight only; estimated `52` credits; `16` partitions; `1750.144` km2 AOI estimate.
- Tucson: PROPOSED new Type-1 preflight only; estimated `39` credits; `12` partitions; `1312.18` km2 AOI estimate.
- LA: PROPOSED new Type-1 preflight only; estimated `102` credits; `30` partitions; `3593.786` km2 AOI estimate.

## Total

- Total projected credits: `193` (`ESTIMATE_NOT_VENDOR_QUOTE`)
- Scope: Las Vegas + Tucson + LA proposed new Type-1 requests only

## JSON

```json
{
  "calls_actually_made": 0,
  "cities": [
    {
      "activity_id": "92086c4c-1550-4263-8ac8-9a6c9e030bc4",
      "city": "Phoenix",
      "mode": "REUSE_EXISTING_ACTIVITY",
      "new_vendor_call_required": false,
      "preflight": null
    },
    {
      "city": "Las Vegas",
      "mode": "PROPOSED_NEW_TYPE1",
      "preflight": {
        "analysis_geography_version": "LAS_VEGAS_CITY_BBOX_V1",
        "aoi_area_estimate_km2": 1750.144,
        "aoi_owner": "server",
        "cache_fingerprint": "222c001cfe837fc12d49d77bb88d3c7ffc11ef254499afd25c4fff482f37240c",
        "city": "Las Vegas",
        "city_config_version": "MULTICITY_CITY_CONFIG_V1",
        "contract_version": "MULTICITY_TYPE1_LIVE_V1",
        "estimated_credits": {
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "ESTIMATE_NOT_VENDOR_QUOTE_V1",
          "label": "ESTIMATE_NOT_VENDOR_QUOTE",
          "value": 52
        },
        "expected_tiles_estimate": 175015,
        "hosted_live_enabled": false,
        "key_alias": "VALIDATION_B",
        "local_time": "2024-07-08T15:00:00",
        "metric": "TCM mean",
        "partition_count": 16,
        "provider_resolved_time": {
          "note": "Modeled as AOI-local wall time for single_hour/filter_type 1; no UTC conversion is sent by this disabled architecture.",
          "provider_payload_local_valid_time": "2024-07-08T15:00",
          "timezone": "America/Los_Angeles"
        },
        "real_vendor_enabled": false,
        "request_fingerprint": "3544558c0d1e9e6ade24d7a6e5adfcfd64959a8cc308d748d70cf9eef26e8042",
        "resolution": "100m",
        "rollback_behavior": "Dry-run and refusal paths consume no spend, make no vendor call, and persist no vendor output. Only an explicit server-seeded safe cache payload may be stored.",
        "vendor_stage": "disabled_refuse_real_vendor"
      }
    },
    {
      "city": "Tucson",
      "mode": "PROPOSED_NEW_TYPE1",
      "preflight": {
        "analysis_geography_version": "TUCSON_CITY_BBOX_V1",
        "aoi_area_estimate_km2": 1312.18,
        "aoi_owner": "server",
        "cache_fingerprint": "5baa60aac6e2e6242e52008d08baafab8f2f83952da9f43dbaeab21918530d4a",
        "city": "Tucson",
        "city_config_version": "MULTICITY_CITY_CONFIG_V1",
        "contract_version": "MULTICITY_TYPE1_LIVE_V1",
        "estimated_credits": {
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "ESTIMATE_NOT_VENDOR_QUOTE_V1",
          "label": "ESTIMATE_NOT_VENDOR_QUOTE",
          "value": 39
        },
        "expected_tiles_estimate": 131218,
        "hosted_live_enabled": false,
        "key_alias": "VALIDATION_B",
        "local_time": "2024-07-08T15:00:00",
        "metric": "TCM mean",
        "partition_count": 12,
        "provider_resolved_time": {
          "note": "Modeled as AOI-local wall time for single_hour/filter_type 1; no UTC conversion is sent by this disabled architecture.",
          "provider_payload_local_valid_time": "2024-07-08T15:00",
          "timezone": "America/Phoenix"
        },
        "real_vendor_enabled": false,
        "request_fingerprint": "dc429e54258957700f90a179ad493fcce315e2aeda1ea11f3eb3271d2c0c4fca",
        "resolution": "100m",
        "rollback_behavior": "Dry-run and refusal paths consume no spend, make no vendor call, and persist no vendor output. Only an explicit server-seeded safe cache payload may be stored.",
        "vendor_stage": "disabled_refuse_real_vendor"
      }
    },
    {
      "city": "LA",
      "mode": "PROPOSED_NEW_TYPE1",
      "preflight": {
        "analysis_geography_version": "LOS_ANGELES_CITY_BBOX_V1",
        "aoi_area_estimate_km2": 3593.786,
        "aoi_owner": "server",
        "cache_fingerprint": "906c799bf4406d8378d3105e9c826d578bd18a825d886ea094d75aae03c06321",
        "city": "Los Angeles",
        "city_config_version": "MULTICITY_CITY_CONFIG_V1",
        "contract_version": "MULTICITY_TYPE1_LIVE_V1",
        "estimated_credits": {
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "ESTIMATE_NOT_VENDOR_QUOTE_V1",
          "label": "ESTIMATE_NOT_VENDOR_QUOTE",
          "value": 102
        },
        "expected_tiles_estimate": 359379,
        "hosted_live_enabled": false,
        "key_alias": "VALIDATION_B",
        "local_time": "2024-07-08T15:00:00",
        "metric": "TCM mean",
        "partition_count": 30,
        "provider_resolved_time": {
          "note": "Modeled as AOI-local wall time for single_hour/filter_type 1; no UTC conversion is sent by this disabled architecture.",
          "provider_payload_local_valid_time": "2024-07-08T15:00",
          "timezone": "America/Los_Angeles"
        },
        "real_vendor_enabled": false,
        "request_fingerprint": "2591c0be02e2d0c8c72df3de83982bd17e57e31a24b0453c9994f772530f63d6",
        "resolution": "100m",
        "rollback_behavior": "Dry-run and refusal paths consume no spend, make no vendor call, and persist no vendor output. Only an explicit server-seeded safe cache payload may be stored.",
        "vendor_stage": "disabled_refuse_real_vendor"
      }
    }
  ],
  "estimated_credits_disclaimer": "ESTIMATE_NOT_VENDOR_QUOTE",
  "heuristic_formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
  "package_version": "CROSS_CITY_VALIDATION_PACKAGE_V1",
  "target_local": "2024-07-08T15:00:00",
  "total_projected_credits": {
    "label": "ESTIMATE_NOT_VENDOR_QUOTE",
    "scope": "Las Vegas + Tucson + LA proposed new Type-1 requests only",
    "value": 193
  }
}
```
