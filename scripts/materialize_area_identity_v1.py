#!/usr/bin/env python3
"""Materialize offline AREA_IDENTITY_V1 packages from committed geometry."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "geography" / "area_identity"

CITY_META = {
    "phoenix-local": {
        "city_id": "phoenix-az-local",
        "city_label": "Phoenix, AZ",
        "geography_kind": "local_analysis",
        "secondary_prefix": "Local analysis",
        "geometry": ROOT / "data" / "areas" / "phoenix-demo" / "geometry.geojson",
        "area_config": ROOT / "data" / "demo" / "phoenix" / "area_config.json",
    },
    "cross-city/phoenix": {
        "city_id": "phoenix-az",
        "city_label": "Phoenix, AZ",
        "geography_kind": "cross_city_comparison",
        "secondary_prefix": "Comparison area",
        "geometry": ROOT / "data" / "areas" / "cross-city" / "phoenix" / "geometry.geojson",
        "area_config": ROOT / "data" / "areas" / "cross-city" / "phoenix" / "area_config.json",
    },
    "cross-city/las_vegas": {
        "city_id": "las-vegas-nv",
        "city_label": "Las Vegas, NV",
        "geography_kind": "cross_city_comparison",
        "secondary_prefix": "Comparison area",
        "geometry": ROOT / "data" / "areas" / "cross-city" / "las_vegas" / "geometry.geojson",
        "area_config": ROOT / "data" / "areas" / "cross-city" / "las_vegas" / "area_config.json",
    },
    "cross-city/tucson": {
        "city_id": "tucson-az",
        "city_label": "Tucson, AZ",
        "geography_kind": "cross_city_comparison",
        "secondary_prefix": "Comparison area",
        "geometry": ROOT / "data" / "areas" / "cross-city" / "tucson" / "geometry.geojson",
        "area_config": ROOT / "data" / "areas" / "cross-city" / "tucson" / "area_config.json",
    },
    "cross-city/los_angeles": {
        "city_id": "los-angeles-ca",
        "city_label": "Los Angeles, CA",
        "geography_kind": "cross_city_comparison",
        "secondary_prefix": "Comparison area",
        "geometry": ROOT / "data" / "areas" / "cross-city" / "los_angeles" / "geometry.geojson",
        "area_config": ROOT / "data" / "areas" / "cross-city" / "los_angeles" / "area_config.json",
    },
}

PHOENIX_LOCAL_ORDER = [
    "04013107401",
    "04013107500",
    "04013107601",
    "04013107602",
    "04013108802",
    "04013108602",
    "04013108601",
    "04013117100",
    "04013108501",
    "04013107700",
    "04013108502",
    "04013107404",
    "04013107403",
    "04013107402",
    "04013108902",
    "04013108901",
    "04013106703",
    "04013106600",
    "04013106501",
    "04013106502",
    "04013106400",
    "04013106702",
    "04013106701",
    "04013107800",
    "04013108400",
]


def format_tract_from_geoid(geoid: str) -> tuple[str, str]:
    geoid = str(geoid).zfill(11)
    tractce = geoid[-6:]
    suffix = tractce[-2:]
    prefix = tractce[:-2].lstrip("0") or "0"
    short = f"{prefix}.{suffix}"
    return short, f"Census Tract {short}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def materialize(key: str, meta: dict) -> dict:
    geom_path: Path = meta["geometry"]
    geom_raw = geom_path.read_bytes()
    geom = json.loads(geom_raw.decode("utf-8"))
    by_geoid = {
        str(feat["properties"]["GEOID"]).zfill(11): feat["properties"]
        for feat in geom["features"]
    }
    if key == "phoenix-local":
        order = PHOENIX_LOCAL_ORDER
    else:
        cfg = json.loads(meta["area_config"].read_text(encoding="utf-8"))
        order = [str(g).zfill(11) for g in cfg["expected_zone_ids"]]

    geometry_version = None
    if meta["area_config"].exists():
        cfg = json.loads(meta["area_config"].read_text(encoding="utf-8"))
        geometry_version = cfg.get("zone_geometry_version")

    identities: list[dict] = []
    for idx, geoid in enumerate(order, start=1):
        props = by_geoid[geoid]
        short_from_geoid, namelsad_from_geoid = format_tract_from_geoid(geoid)
        raw_namelsad = str(props.get("NAMELSAD") or "").strip()
        raw_name = str(props.get("NAME") or "").strip()
        if raw_namelsad.startswith("Census Tract ") and "." in raw_namelsad:
            display_name = raw_namelsad
            short_name = raw_name if "." in raw_name else short_from_geoid
            name_source = "census_tiger_namelsad"
            fallback_level = 2
        else:
            display_name = namelsad_from_geoid
            short_name = short_from_geoid
            name_source = "census_geoid_tract_format"
            fallback_level = 3
        identities.append(
            {
                "area_id": geoid,
                "city_id": meta["city_id"],
                "geoid": geoid,
                "display_name": display_name,
                "short_name": short_name,
                "secondary_label": f"{meta['secondary_prefix']} · {meta['city_label']}",
                "name_source": name_source,
                "name_source_version": "AREA_IDENTITY_V1",
                "name_confidence": "high" if fallback_level <= 2 else "medium",
                "geometry_version": geometry_version,
                "fallback_level": fallback_level,
                "internal_index": idx,
                "geography_kind": meta["geography_kind"],
                "method_detail": (
                    f"{meta['secondary_prefix']} {idx} · GEOID {geoid}"
                ),
            }
        )

    # Disambiguate duplicate primary labels within the package.
    counts: dict[str, int] = {}
    for row in identities:
        counts[row["display_name"]] = counts.get(row["display_name"], 0) + 1
    for row in identities:
        if counts[row["display_name"]] > 1:
            row["display_name"] = f"{row['display_name']} · Tract {row['short_name']}"

    counts2: dict[str, int] = {}
    for row in identities:
        counts2[row["display_name"]] = counts2.get(row["display_name"], 0) + 1
    for row in identities:
        if counts2[row["display_name"]] > 1:
            row["display_name"] = f"{row['short_name']} · Tract {row['short_name']}"

    payload = {
        "schema": "AREA_IDENTITY_V1",
        "city_id": meta["city_id"],
        "city_label": meta["city_label"],
        "geography_kind": meta["geography_kind"],
        "materialized_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "source": {
            "geometry_path": str(geom_path.relative_to(ROOT)).replace("\\", "/"),
            "zone_source": "U.S. Census Bureau TIGER/Line Census Tracts",
            "naming_hierarchy": [
                "authoritative neighborhood/district (none packaged)",
                "census NAMELSAD when well-formed",
                "census tract label from GEOID",
                "generic Comparison/Analysis Area N (method detail only)",
            ],
            "fortyguard_names": "NO",
        },
        "geometry_hash": sha256_bytes(geom_raw),
        "mapping_hash": sha256_bytes(
            json.dumps(
                [f"{r['geoid']}:{r['display_name']}" for r in identities],
                separators=(",", ":"),
            ).encode()
        ),
        "name_source_version": "AREA_IDENTITY_V1",
        "geometry_version": geometry_version,
        "areas": identities,
    }
    out_dir = OUT / key
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "identities.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(
        key,
        "areas",
        len(identities),
        "sample",
        identities[0]["display_name"],
        "|",
        identities[0]["secondary_label"],
    )
    return payload


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key, meta in CITY_META.items():
        materialize(key, meta)
    manifest = {
        "schema": "AREA_IDENTITY_V1",
        "packages": list(CITY_META.keys()),
        "materialized_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "notes": (
            "Offline replay package. No live reverse-geocoding. "
            "FortyGuard is thermal evidence source only."
        ),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / "AREA_IDENTITY_V1.md").write_text(
        """# AREA_IDENTITY_V1

Public UI primary label: `display_name` (Census tract NAMELSAD / GEOID-derived tract label).

Machine id: `area_id` (= GEOID). Keep stable for provenance.

Secondary: geography kind · City, State.

Naming hierarchy:
1. Authoritative neighborhood/district — **none packaged** (no invented names)
2. Census NAMELSAD when well-formed (contains decimal)
3. Census tract label derived from GEOID (`Census Tract 123.45`)
4. Generic Analysis/Comparison Area N — method detail only, not primary UI

Phoenix local vs cross-city Phoenix are **distinct** packages with distinct secondary labels.

FortyGuard area names: **NO** — FG remains thermal evidence source only.
""",
        encoding="utf-8",
    )

    # Emit a web-importable registry so the UI stays offline without Vite data aliases.
    web_out = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "features"
        / "areaIdentity"
        / "generatedRegistry.ts"
    )
    web_out.parent.mkdir(parents=True, exist_ok=True)
    packages_payload = {}
    for key in CITY_META:
        packages_payload[key] = json.loads(
            (OUT / key / "identities.json").read_text(encoding="utf-8")
        )
    web_out.write_text(
        "/* Generated by scripts/materialize_area_identity_v1.py — do not edit by hand. */\n"
        "export const AREA_IDENTITY_REGISTRY = "
        + json.dumps(packages_payload, indent=2)
        + " as const;\n",
        encoding="utf-8",
    )
    print("web registry", web_out)
    print("done", OUT)


if __name__ == "__main__":
    main()
