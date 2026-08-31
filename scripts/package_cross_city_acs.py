#!/usr/bin/env python3
"""Package ACS 5-year 2020–2024 for all cross-city comparison tracts.

Uses Census table-based Summary File on www2.census.gov (no API key).
No FortyGuard. Writes data/context/cross-city/.
"""

from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO / "data" / "areas" / "cross-city" / "INDEX.json"
OUT_DIR = REPO / "data" / "context" / "cross-city"

ACS_YEAR = 2024
ACS_VINTAGE_LABEL = "ACS 5-year 2020-2024"
ACS_BASE = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/"
    f"{ACS_YEAR}/table-based-SF/data/5YRData"
)
USER_AGENT = "HVA-Signal/0.1 (cross-city-acs; free Census SF)"
TABLES = ("b01001", "b19013", "b11001", "b25034")
_CENSUS_MISSING = frozenset(
    {-666666666, -222222222, -333333333, -555555555, -888888888, -999999999}
)
PRE1980_E = ("B25034_E007", "B25034_E008", "B25034_E009", "B25034_E010", "B25034_E011")
PRE1980_M = ("B25034_M007", "B25034_M008", "B25034_M009", "B25034_M010", "B25034_M011")


def _http_stream_lines(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            yield raw.decode("utf-8", errors="replace").rstrip("\n")


def parse_acs_number(raw: str) -> float | None:
    text = raw.strip()
    if not text or text in {".", "null", "NA"}:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    if int(value) in _CENSUS_MISSING:
        return None
    if abs(value) >= 111111111:
        return None
    return value


def extract_acs_table(table: str, wanted_geo_ids: set[str]) -> dict[str, dict[str, float | None]]:
    url = f"{ACS_BASE}/acsdt5y{ACS_YEAR}-{table}.dat"
    print(f"ACS stream {table} <- {url}", flush=True)
    rows: dict[str, dict[str, float | None]] = {}
    header: list[str] | None = None
    for line in _http_stream_lines(url):
        if not line:
            continue
        parts = line.split("|")
        if header is None:
            header = parts
            continue
        geo_id = parts[0]
        if geo_id not in wanted_geo_ids:
            continue
        record: dict[str, float | None] = {}
        for name, cell in zip(header[1:], parts[1:], strict=False):
            record[name] = parse_acs_number(cell)
        rows[geo_id] = record
        if len(rows) == len(wanted_geo_ids):
            break
    print(f"  kept {len(rows)} / {len(wanted_geo_ids)}", flush=True)
    return rows


def _moe_sum(moes: list[float | None]) -> float | None:
    parts = [m for m in moes if m is not None and m >= 0]
    if not parts:
        return None
    return math.sqrt(sum(m * m for m in parts))


def eligibility(estimate: float | None, moe: float | None) -> bool:
    if estimate is None:
        return False
    if moe is None:
        return True
    if estimate == 0:
        return moe == 0
    return (moe / abs(estimate)) <= 0.5


def build_row(geoid: str, tables: dict[str, dict[str, dict[str, float | None]]]) -> dict[str, Any]:
    geo_id = f"1400000US{geoid}"
    source = {
        "dataset": f"acsdt5y{ACS_YEAR}",
        "vintage": ACS_VINTAGE_LABEL,
        "url_base": ACS_BASE,
    }
    b01 = tables["b01001"].get(geo_id, {})
    b19 = tables["b19013"].get(geo_id, {})
    b11 = tables["b11001"].get(geo_id, {})
    b25 = tables["b25034"].get(geo_id, {})
    pop_e, pop_m = b01.get("B01001_E001"), b01.get("B01001_M001")
    inc_e, inc_m = b19.get("B19013_E001"), b19.get("B19013_M001")
    hh_e, hh_m = b11.get("B11001_E001"), b11.get("B11001_M001")
    one_e, one_m = b11.get("B11001_E008"), b11.get("B11001_M008")
    total_e, total_m = b25.get("B25034_E001"), b25.get("B25034_M001")
    pre_vals = [b25.get(k) for k in PRE1980_E]
    pre_m_vals = [b25.get(k) for k in PRE1980_M]
    pre_e = None if any(v is None for v in pre_vals) else float(sum(v for v in pre_vals if v is not None))
    pre_m = _moe_sum(pre_m_vals)
    older_share = (
        (pre_e / float(total_e)) if pre_e is not None and total_e not in (None, 0) else None
    )
    one_share = (
        (one_e / float(hh_e)) if one_e is not None and hh_e not in (None, 0) else None
    )
    return {
        "geoid": geoid,
        "population": {
            "estimate": pop_e,
            "moe": pop_m,
            "comparison_eligible": eligibility(pop_e, pop_m),
            "source": source,
            "vintage": ACS_VINTAGE_LABEL,
            "variable": "B01001_001",
        },
        "median_household_income": {
            "estimate": inc_e,
            "moe": inc_m,
            "comparison_eligible": eligibility(inc_e, inc_m),
            "source": source,
            "vintage": ACS_VINTAGE_LABEL,
            "variable": "B19013_001",
        },
        "homes_built_before_1980": {
            "estimate": pre_e,
            "moe": pre_m,
            "share_of_units": older_share,
            "total_units_estimate": total_e,
            "total_units_moe": total_m,
            "comparison_eligible": eligibility(pre_e, pre_m),
            "source": source,
            "vintage": ACS_VINTAGE_LABEL,
            "variables": list(PRE1980_E),
        },
        "one_person_households": {
            "estimate": one_e,
            "moe": one_m,
            "share_of_households": one_share,
            "total_households_estimate": hh_e,
            "total_households_moe": hh_m,
            "comparison_eligible": eligibility(one_e, one_m),
            "source": source,
            "vintage": ACS_VINTAGE_LABEL,
            "variable": "B11001_008",
        },
    }


def main() -> int:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wanted: set[str] = set()
    for city in index["cities"]:
        for geoid in city["exact_tract_geoids"]:
            wanted.add(f"1400000US{geoid}")
    tables = {table: extract_acs_table(table, wanted) for table in TABLES}
    cities_meta = []
    for city in index["cities"]:
        rows = {
            geoid: build_row(geoid, tables) for geoid in city["exact_tract_geoids"]
        }
        missing = [
            g for g, row in rows.items() if row["population"]["estimate"] is None
        ]
        doc = {
            "city_id": city["city_id"],
            "place_geoid": city["place_geoid"],
            "tract_count": len(rows),
            "missing_population_geoids": missing,
            "rows": rows,
        }
        path = OUT_DIR / f"{city['city_id']}.json"
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cities_meta.append(
            {
                "city_id": city["city_id"],
                "path": str(path.relative_to(REPO).as_posix()),
                "tract_count": len(rows),
                "missing_population": len(missing),
            }
        )
        print(f"OK {city['city_id']}: tracts={len(rows)} missing_pop={len(missing)}")

    manifest = {
        "contract_version": "CROSS_CITY_ACS_CONTEXT_V1",
        "requested_vintage": ACS_VINTAGE_LABEL,
        "resolved_vintage": ACS_VINTAGE_LABEL,
        "resolved_year": ACS_YEAR,
        "vintage_matches_request": True,
        "source": ACS_BASE,
        "mixed_vintage": False,
        "cities": cities_meta,
    }
    (OUT_DIR / "SOURCE.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0 if all(c["missing_population"] == 0 for c in cities_meta) else 1


if __name__ == "__main__":
    raise SystemExit(main())
