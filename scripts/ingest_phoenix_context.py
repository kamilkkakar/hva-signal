"""One-shot ingest for Phoenix 25-zone contextual observations.

Reads official public sources, writes a runtime cache under
data/context/phoenix-demo/. Not imported by the API request path.

Sources:
- Census ACS 5-year 2020-2024 table-based Summary File (www2.census.gov)
- City of Phoenix Office of Heat Response shade-study tree canopy
  (ArcGIS MapServer, 2022 Google EIE aggregated to tract)
- MAG Heat Relief Network Regional Directory May-September 2026
  (azmag.gov), Census geocoder + point-in-polygon to TIGER 2025 zones

No combined score. Join misses stay UNKNOWN / NOT_IDENTIFIED_IN_DATASET.
"""

from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from shapely.validation import make_valid

REPO = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = REPO / "data" / "areas" / "phoenix-demo" / "geometry.geojson"
OUT_DIR = REPO / "data" / "context" / "phoenix-demo"

ACS_YEAR = 2024
ACS_VINTAGE_LABEL = "ACS 5-year 2020-2024"
ACS_AS_OF = "2024-07-01"
ACS_BASE = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/"
    f"{ACS_YEAR}/table-based-SF/data/5YRData"
)
PHOENIX_PLACE_GEOID = "0455000"
PHOENIX_PLACE_GEO_ID = f"1600000US{PHOENIX_PLACE_GEOID}"
CANOPY_LAYER = (
    "https://maps.phoenix.gov/pub/rest/services/Public/"
    "Shade_Study_Data_CMO_OHR/MapServer/1/query"
)
CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
INVENTORY_ID = "mag_hrn_2026_v1"
INVENTORY_AS_OF = "2026-05-05"
USER_AGENT = "hva-signal-phoenix-context/0.1 (research cache; not live scraping)"

# MAG Heat Relief Network — Phoenix rows from the 2026 regional directory.
# Hours are as published; completeness flags stay conservative.
MAG_PHOENIX_SITES: list[dict[str, str]] = [
    {"name": "1111 W. Hatcher", "address": "1111 W. Hatcher Rd. Phoenix AZ 85021", "hours": "Mo-Fr 9am-12pm", "phone": "480-384-0271"},
    {"name": "1818 W. Adams Cooling Pod", "address": "1818 W. Adams St. Phoenix AZ 85007", "hours": "Mo-Su 8am-8pm", "phone": "602-334-4331"},
    {"name": "20 W Jackson", "address": "20 W. Jackson St. Phoenix AZ 85003", "hours": "Open 24/7", "phone": "602-534-1837"},
    {"name": "23rd Avenue Recovery Center", "address": "8836 N. 23rd Ave. Phoenix AZ 85021", "hours": "Mo-Fr 8am-4:30pm", "phone": "602-685-6000"},
    {"name": "27th Avenue Integrated Care", "address": "3864 N. 27th Ave. Phoenix AZ 85017", "hours": "Mo-Fr 8am-4:30pm", "phone": "602-685-6093"},
    {"name": "51st Avenue Recovery Center", "address": "4616 N. 51st Ave. Phoenix AZ 85031", "hours": "Mo-Fr 8am-5pm", "phone": "602-685-6000"},
    {"name": "Acacia Library", "address": "750 E. Townley Ave. Phoenix AZ 85020", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 10am-6pm", "phone": "602-534-2026"},
    {"name": "Adam Diaz Senior Center", "address": "4115 W. Thomas Rd. Phoenix AZ 85019", "hours": "Mo-Fr 9am-3pm", "phone": "602-534-1177"},
    {"name": "Agave Library", "address": "23550 N. 36th Ave. Phoenix AZ 85310", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Andre House", "address": "213 S. 11th Ave. Phoenix AZ 85007", "hours": "Mo-Th 10am-4pm, Sa-Su 1pm-4pm", "phone": "602-255-0580"},
    {"name": "Arizona Friends of Homeless", "address": "1118 W. Glendale Ave. Phoenix AZ 85021", "hours": "Mo-Th 8am-1pm", "phone": "602-330-3403"},
    {"name": "Bret Tarver Learning Center", "address": "1516 N. 35th Ave. Phoenix AZ 85009", "hours": "Mo-Fr 1pm-7pm, Sa 10am-3pm", "phone": "602-262-7121"},
    {"name": "Burton Barr Central Library", "address": "1221 N. Central Ave. Phoenix AZ 85004", "hours": "Mo, Fr & Sa 9am-5pm; Tu-Th 9am-7pm; Su 12pm-5pm", "phone": "602-534-2026"},
    {"name": "Century Library", "address": "1750 E. Highland Ave. Phoenix AZ 85016", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 10am-6pm", "phone": "602-534-2026"},
    {"name": "Cesar Chavez Library", "address": "3635 W. Baseline Rd. Phoenix AZ 85339", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Chinese Senior Center", "address": "734 W. Elm St. Phoenix AZ 85013", "hours": "Mo-Fr 9am-3pm", "phone": "602-534-5099"},
    {"name": "Cholla Library", "address": "10050 E. Metro Pkwy. Phoenix AZ 85051", "hours": "Mo-Sa 9am-9pm, Su 12pm-9pm", "phone": "602-534-2026"},
    {"name": "Cielito Pool", "address": "4551 N. 35th Ave. Phoenix AZ 85017", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "City of Refuge", "address": "3147 N. Black Canyon Hwy Phoenix AZ 85015", "hours": "Mo-Fr 8am-5pm", "phone": "602-487-4599"},
    {"name": "Coronado Pool", "address": "1717 N. 12th St. Phoenix AZ 85006", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "Cortez Pool", "address": "3434 W. Dunlap Ave. Phoenix AZ 85051", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "DREAMreach Ministry", "address": "2205 E. Eugie Terrace Phoenix AZ 85022", "hours": "Mo-Sa 11am-5pm, Su 11am-4pm", "phone": "602-404-7465"},
    {"name": "De La Cruz Tire Shop", "address": "3001 N. 16th St. Phoenix AZ 85016", "hours": "Mo-Su 8am-7pm", "phone": "602-478-5855"},
    {"name": "Deer Valley Community Center", "address": "2001 W. Wahalla Ln. Phoenix AZ 85027", "hours": "Mo-Fr 9am-3pm", "phone": "602-495-3713"},
    {"name": "Deer Valley Pool", "address": "19400 N. 19th Ave. Phoenix AZ 85027", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "Desert Broom Library", "address": "29710 N. Cave Creek Rd. Phoenix AZ 85331", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Desert Cove Clinic (IHH)", "address": "10844 N. 23rd Ave. Phoenix AZ 85008", "hours": "Mo-Fr 8am-4:30pm", "phone": "602-685-6000"},
    {"name": "Desert Mission Health Center", "address": "9015 N. 3rd St. Phoenix AZ 85020", "hours": "Mo-Fr 7am-6pm", "phone": "575-914-0732"},
    {"name": "Desert Sage Library", "address": "7602 W. Encanto Blvd. Phoenix AZ 85035", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 10am-6pm", "phone": "602-534-2026"},
    {"name": "Desert West Community Center", "address": "6501 W. Virginia Ave. Phoenix AZ 85035", "hours": "Mo-Fr 9am-3pm", "phone": "602-495-3710"},
    {"name": "Devonshire Senior Center", "address": "2802 E. Devonshire Ave. Phoenix AZ 85016", "hours": "Mo-Fr 9am-3pm", "phone": "602-495-0905"},
    {"name": "Diamond Street Resource Center", "address": "1245 E Diamond St Phoenix AZ 85006", "hours": "Mo-Fr 1pm-5pm", "phone": "520-300-0618"},
    {"name": "Downtown Family Health Clinic", "address": "220 S. 12th Ave. Phoenix AZ 85007", "hours": "Mo 7am-8pm, Tu-Fr 7am-7pm, Sa-Su 8am-5pm", "phone": "951-205-0555"},
    {"name": "Eastlake Park Community Center", "address": "1549 E. Jefferson St. Phoenix AZ 85034", "hours": "Mo-Th 10am-9pm, Fr 10am-6pm, Sa 9am-7pm", "phone": "602-327-9032"},
    {"name": "El Prado Pool", "address": "6428 S. 19th Ave. Phoenix AZ 85042", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "Encanto Pool", "address": "2125 N. 15th Ave. Phoenix AZ 85006", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "FIBCO Family Services", "address": "1141 E. Jefferson St. Phoenix AZ 85034", "hours": "Tu,We & Fr 9am-2pm", "phone": "602-509-5869"},
    {"name": "Falcon Pool", "address": "3420 W. Roosevelt St. Phoenix AZ 85009", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "First Church UCC Phoenix", "address": "1407 N. 2nd St. Phoenix AZ 85004", "hours": "Mo 9am-5pm, Tu-We & Su 11am-7pm", "phone": "602-574-9645"},
    {"name": "Goelet A. C. Beuf Community Center", "address": "3435 W. Pinnacle Peak Rd. Phoenix AZ 85027", "hours": "Mo-Fr 9am-3pm", "phone": "602-534-9740"},
    {"name": "Grace Lutheran Church", "address": "1124 N. 3rd St. Phoenix AZ 85004", "hours": "Th-Sa 11am-7pm", "phone": "602-334-4331"},
    {"name": "Harmon Library", "address": "1325 S. 5th Ave. Phoenix AZ 85003", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 10am-6pm", "phone": "602-534-2026"},
    {"name": "Harmon Pool", "address": "1425 S. 5th Ave. Phoenix AZ 85003", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "Harmon Recreation Center", "address": "1425 S. 5th Ave. Phoenix AZ 85003", "hours": "Mo-Fr 4pm-7pm, Sa 8am-1pm", "phone": "602-327-9032"},
    {"name": "Hayden Neighborhood Recreation Center", "address": "420 W. Tamarisk Ave. Phoenix AZ 85041", "hours": "Mo-Fr 4pm-8pm", "phone": "602-327-9032"},
    {"name": "Helen Drake Senior Center", "address": "7600 N. 27th Ave. Phoenix AZ 85051", "hours": "Mo-Fr 9am-3pm", "phone": "602-534-6649"},
    {"name": "Heritage & Science Park Visitor Center", "address": "113 N. 6th St. Phoenix AZ 85004", "hours": "Th-Sa 10am-3:30pm, Su 12pm-3:30pm", "phone": "602-258-0048"},
    {"name": "Hermoso Pool", "address": "5749 S. 20th St. Phoenix AZ 85040", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "Holiday Park Recreation Center", "address": "4560 N. 67th Ave. Phoenix AZ 85035", "hours": "Mo-Fr 5pm-7pm", "phone": "602-495-0950"},
    {"name": "Ironwood Library", "address": "4333 E. Chandler Blvd. Phoenix AZ 85048", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "John F. Long Family Service Center", "address": "3454 N. 51st Ave. Phoenix AZ 85031", "hours": "Mo-Fr 8am-5pm", "phone": "602-262-6989"},
    {"name": "Juniper Library", "address": "1825 W. Union Hills Dr. Phoenix AZ 85027", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Justa Resource & Day Center", "address": "1001 W. Jefferson St. Phoenix AZ 85007", "hours": "Mo-Su 3pm-9pm", "phone": "602-783-2175"},
    {"name": "Key Campus Brian Garcia Welcome Center", "address": "204 S. 12th Ave. Phoenix AZ 85007", "hours": "Mo-Su 8am-11pm", "phone": "480-793-3615"},
    {"name": "Labor's Community Service Agency", "address": "3117 N. 16th St. Phoenix AZ 85016", "hours": "Mo-Fr 9am-4pm", "phone": "480-475-9932"},
    {"name": "Lincoln Family Downtown YMCA", "address": "350 N. 1st Ave. Phoenix AZ 85003", "hours": "Mo-Fr 7am-7pm", "phone": "602-885-8962"},
    {"name": "Longview Neighborhood Recreation Center", "address": "4040 N. 14th St. Phoenix AZ 85014", "hours": "Mo-Th 9am-9pm, Fr 9am-6pm, Sa 10am-6pm", "phone": "602-327-9032"},
    {"name": "Madison Pool", "address": "1440 E. Glenrosa Ave. Phoenix AZ 85013", "hours": "Mo-Th & Sa-Su 1pm-7pm", "phone": "602-262-6482"},
    {"name": "Marcos de Niza Senior Center", "address": "305 W. Pima Rd. Phoenix AZ 85003", "hours": "Mo-Fr 9am-3pm", "phone": "602-261-8511"},
    {"name": "Maryvale Community Center", "address": "4420 N. 51st Ave. Phoenix AZ 85032", "hours": "Mo-Th 9am-9pm, Fr 9am-6pm, Sa 10am-6pm", "phone": "602-327-9032"},
    {"name": "Maryvale Pool", "address": "4444 N. 51st Ave. Phoenix AZ 85031", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "McDowell Place Senior Center", "address": "1845 E. McDowell Rd. Phoenix AZ 85006", "hours": "Mo-Fr 9am-3pm", "phone": "602-534-3896"},
    {"name": "McDowell Road Integrated Care", "address": "4909 E. McDowell Rd. Phoenix AZ 85008", "hours": "Mo-Fr 8am-5pm", "phone": "602-685-6000"},
    {"name": "Mesquite Library", "address": "4525 E. Paradise Village Pkwy N. Phoenix AZ 85032", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Midtown Health Center", "address": "4131 N. 24th St. Phoenix AZ 85016", "hours": "Mo-Fr 7:30am-5:30pm", "phone": "480-882-4545"},
    {"name": "Midtown Medical Respite Center", "address": "333 W. Indian School Rd. Phoenix AZ 85013", "hours": "Mo-Fr 8:30am-5pm", "phone": "602-776-0776"},
    {"name": "Mitchell Clinic", "address": "40 E. Mitchell Dr. Phoenix AZ 85012", "hours": "Mo-Fr 8am-4pm", "phone": "602-685-6000"},
    {"name": "NourishPHX", "address": "501 S. 9th Ave. Phoenix AZ 85007", "hours": "Mo-Fr 9am-11am", "phone": "602-775-5740"},
    {"name": "Ocotillo Library", "address": "102 W. Southern Ave. Phoenix AZ 85041", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 10am-6pm", "phone": "602-534-2026"},
    {"name": "Palo Verde Library", "address": "4402 N. 51st Ave. Phoenix AZ 85031", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Parson's Family Health Center at Circle the City", "address": "3522 N. 3rd Ave. Phoenix AZ 85013", "hours": "Mo-Fr 8am-5pm", "phone": "602-776-7676"},
    {"name": "Phoenix Citadel Corps", "address": "628 N. 3rd Ave. Phoenix AZ 85003", "hours": "Mo-Fr 11am-5pm", "phone": "602-267-4193"},
    {"name": "Phoenix Dream Center", "address": "3210 Grand Ave. Phoenix AZ 85017", "hours": "Mo-Su 6am-10pm", "phone": "602-373-1084"},
    {"name": "Phoenix Kroc Center", "address": "1375 E. Broadway Rd. Phoenix AZ 85040", "hours": "Mo-Fr 11am-5pm", "phone": "602-267-4193"},
    {"name": "Roosevelt Pool", "address": "6246 S. 7th St. Phoenix AZ 85042", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "Saguaro Library", "address": "2808 N. 46th St. Phoenix AZ 85008", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Senior Opportunities West Senior Center", "address": "1220 S. 7th Ave. Phoenix AZ 85007", "hours": "Mo-Fr 9am-4pm", "phone": "602-534-7657"},
    {"name": "South Mountain Clinic", "address": "3540 E. Baseline Rd. Phoenix AZ 85042", "hours": "Mo-Fr 8am-4pm", "phone": "602-685-6000"},
    {"name": "South Mountain Community Center", "address": "212 E. Alta Vista Rd. Phoenix AZ 85042", "hours": "Mo-Fr 9am-3pm", "phone": "602-262-4097"},
    {"name": "South Mountain Community Library", "address": "7050 S. 24th St. Phoenix AZ 85042", "hours": "Mo-Th 9am-7pm; Fr-Sa 9am-5pm", "phone": "602-534-2026"},
    {"name": "State Coolcontainer 1645", "address": "1645 W Jefferson St. Phoenix AZ 85007", "hours": "Mo-Su 8am-8pm", "phone": "602-334-4331"},
    {"name": "Travis L. Williams Family Services Center", "address": "4732 S. Central Ave. Phoenix AZ 85040", "hours": "Mo-Fr 8am-5pm", "phone": "602-495-7504"},
    {"name": "University Park Recreation Center", "address": "1102 W. Van Buren St. Phoenix AZ 85007", "hours": "Mo-Fr 4pm-8pm", "phone": "602-327-9032"},
    {"name": "University Pool", "address": "1102 W. Van Buren St. Phoenix AZ 85007", "hours": "Mo-Th & Sa-Su 12pm-6pm", "phone": "602-262-6482"},
    {"name": "Verde Park Recreation Center", "address": "916 E. Van Buren St. Phoenix AZ 85006", "hours": "Mo-Fr 4pm-8pm", "phone": "602-327-9032"},
    {"name": "Warren Ledbetter Service Center", "address": "2702 E. Washington St. Phoenix AZ 85034", "hours": "Mo-Fr 11am-5pm", "phone": "602-267-4193"},
    {"name": "Yucca Library", "address": "5648 N. 15th Ave. Phoenix AZ 85015", "hours": "Mo, Fr, Sa 9am-5pm; Tu-Th 9am-6pm", "phone": "602-534-2026"},
    {"name": "Yideeskaadi Hozhooji Center (YHC)", "address": "3008 N. 3rd St. Phoenix AZ 85012", "hours": "Mo-Su 9am-5pm", "phone": "480-566-1252"},
]

ACS_TABLES = (
    "b01001",  # sex by age
    "b17001",  # poverty
    "b19013",  # median household income
    "b25034",  # year structure built
    "b25035",  # median year built
    "b08201",  # vehicles
    "b11001",  # household type
    "b11007",  # households with people 65+
    "b09020",  # 65+ relationship / living alone
    "b18105",  # ambulatory difficulty
)

_CENSUS_MISSING = frozenset(
    {
        -666666666,
        -222222222,
        -333333333,
        -555555555,
        -888888888,
        -999999999,
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _http_get(url: str, *, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_stream_lines(url: str, *, timeout: int = 180):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            yield raw.decode("utf-8", errors="replace").rstrip("\n")


def load_zone_geoids() -> list[str]:
    collection = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    geoids = [str(feat["properties"]["GEOID"]) for feat in collection["features"]]
    if len(geoids) != 25:
        raise SystemExit(f"expected 25 analysis zones, got {len(geoids)}")
    if len(set(geoids)) != 25:
        raise SystemExit("duplicate analysis-zone GEOIDs")
    for geoid in geoids:
        if not re.fullmatch(r"[0-9]{11}", geoid):
            raise SystemExit(f"invalid tract GEOID {geoid!r}")
    return geoids


def load_zone_shapes() -> dict[str, Any]:
    collection = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    shapes: dict[str, Any] = {}
    for feat in collection["features"]:
        geoid = str(feat["properties"]["GEOID"])
        geom = make_valid(shape(feat["geometry"]))
        shapes[geoid] = geom
    return shapes


def acs_geo_id(tract_geoid: str) -> str:
    return f"1400000US{tract_geoid}"


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
    for i, line in enumerate(_http_stream_lines(url)):
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
    print(f"  kept {len(rows)} / {len(wanted_geo_ids)} geographies", flush=True)
    return {"_header": header or [], **{k: v for k, v in rows.items()}}  # type: ignore[dict-item]


def fetch_canopy_geojson(zone_shapes: dict[str, Any]) -> dict[str, Any]:
    union = None
    for geom in zone_shapes.values():
        union = geom if union is None else union.union(geom)
    minx, miny, maxx, maxy = union.bounds
    params = {
        "f": "geojson",
        "where": "1=1",
        "outFields": "TREE_PCT_N,OBJECTID",
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "geometry": f"{minx},{miny},{maxx},{maxy}",
    }
    url = CANOPY_LAYER + "?" + urllib.parse.urlencode(params)
    print(f"Canopy query <- {CANOPY_LAYER}", flush=True)
    payload = json.loads(_http_get(url, timeout=90).decode("utf-8"))
    features = payload.get("features") or []
    print(f"  canopy features in envelope: {len(features)}", flush=True)
    return payload


def join_canopy(zone_shapes: dict[str, Any], canopy: dict[str, Any]) -> dict[str, Any]:
    features = canopy.get("features") or []
    canopy_geoms: list[Any] = []
    canopy_vals: list[float] = []
    for feat in features:
        props = feat.get("properties") or {}
        raw = props.get("TREE_PCT_N")
        if raw is None:
            continue
        try:
            pct = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(pct) or pct < 0:
            continue
        geom = make_valid(shape(feat["geometry"]))
        if geom.is_empty:
            continue
        canopy_geoms.append(geom)
        canopy_vals.append(pct)

    joined: dict[str, Any] = {}
    unmatched: list[str] = []
    if not canopy_geoms:
        return {"tracts": {}, "unmatched": list(zone_shapes)}

    tree = STRtree(canopy_geoms)
    for geoid, zone in zone_shapes.items():
        zone_area = float(zone.area)
        if zone_area <= 0:
            unmatched.append(geoid)
            continue
        weighted = 0.0
        covered = 0.0
        for idx in tree.query(zone):
            poly = canopy_geoms[int(idx)]
            inter = zone.intersection(poly)
            if inter.is_empty:
                continue
            inter_area = float(inter.area)
            if inter_area <= 0:
                continue
            weighted += canopy_vals[int(idx)] * inter_area
            covered += inter_area
        if covered / zone_area < 0.50:
            unmatched.append(geoid)
            continue
        joined[geoid] = {
            "tree_pct_n": weighted / covered,
            "overlap_share": covered / zone_area,
            "unit": "percent_of_plantable_ground",
        }
    return {"tracts": joined, "unmatched": unmatched}


def geocode_address(address: str) -> dict[str, Any] | None:
    params = {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    }
    url = CENSUS_GEOCODER + "?" + urllib.parse.urlencode(params)
    try:
        payload = json.loads(_http_get(url, timeout=30).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — ingest continues
        return {"error": str(exc)}
    matches = (
        ((payload.get("result") or {}).get("addressMatches"))
        or []
    )
    if not matches:
        return None
    coords = matches[0].get("coordinates") or {}
    lon = coords.get("x")
    lat = coords.get("y")
    if lon is None or lat is None:
        return None
    return {
        "lon": float(lon),
        "lat": float(lat),
        "matched_address": matches[0].get("matchedAddress"),
    }


def geocode_cooling_sites(zone_shapes: dict[str, Any]) -> dict[str, Any]:
    geoids = list(zone_shapes)
    geoms = [zone_shapes[g] for g in geoids]
    tree = STRtree(geoms)
    sites: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    by_zone: dict[str, list[str]] = {g: [] for g in geoids}

    for i, row in enumerate(MAG_PHOENIX_SITES):
        resource_id = f"mag-hrn-2026-{i+1:03d}"
        geo = geocode_address(row["address"])
        time.sleep(0.15)
        if not geo or "error" in geo or "lon" not in geo:
            failures.append(
                {
                    "resource_id": resource_id,
                    "name": row["name"],
                    "address": row["address"],
                    "reason": "geocode_unmatched" if not geo else str(geo),
                }
            )
            sites.append({**row, "resource_id": resource_id, "join": "unmatched"})
            continue
        point = Point(geo["lon"], geo["lat"])
        assigned: str | None = None
        for idx in tree.query(point):
            candidate = geoids[int(idx)]
            if zone_shapes[candidate].covers(point) or zone_shapes[candidate].intersects(point):
                assigned = candidate
                break
        record = {
            **row,
            "resource_id": resource_id,
            "lon": geo["lon"],
            "lat": geo["lat"],
            "matched_address": geo.get("matched_address"),
            "zone_id": assigned,
            "join": "tract_geoid_point_in_polygon" if assigned else "outside_analysis_window",
        }
        sites.append(record)
        if assigned:
            by_zone[assigned].append(resource_id)
        print(f"  geocoded {row['name']}: {assigned or 'outside window'}", flush=True)

    return {
        "sites": sites,
        "by_zone": by_zone,
        "geocode_failures": failures,
        "sites_in_window": sum(1 for s in sites if s.get("zone_id")),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zone_geoids = load_zone_geoids()
    zone_shapes = load_zone_shapes()
    wanted = {acs_geo_id(g) for g in zone_geoids}
    wanted.add(PHOENIX_PLACE_GEO_ID)

    acs_tables: dict[str, Any] = {}
    for table in ACS_TABLES:
        extracted = extract_acs_table(table, wanted)
        header = extracted.pop("_header")
        acs_tables[table.upper()] = {"columns": header, "rows": extracted}

    canopy_raw = fetch_canopy_geojson(zone_shapes)
    canopy_join = join_canopy(zone_shapes, canopy_raw)

    print("Geocoding MAG Heat Relief Network Phoenix sites...", flush=True)
    cooling = geocode_cooling_sites(zone_shapes)

    acs_matched = []
    acs_unmatched = []
    for geoid in zone_geoids:
        geo_id = acs_geo_id(geoid)
        present = all(geo_id in acs_tables[t]["rows"] for t in acs_tables)
        (acs_matched if present else acs_unmatched).append(geoid)

    bundle = {
        "contract_version": "hva-signal-phoenix-context-v1",
        "area_id": "phoenix-demo",
        "generated_at": _now_iso(),
        "zone_count": 25,
        "join_key": {
            "analysis_zones": "properties.GEOID (11-digit TIGER 2025 census tract)",
            "acs": "GEO_ID 1400000US{GEOID} from ACS 5-year table-based Summary File",
            "canopy": "majority-area spatial intersection; Phoenix layer has no GEOID field",
            "cooling": "Census geocoder lon/lat then point-in-polygon to TIGER 2025 zones",
        },
        "sources": {
            "acs": {
                "vintage": ACS_VINTAGE_LABEL,
                "year": ACS_YEAR,
                "as_of": ACS_AS_OF,
                "url_base": ACS_BASE,
                "tables": list(acs_tables),
            },
            "canopy": {
                "name": "City of Phoenix Office of Heat Response shade study — tree canopy by census tract",
                "imagery_year": 2022,
                "accessed": "2023-07 (source metadata); layer queried at ingest",
                "url": CANOPY_LAYER.rsplit("/", 1)[0],
                "definition": (
                    "TREE_PCT_N = tree canopy area / (total area - building area) * 100 "
                    "(plantable-ground share, not total-land share)"
                ),
            },
            "cooling": {
                "inventory_id": INVENTORY_ID,
                "as_of": INVENTORY_AS_OF,
                "name": "MAG Heat Relief Network Regional Directory May-September 2026",
                "url": "https://azmag.gov/Programs/Heat-Relief-Network/Heat-Relief-Network-Directories",
                "map": "https://hrn.azmag.gov",
                "coverage": "partial",
            },
        },
        "join_audit": {
            "zone_geoids": zone_geoids,
            "acs_matched": acs_matched,
            "acs_unmatched": acs_unmatched,
            "canopy_matched": sorted(canopy_join["tracts"]),
            "canopy_unmatched": canopy_join["unmatched"],
            "cooling_sites_in_window": cooling["sites_in_window"],
            "cooling_geocode_failures": cooling["geocode_failures"],
        },
        "acs": acs_tables,
        "phoenix_city_geoid": PHOENIX_PLACE_GEOID,
        "canopy": canopy_join["tracts"],
        "cooling": {
            "inventory_id": INVENTORY_ID,
            "as_of": INVENTORY_AS_OF,
            "sites": cooling["sites"],
            "by_zone": cooling["by_zone"],
        },
    }

    (OUT_DIR / "context_bundle.json").write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "SOURCE.json").write_text(
        json.dumps(
            {
                "artifact": "context_bundle.json",
                "contract_version": "hva-signal-phoenix-context-v1",
                "area_id": "phoenix-demo",
                "acs_vintage": ACS_VINTAGE_LABEL,
                "generated_at": bundle["generated_at"],
                "sources": bundle["sources"],
                "join_key": bundle["join_key"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "join_audit.json").write_text(
        json.dumps(bundle["join_audit"], indent=2) + "\n",
        encoding="utf-8",
    )
    print("Wrote", OUT_DIR / "context_bundle.json")
    print("ACS matched", len(acs_matched), "unmatched", acs_unmatched)
    print("Canopy matched", len(canopy_join["tracts"]), "unmatched", canopy_join["unmatched"])
    print("Cooling sites in 25-zone window", cooling["sites_in_window"])


if __name__ == "__main__":
    main()
