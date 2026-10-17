#!/usr/bin/env python3
"""Fetch named Manila streets and their real OSM geometry for in-game wayfinding."""
from __future__ import annotations
import json, math, time
from pathlib import Path
import requests

SOUTH, WEST, NORTH, EAST = 14.575, 120.965, 14.600, 120.990
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "manila_street_names.json"
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
]
QUERY = f"""[out:json][timeout:120];
way[highway][name]({SOUTH},{WEST},{NORTH},{EAST});
out body; >; out skel qt;"""

def main() -> None:
    headers = {"User-Agent": "AdamRoyal-Game/1.0 (OpenStreetMap contributors attribution in game)", "Accept": "application/json"}
    last_error = None
    data = None
    with requests.Session() as session:
        for attempt in range(3):
            for endpoint in ENDPOINTS:
                try:
                    response = session.post(endpoint, data={"data": QUERY}, headers=headers, timeout=(15, 90))
                    response.raise_for_status()
                    candidate = response.json()
                    if candidate.get("elements"):
                        data = candidate
                        print(f"STREET_SOURCE={endpoint} ELEMENTS={len(candidate['elements'])}")
                        break
                except Exception as exc:
                    last_error = exc
                    print(f"Street endpoint failed: {endpoint}: {exc}", flush=True)
            if data:
                break
            time.sleep(2 + attempt * 3)
    if not data:
        raise RuntimeError(f"Could not fetch real named Manila streets from any Overpass mirror: {last_error}")

    nodes = {int(e["id"]): (float(e["lat"]), float(e["lon"])) for e in data["elements"] if e.get("type") == "node"}
    center_lat, center_lon = (SOUTH + NORTH) / 2, (WEST + EAST) / 2
    meters_lon = 111320.0 * math.cos(math.radians(center_lat))
    roads = []
    seen = set()
    for way in data["elements"]:
        if way.get("type") != "way" or not way.get("tags", {}).get("name"):
            continue
        tags = way["tags"]
        points = []
        for node_id in way.get("nodes", []):
            if node_id in nodes:
                lat, lon = nodes[node_id]
                points.append([round((lon-center_lon)*meters_lon, 2), round((center_lat-lat)*111132.0, 2)])
        if len(points) < 2:
            continue
        name = str(tags["name"]).strip()
        if not name:
            continue
        key = (name.casefold(), tuple(points))
        if key in seen:
            continue
        seen.add(key)
        roads.append({
            "osm_way_id": int(way["id"]),
            "name": name,
            "local_name": tags.get("name:tl", tags.get("name:en", name)),
            "highway": tags.get("highway", "road"),
            "ref": tags.get("ref", ""),
            "points": points,
        })
    roads.sort(key=lambda road: (road["name"].casefold(), road["osm_way_id"]))
    result = {
        "schema": 1,
        "city": "Manila, Philippines",
        "source": "OpenStreetMap contributors / Overpass API",
        "attribution": "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright",
        "bounds": {"south": SOUTH, "west": WEST, "north": NORTH, "east": EAST},
        "named_road_segments": len(roads),
        "unique_street_names": len({r["name"] for r in roads}),
        "streets": roads,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"MANILA_STREET_NAMES_PASS segments={len(roads)} unique_names={result['unique_street_names']} bytes={OUT.stat().st_size}")
    if len(roads) < 20 or result["unique_street_names"] < 10:
        raise RuntimeError(f"Named street data looks incomplete: {len(roads)} segments / {result['unique_street_names']} names")

if __name__ == "__main__":
    main()
