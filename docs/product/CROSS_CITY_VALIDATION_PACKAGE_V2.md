# CROSS_CITY_VALIDATION_PACKAGE_V2

- Target local timestamp: `2024-07-08T15:00:00`
- Observation contract: `CROSS_CITY_OBSERVATION_V1`
- Calls actually made: `0`
- Phoenix reuse: `NO` (Existing phoenix-demo surface and CROSS_CITY_COMPARISON_GEOGRAPHY_V1 Phoenix share zero tracts and zero spatial overlap.)
- Local complexity disclaimer: local_complexity_units are NOT vendor credits; historical 39/52/102 values were mislabelled.

## City Plan

- Phoenix: PROPOSED new Type-1; analysis `56.166699` km2; partitions `1`; expected tiles `5617`; local complexity units `3` (LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS); empirical sanity upper `9534` (NOT a vendor quote).
- Las Vegas: PROPOSED new Type-1; analysis `39.826665` km2; partitions `1`; expected tiles `3983`; local complexity units `2` (LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS); empirical sanity upper `6775` (NOT a vendor quote).
- Tucson: PROPOSED new Type-1; analysis `112.243142` km2; partitions `1`; expected tiles `11225`; local complexity units `4` (LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS); empirical sanity upper `19002` (NOT a vendor quote).
- Los Angeles: PROPOSED new Type-1; analysis `17.231457` km2; partitions `1`; expected tiles `1724`; local complexity units `2` (LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS); empirical sanity upper `2961` (NOT a vendor quote).

## Total

- Total new calls required: `4`
- Total conservative upper-bound spend proxy: `38272` (NOT_A_VENDOR_QUOTE; EMPIRICAL_SANITY_CHECK; confidence LOW)
- Ready for human authorization: `False`
- Blocker: Human must authorize the four-call package after reviewing V2 footprints and empirical sanity bounds. Three-call reuse assumption is withdrawn.

## JSON

```json
{
  "authorization_blocker": "Human must authorize the four-call package after reviewing V2 footprints and empirical sanity bounds. Three-call reuse assumption is withdrawn.",
  "calls_actually_made": 0,
  "cities": [
    {
      "activity_id": null,
      "analysis_area_km2": 56.166699,
      "bounding_envelope_area_km2": 76.514294,
      "cache_fingerprint": "b6c051c01b1fc20d537cc7eaa1dcb420c8bedcc1551ede0c0d4d2c7b427fef3a",
      "city": "Phoenix",
      "city_id": "phoenix",
      "confidence": "LOW",
      "conservative_upper_bound": 9534,
      "cost_model_output": {
        "estimate_type": "LOCAL_MODEL",
        "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
        "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
        "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
        "mislabelled_as_credits_historically": true,
        "not_vendor_credits": true,
        "units": "dimensionless_local_complexity_units",
        "value": 3,
        "variable_name": "local_complexity_units"
      },
      "dst_active": false,
      "empirical_sanity": {
        "basis": "scaled from Phoenix ~4220 debit / 3749 tiles; area=56.166699 km2",
        "confidence": "LOW",
        "conservative_upper_bound": 9534,
        "estimate_type": "EMPIRICAL_SANITY_CHECK",
        "phoenix_scaled_mid": 6322,
        "phoenix_scaled_range": [
          4426,
          9534
        ]
      },
      "expected_tile_cell_count": 5617,
      "final_analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
      "final_comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
      "freeze": {
        "analysis_area_count": 25,
        "area_config_hash": "756fd6be3680b75a7df4d5179923237a91de11df404c365dcc31aca5fd5ee4de",
        "combined_geometry_hash": "d3185750f2ef62d343702ea0ee80714f0dd81d0ae4a5fa01fee4a4d91be31c0f",
        "exact_tract_geoids": [
          "04013104501",
          "04013104502",
          "04013104402",
          "04013104600",
          "04013103615",
          "04013104401",
          "04013103614",
          "04013103900",
          "04013103605",
          "04013103609",
          "04013103612",
          "04013103604",
          "04013103608",
          "04013618800",
          "04013618900",
          "04013618700",
          "04013618600",
          "04013619100",
          "04013105502",
          "04013105400",
          "04013105300",
          "04013105503",
          "04013105501",
          "04013105601",
          "04013105602"
        ]
      },
      "key_alias": "VALIDATION_B",
      "local_time": "2024-07-08T15:00:00-07:00",
      "mode": "PROPOSED_NEW_TYPE1",
      "new_vendor_call_required": true,
      "overhead_envelope_vs_union_pct": 36.23,
      "partitions": 1,
      "phoenix_reuse": "NO",
      "preflight": {
        "analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
        "aoi_area_estimate_km2": 56.167,
        "aoi_owner": "server",
        "cache_fingerprint": "b6c051c01b1fc20d537cc7eaa1dcb420c8bedcc1551ede0c0d4d2c7b427fef3a",
        "city": "Phoenix",
        "city_config_version": "MULTICITY_CITY_CONFIG_V1",
        "comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
        "contract_version": "MULTICITY_TYPE1_LIVE_V1",
        "estimated_credits": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 3,
          "variable_name": "local_complexity_units"
        },
        "expected_tiles_estimate": 5617,
        "hosted_live_enabled": false,
        "key_alias": "VALIDATION_B",
        "local_complexity_estimate": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 3,
          "variable_name": "local_complexity_units"
        },
        "local_time": "2024-07-08T15:00:00",
        "metric": "TCM mean",
        "partition_count": 1,
        "provider_resolved_time": {
          "note": "Modeled as AOI-local wall time for single_hour/filter_type 1; no UTC conversion is sent by this disabled architecture.",
          "provider_payload_local_valid_time": "2024-07-08T15:00",
          "timezone": "America/Phoenix"
        },
        "real_vendor_enabled": false,
        "request_fingerprint": "56278314bbb6b9e49df3b3f255e74157da80a49ba2503f2ca7c8c147fcd4333c",
        "resolution": "100m",
        "rollback_behavior": "Dry-run and refusal paths consume no spend, make no vendor call, and persist no vendor output. Only an explicit server-seeded safe cache payload may be stored.",
        "vendor_stage": "disabled_refuse_real_vendor"
      },
      "provider_request_area_km2": 56.166699,
      "provider_time": "2024-07-08T15:00",
      "request_fingerprint": "56278314bbb6b9e49df3b3f255e74157da80a49ba2503f2ca7c8c147fcd4333c",
      "utc_timestamp": "2024-07-08T22:00:00+00:00"
    },
    {
      "activity_id": null,
      "analysis_area_km2": 39.826665,
      "bounding_envelope_area_km2": 52.179918,
      "cache_fingerprint": "dddfb9c06143932023e521dae89dbc1eb397c1100212b6d6ececdee12ad318fc",
      "city": "Las Vegas",
      "city_id": "las_vegas",
      "confidence": "LOW",
      "conservative_upper_bound": 6775,
      "cost_model_output": {
        "estimate_type": "LOCAL_MODEL",
        "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
        "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
        "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
        "mislabelled_as_credits_historically": true,
        "not_vendor_credits": true,
        "units": "dimensionless_local_complexity_units",
        "value": 2,
        "variable_name": "local_complexity_units"
      },
      "dst_active": true,
      "empirical_sanity": {
        "basis": "scaled from Phoenix ~4220 debit / 3749 tiles; area=39.826665 km2",
        "confidence": "LOW",
        "conservative_upper_bound": 6775,
        "estimate_type": "EMPIRICAL_SANITY_CHECK",
        "phoenix_scaled_mid": 4483,
        "phoenix_scaled_range": [
          3138,
          6775
        ]
      },
      "expected_tile_cell_count": 3983,
      "final_analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
      "final_comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
      "freeze": {
        "analysis_area_count": 25,
        "area_config_hash": "1e459a5e40e0f03e3dbe05361ea1574cebbff5f100f7a394f98c52f12f153853",
        "combined_geometry_hash": "4023d404b44da71b6f8e275c1295d5aa2d3781634741a1653fbe3158f3de062e",
        "exact_tract_geoids": [
          "32003003245",
          "32003003246",
          "32003003411",
          "32003003412",
          "32003003408",
          "32003003409",
          "32003003247",
          "32003003248",
          "32003003415",
          "32003003416",
          "32003003419",
          "32003003418",
          "32003003215",
          "32003003422",
          "32003003421",
          "32003003219",
          "32003003220",
          "32003003003",
          "32003003104",
          "32003003103",
          "32003003102",
          "32003003004",
          "32003003254",
          "32003003253",
          "32003003005"
        ]
      },
      "key_alias": "VALIDATION_B",
      "local_time": "2024-07-08T15:00:00-07:00",
      "mode": "PROPOSED_NEW_TYPE1",
      "new_vendor_call_required": true,
      "overhead_envelope_vs_union_pct": 31.02,
      "partitions": 1,
      "phoenix_reuse": "N/A",
      "preflight": {
        "analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
        "aoi_area_estimate_km2": 39.827,
        "aoi_owner": "server",
        "cache_fingerprint": "dddfb9c06143932023e521dae89dbc1eb397c1100212b6d6ececdee12ad318fc",
        "city": "Las Vegas",
        "city_config_version": "MULTICITY_CITY_CONFIG_V1",
        "comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
        "contract_version": "MULTICITY_TYPE1_LIVE_V1",
        "estimated_credits": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 2,
          "variable_name": "local_complexity_units"
        },
        "expected_tiles_estimate": 3983,
        "hosted_live_enabled": false,
        "key_alias": "VALIDATION_B",
        "local_complexity_estimate": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 2,
          "variable_name": "local_complexity_units"
        },
        "local_time": "2024-07-08T15:00:00",
        "metric": "TCM mean",
        "partition_count": 1,
        "provider_resolved_time": {
          "note": "Modeled as AOI-local wall time for single_hour/filter_type 1; no UTC conversion is sent by this disabled architecture.",
          "provider_payload_local_valid_time": "2024-07-08T15:00",
          "timezone": "America/Los_Angeles"
        },
        "real_vendor_enabled": false,
        "request_fingerprint": "a28a3c44299d71b19cfdf27e142ee2d904fdcc2fadb18181e75bcd36f0523c6e",
        "resolution": "100m",
        "rollback_behavior": "Dry-run and refusal paths consume no spend, make no vendor call, and persist no vendor output. Only an explicit server-seeded safe cache payload may be stored.",
        "vendor_stage": "disabled_refuse_real_vendor"
      },
      "provider_request_area_km2": 39.826665,
      "provider_time": "2024-07-08T15:00",
      "request_fingerprint": "a28a3c44299d71b19cfdf27e142ee2d904fdcc2fadb18181e75bcd36f0523c6e",
      "utc_timestamp": "2024-07-08T22:00:00+00:00"
    },
    {
      "activity_id": null,
      "analysis_area_km2": 112.243142,
      "bounding_envelope_area_km2": 183.162295,
      "cache_fingerprint": "af217e898e35b28f126abe5d2fac3b082f00fc5bbf035e1228d2896d3db9ea0e",
      "city": "Tucson",
      "city_id": "tucson",
      "confidence": "LOW",
      "conservative_upper_bound": 19002,
      "cost_model_output": {
        "estimate_type": "LOCAL_MODEL",
        "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
        "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
        "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
        "mislabelled_as_credits_historically": true,
        "not_vendor_credits": true,
        "units": "dimensionless_local_complexity_units",
        "value": 4,
        "variable_name": "local_complexity_units"
      },
      "dst_active": false,
      "empirical_sanity": {
        "basis": "scaled from Phoenix ~4220 debit / 3749 tiles; area=112.243142 km2",
        "confidence": "LOW",
        "conservative_upper_bound": 19002,
        "estimate_type": "EMPIRICAL_SANITY_CHECK",
        "phoenix_scaled_mid": 12635,
        "phoenix_scaled_range": [
          8844,
          19002
        ]
      },
      "expected_tile_cell_count": 11225,
      "final_analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
      "final_comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
      "freeze": {
        "analysis_area_count": 25,
        "area_config_hash": "4b2db80bc6c1098bbd6f0425ad38f85065bf137caecfa20ee92f6e87dd56eb9f",
        "combined_geometry_hash": "3455b3160a482b8dd2c33fff308b252b9285574fabd394c1f48a77d197d244b6",
        "exact_tract_geoids": [
          "04019980300",
          "04019003601",
          "04019004029",
          "04019004034",
          "04019004033",
          "04019004038",
          "04019004037",
          "04019004058",
          "04019004063",
          "04019004036",
          "04019004035",
          "04019004056",
          "04019004057",
          "04019003503",
          "04019003504",
          "04019004008",
          "04019004076",
          "04019004075",
          "04019004078",
          "04019004077",
          "04019003506",
          "04019003505",
          "04019003502",
          "04019003302",
          "04019004010"
        ]
      },
      "key_alias": "VALIDATION_B",
      "local_time": "2024-07-08T15:00:00-07:00",
      "mode": "PROPOSED_NEW_TYPE1",
      "new_vendor_call_required": true,
      "overhead_envelope_vs_union_pct": 63.18,
      "partitions": 1,
      "phoenix_reuse": "N/A",
      "preflight": {
        "analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
        "aoi_area_estimate_km2": 112.243,
        "aoi_owner": "server",
        "cache_fingerprint": "af217e898e35b28f126abe5d2fac3b082f00fc5bbf035e1228d2896d3db9ea0e",
        "city": "Tucson",
        "city_config_version": "MULTICITY_CITY_CONFIG_V1",
        "comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
        "contract_version": "MULTICITY_TYPE1_LIVE_V1",
        "estimated_credits": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 4,
          "variable_name": "local_complexity_units"
        },
        "expected_tiles_estimate": 11225,
        "hosted_live_enabled": false,
        "key_alias": "VALIDATION_B",
        "local_complexity_estimate": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 4,
          "variable_name": "local_complexity_units"
        },
        "local_time": "2024-07-08T15:00:00",
        "metric": "TCM mean",
        "partition_count": 1,
        "provider_resolved_time": {
          "note": "Modeled as AOI-local wall time for single_hour/filter_type 1; no UTC conversion is sent by this disabled architecture.",
          "provider_payload_local_valid_time": "2024-07-08T15:00",
          "timezone": "America/Phoenix"
        },
        "real_vendor_enabled": false,
        "request_fingerprint": "398f25b7771c7d075882ff77eff89428701f365316efe2e038ea1058d0b007bc",
        "resolution": "100m",
        "rollback_behavior": "Dry-run and refusal paths consume no spend, make no vendor call, and persist no vendor output. Only an explicit server-seeded safe cache payload may be stored.",
        "vendor_stage": "disabled_refuse_real_vendor"
      },
      "provider_request_area_km2": 112.243142,
      "provider_time": "2024-07-08T15:00",
      "request_fingerprint": "398f25b7771c7d075882ff77eff89428701f365316efe2e038ea1058d0b007bc",
      "utc_timestamp": "2024-07-08T22:00:00+00:00"
    },
    {
      "activity_id": null,
      "analysis_area_km2": 17.231457,
      "bounding_envelope_area_km2": 35.632744,
      "cache_fingerprint": "c4c45a39ffcbdda85fb04ae23169f72b50d5e8d7cd8244842a22179197579034",
      "city": "Los Angeles",
      "city_id": "los_angeles",
      "confidence": "LOW",
      "conservative_upper_bound": 2961,
      "cost_model_output": {
        "estimate_type": "LOCAL_MODEL",
        "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
        "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
        "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
        "mislabelled_as_credits_historically": true,
        "not_vendor_credits": true,
        "units": "dimensionless_local_complexity_units",
        "value": 2,
        "variable_name": "local_complexity_units"
      },
      "dst_active": true,
      "empirical_sanity": {
        "basis": "scaled from Phoenix ~4220 debit / 3749 tiles; area=17.231457 km2",
        "confidence": "LOW",
        "conservative_upper_bound": 2961,
        "estimate_type": "EMPIRICAL_SANITY_CHECK",
        "phoenix_scaled_mid": 1941,
        "phoenix_scaled_range": [
          1358,
          2961
        ]
      },
      "expected_tile_cell_count": 1724,
      "final_analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
      "final_comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
      "freeze": {
        "analysis_area_count": 25,
        "area_config_hash": "0a8473fbe6fff86aa99f6775a2345443187ea1ccd7741754a03350e777450bab",
        "combined_geometry_hash": "7049e495115c3f6aeece5000198cd22ef4b616bc78da9f0b778a1781a39d488c",
        "exact_tract_geoids": [
          "06037271803",
          "06037271804",
          "06037271801",
          "06037271901",
          "06037271902",
          "06037271500",
          "06037271600",
          "06037271702",
          "06037271300",
          "06037271703",
          "06037271704",
          "06037271200",
          "06037271100",
          "06037267800",
          "06037269909",
          "06037269908",
          "06037269903",
          "06037269907",
          "06037269906",
          "06037269905",
          "06037270102",
          "06037269300",
          "06037267902",
          "06037269000",
          "06037270101"
        ]
      },
      "key_alias": "VALIDATION_B",
      "local_time": "2024-07-08T15:00:00-07:00",
      "mode": "PROPOSED_NEW_TYPE1",
      "new_vendor_call_required": true,
      "overhead_envelope_vs_union_pct": 106.79,
      "partitions": 1,
      "phoenix_reuse": "N/A",
      "preflight": {
        "analysis_geography_version": "MULTI_CITY_ANALYSIS_GEOGRAPHY_V1",
        "aoi_area_estimate_km2": 17.231,
        "aoi_owner": "server",
        "cache_fingerprint": "c4c45a39ffcbdda85fb04ae23169f72b50d5e8d7cd8244842a22179197579034",
        "city": "Los Angeles",
        "city_config_version": "MULTICITY_CITY_CONFIG_V1",
        "comparison_geography_version": "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
        "contract_version": "MULTICITY_TYPE1_LIVE_V1",
        "estimated_credits": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 2,
          "variable_name": "local_complexity_units"
        },
        "expected_tiles_estimate": 1724,
        "hosted_live_enabled": false,
        "key_alias": "VALIDATION_B",
        "local_complexity_estimate": {
          "estimate_type": "LOCAL_MODEL",
          "formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
          "heuristic_version": "LOCAL_COMPLEXITY_HEURISTIC_V2",
          "label": "LOCAL_COMPLEXITY_UNITS_NOT_VENDOR_CREDITS",
          "mislabelled_as_credits_historically": true,
          "not_vendor_credits": true,
          "units": "dimensionless_local_complexity_units",
          "value": 2,
          "variable_name": "local_complexity_units"
        },
        "local_time": "2024-07-08T15:00:00",
        "metric": "TCM mean",
        "partition_count": 1,
        "provider_resolved_time": {
          "note": "Modeled as AOI-local wall time for single_hour/filter_type 1; no UTC conversion is sent by this disabled architecture.",
          "provider_payload_local_valid_time": "2024-07-08T15:00",
          "timezone": "America/Los_Angeles"
        },
        "real_vendor_enabled": false,
        "request_fingerprint": "93c8824afc862a4e04741418f4ede8937730c5d56c770521c4ce5e46242ec124",
        "resolution": "100m",
        "rollback_behavior": "Dry-run and refusal paths consume no spend, make no vendor call, and persist no vendor output. Only an explicit server-seeded safe cache payload may be stored.",
        "vendor_stage": "disabled_refuse_real_vendor"
      },
      "provider_request_area_km2": 17.231457,
      "provider_time": "2024-07-08T15:00",
      "request_fingerprint": "93c8824afc862a4e04741418f4ede8937730c5d56c770521c4ce5e46242ec124",
      "utc_timestamp": "2024-07-08T22:00:00+00:00"
    }
  ],
  "empirical_phoenix_calibration": {
    "activity_id": "92086c4c-1550-4263-8ac8-9a6c9e030bc4",
    "approx_debit_credits": 4220,
    "debit_per_partition": 4220,
    "debit_per_tile": 1.1256,
    "note": "Single-observation ratios. NOT a universal provider rate. NOT a vendor quote for other cities.",
    "partitions": 1,
    "resolution_m": 100,
    "tiles_returned": 3749
  },
  "heuristic_formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
  "local_complexity_disclaimer": "local_complexity_units are NOT vendor credits; historical 39/52/102 values were mislabelled.",
  "observation_contract": "CROSS_CITY_OBSERVATION_V1",
  "package_version": "CROSS_CITY_VALIDATION_PACKAGE_V2",
  "phoenix_reuse_proof": {
    "activity_id": "92086c4c-1550-4263-8ac8-9a6c9e030bc4",
    "approx_100m_cell_coverage_ratio": 0.0,
    "new_phoenix_call_needed": true,
    "reason": "Existing phoenix-demo surface and CROSS_CITY_COMPARISON_GEOGRAPHY_V1 Phoenix share zero tracts and zero spatial overlap.",
    "reusable": "NO",
    "tracts_fully_covered": "0 / 25",
    "tracts_not_covered": 25,
    "tracts_partially_covered": 0
  },
  "ready_for_human_authorization": false,
  "target_local": "2024-07-08T15:00:00",
  "total_conservative_upper_bound_spend": {
    "confidence": "LOW",
    "estimate_type": "EMPIRICAL_SANITY_CHECK",
    "label": "NOT_A_VENDOR_QUOTE",
    "scope": "Phoenix + Las Vegas + Tucson + Los Angeles proposed new Type-1",
    "units": "empirical_sanity_scaled_debit_proxy",
    "value": 38272
  },
  "total_new_calls_required": 4
}
```
