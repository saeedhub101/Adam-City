#!/usr/bin/env python3
"""Build a compact, redistributable OSM vector extract for central Amman.

Input: a Geofabrik Jordan PBF already clipped to the configured bbox.
Output: GeoJSON containing mapped building footprints and road centerlines.
Source data © OpenStreetMap contributors, ODbL 1.0.
This is geographic vector data, not photogrammetry or textured 3D scans.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import osmium

# Central Amman: includes Downtown/Al-Balad and nearby hillside streets.
WEST, SOUTH, EAST, NORTH = 35.9100, 31.9400, 35.9440, 31.9640
ORIGIN_LON, ORIGIN_LAT = 35.9270, 31.9520
INPUT = Path(os.environ.get("AMMAN_OSM_PBF", "amman-core.osm.pbf"))
OUTPUT = Path(os.environ.get("AMMAN_GEOJSON", "SaeedRoyaleGodot/assets/amman_core.geojson"))


def compact_tags(tags: Any) -> dict[str, str]:
    allowed = {
        "building", "building:levels", "height", "min_height", "name",
        "name:ar", "addr:street", "addr:housenumber", "shop", "amenity",
        "highway", "surface", "lanes", "maxspeed", "oneway", "bridge",
        "tunnel", "lit", "sidewalk", "service", "junction", "width",
    }
    return {tag.k: tag.v for tag in tags if tag.k in allowed}


class AmmanHandler(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.features: list[dict[str, Any]] = []
        self.buildings = 0
        self.roads = 0
        self.skipped = 0

    def way(self, way: Any) -> None:
        tags = compact_tags(way.tags)
        is_building = "building" in tags and tags["building"] not in {"no", "construction"}
        is_road = "highway" in tags
        if not is_building and not is_road:
            return
        try:
            coords = [[float(node.lon), float(node.lat)] for node in way.nodes if node.location.valid()]
        except (RuntimeError, ValueError):
            self.skipped += 1
            return
        if len(coords) < 2:
            self.skipped += 1
            return
        # Keep only features whose geometry intersects the selected central-Amman window.
        if not any(WEST <= lon <= EAST and SOUTH <= lat <= NORTH for lon, lat in coords):
            self.skipped += 1
            return
        if is_building:
            if len(coords) < 4:
                self.skipped += 1
                return
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            geometry = {"type": "Polygon", "coordinates": [coords]}
            kind = "building"
            self.buildings += 1
        else:
            geometry = {"type": "LineString", "coordinates": coords}
            kind = "road"
            self.roads += 1
        self.features.append({
            "type": "Feature",
            "id": f"way/{way.id}",
            "properties": {"kind": kind, "osm_id": int(way.id), **tags},
            "geometry": geometry,
        })


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(f"Missing input PBF: {INPUT}")
    handler = AmmanHandler()
    handler.apply_file(str(INPUT), locations=True, idx="flex_mem")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "name": "Adam Royal — Central Amman OpenStreetMap Extract",
        "source": "OpenStreetMap contributors",
        "license": "Open Database License (ODbL) 1.0",
        "attribution": "© OpenStreetMap contributors",
        "origin": {"longitude": ORIGIN_LON, "latitude": ORIGIN_LAT},
        "bounds": {"west": WEST, "south": SOUTH, "east": EAST, "north": NORTH},
        "notes": "Real mapped footprints and road centerlines. Not photogrammetry; no facade textures are included.",
        "stats": {
            "building_footprints": handler.buildings,
            "road_centerlines": handler.roads,
            "skipped_features": handler.skipped,
        },
        "features": handler.features,
    }
    OUTPUT.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **collection["stats"], "bytes": OUTPUT.stat().st_size}, ensure_ascii=False))
    if handler.buildings < 100 or handler.roads < 50:
        raise SystemExit("Extract looks incomplete: expected at least 100 buildings and 50 road ways.")


if __name__ == "__main__":
    main()
