#!/usr/bin/env python3
"""Download real OpenStreetMap geometry for central Manila and normalize it for Adam Royal."""
from __future__ import annotations
import json, math, os, sys, time
from pathlib import Path
import requests

# Intramuros, Ermita and southern Binondo edge. Coordinates are real OSM bounds.
SOUTH, WEST, NORTH, EAST = 14.575, 120.965, 14.600, 120.990
OUT = Path(__file__).resolve().parents[1] / "assets" / "manila_city.json"
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
QUERY = f"""[out:json][timeout:180];
(
 way[building]({SOUTH},{WEST},{NORTH},{EAST});
 way[highway]({SOUTH},{WEST},{NORTH},{EAST});
);
out body; >; out skel qt;"""

def fetch() -> dict:
    session = requests.Session()
    headers = {"User-Agent": "AdamRoyal-Game/1.0 (OpenStreetMap attribution included)", "Accept": "application/json"}
    last = None
    for attempt in range(3):
        for endpoint in ENDPOINTS:
            try:
                response = session.post(endpoint, data={"data": QUERY}, timeout=(15, 100), headers=headers)
                response.raise_for_status()
                data = response.json()
                if data.get("elements"):
                    print(f"Downloaded {len(data['elements'])} OSM elements from {endpoint}")
                    return data
                last = RuntimeError("Empty OSM response")
            except Exception as exc:
                last = exc
                print(f"OSM endpoint failed: {endpoint}: {exc}", flush=True)
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Unable to fetch real Manila OSM data after retries: {last}")

def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = fetch()
    nodes = {int(e["id"]): (float(e["lat"]), float(e["lon"])) for e in data["elements"] if e.get("type") == "node"}
    ways = [e for e in data["elements"] if e.get("type") == "way" and e.get("nodes")]
    center_lat, center_lon = (SOUTH + NORTH) / 2, (WEST + EAST) / 2
    meters_lat = 111132.0
    meters_lon = 111320.0 * math.cos(math.radians(center_lat))
    def xy(node_id: int):
        lat, lon = nodes[node_id]
        return [round((lon - center_lon) * meters_lon, 2), round((center_lat - lat) * meters_lat, 2)]
    buildings, roads = [], []
    for way in ways:
        tags = way.get("tags", {})
        coords = [xy(n) for n in way["nodes"] if n in nodes]
        if tags.get("building") and len(coords) >= 4 and coords[0] == coords[-1]:
            coords = coords[:-1]
            if len(coords) < 3:
                continue
            levels = tags.get("building:levels")
            try:
                height = float(tags.get("height", float(levels) * 3.1 if levels else 8.0))
            except (TypeError, ValueError):
                height = 8.0
            height = max(3.0, min(height, 100.0))
            buildings.append({"id": int(way["id"]), "points": coords, "height": height, "type": tags.get("building", "yes")})
        highway = tags.get("highway")
        if highway and len(coords) >= 2:
            widths = {"motorway": 14, "trunk": 12, "primary": 10, "secondary": 8, "tertiary": 7, "residential": 5.5, "service": 3.5, "footway": 1.8, "path": 1.5}
            roads.append({"id": int(way["id"]), "points": coords, "width": widths.get(highway, 5.0), "type": highway})
    result = {
        "schema": 1,
        "city": "Manila, Philippines",
        "source": "OpenStreetMap contributors",
        "attribution": "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright",
        "bounds": {"south": SOUTH, "west": WEST, "north": NORTH, "east": EAST},
        "center": [center_lat, center_lon],
        "buildings": buildings,
        "roads": roads,
    }
    OUT.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT}: {len(buildings)} real building footprints, {len(roads)} road ways, {OUT.stat().st_size:,} bytes")
    if len(buildings) < 100 or len(roads) < 30:
        raise RuntimeError(f"OSM data incomplete: expected >=100 buildings and >=30 roads; got {len(buildings)} and {len(roads)}")

if __name__ == "__main__":
    main()
