#!/usr/bin/env python3
"""One-time grouping of GeoJSON building features into geographic coordinate cells.
Run identifier: 2026-10-23-coordinate-grouping-v2.
"""
from __future__ import annotations
import json, math
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Manila" / "GeoJSON_Source"
OUTPUT = ROOT / "Manila" / "New_Manila"
CELL = 0.001  # roughly 100-111 m at Manila latitude

def points(coords):
    if isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
            yield float(coords[0]), float(coords[1])
        else:
            for item in coords:
                yield from points(item)

def center(feature):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates")
    if coords is None:
        return None
    pts = list(points(coords))
    if not pts:
        return None
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    return (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2

def main():
    if not SOURCE.is_dir():
        raise SystemExit(f"Source directory not found: {SOURCE}")
    paths = sorted(p for p in SOURCE.rglob("*.geojson") if p.name != "conversion-summary.json")
    if not paths:
        raise SystemExit(f"No GeoJSON source tiles found under {SOURCE}")
    groups = defaultdict(list)
    source_features = building_features = missing_geometry = 0
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for feature in data.get("features", []):
            source_features += 1
            props = feature.get("properties") or {}
            if props.get("_source_layer") != "building":
                continue
            building_features += 1
            c = center(feature)
            if c is None:
                missing_geometry += 1
                continue
            lon, lat = c
            lat_key = round(math.floor(lat / CELL) * CELL, 3)
            lon_key = round(math.floor(lon / CELL) * CELL, 3)
            groups[(lat_key, lon_key)].append(feature)
    if not groups:
        raise SystemExit("No features from the exact source layer 'building' were found.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for (lat, lon), features in sorted(groups.items()):
        folder = OUTPUT / f"lat_{lat:.3f}"
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"lon_{lon:.3f}.geojson"
        collection = {
            "type": "FeatureCollection",
            "name": f"buildings_lat_{lat:.3f}_lon_{lon:.3f}",
            "metadata": {
                "coordinate_system": "WGS84 (EPSG:4326)",
                "grouping": "building bounding-box midpoint, assigned to 0.001-degree latitude/longitude cells",
                "cell_latitude_min": lat, "cell_longitude_min": lon,
                "cell_size_degrees": CELL, "building_feature_count": len(features),
                "source": "Manila/GeoJSON_Source",
            },
            "features": features,
        }
        destination.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    summary = {
        "status": "completed",
        "source_directory": "Manila/GeoJSON_Source",
        "output_directory": "Manila/New_Manila",
        "source_geojson_tiles_read": len(paths),
        "source_features_scanned": source_features,
        "building_features_found": building_features,
        "building_features_grouped": building_features - missing_geometry,
        "building_features_without_geometry": missing_geometry,
        "coordinate_groups_created": len(groups),
        "cell_size_degrees": CELL,
        "source_geojson_modified": False,
        "note": "Only the exact source layer 'building' is included. Other layers remain untouched in GeoJSON_Source. Repeated features across zoom levels/tiles are preserved, not deduplicated.",
    }
    (OUTPUT / "grouping-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)
if __name__ == "__main__":
    main()
