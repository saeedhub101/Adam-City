#!/usr/bin/env python3
"""Build an offline index matching existing Amman GLB building nodes to saved OSM records.

This script does not generate geometry, alter GLBs, add textures, or download anything.
It writes an auditable source-to-asset index from the repository's compressed source data.
"""
import gzip
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GLB_DIR = ROOT / "middle east" / "BuildGLB" / "amman"
SOURCE = ROOT / "middle east" / "Jordan" / "layers" / "buildings.geojson.gz"
MANIFEST = GLB_DIR / "manifest.json"
OUTPUT = GLB_DIR / "building-asset-index.json"


def tag(props, *keys):
    for key in keys:
        value = props.get(key)
        if value not in (None, "", "no"):
            return value
    return None


def outer_rings(feature):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if geom.get("type") == "Polygon":
        polys = [coords]
    elif geom.get("type") == "MultiPolygon":
        polys = coords
    else:
        return []
    result = []
    for poly in polys:
        if not poly or not poly[0]:
            continue
        ring = [p for p in poly[0] if isinstance(p, list) and len(p) >= 2]
        if len(ring) >= 3:
            result.append(ring)
    return result


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Missing repository-local OSM source: {SOURCE}")
    if not MANIFEST.is_file():
        raise FileNotFoundError(f"Missing existing GLB manifest: {MANIFEST}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    known_tiles = {entry["tile"]: entry["file"] for entry in manifest.get("tiles", [])
                   if entry.get("tile") and entry.get("file")}
    entries = []
    missing_tiles = 0
    outside_bounds = 0
    bounds = manifest.get("bounds", {})
    tile_size = float(manifest.get("tile_degrees", 0.01))

    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        source = json.load(stream)

    for feature in source.get("features", []):
        props = feature.get("properties") or {}
        osm_id = str(feature.get("id", ""))
        if not osm_id:
            continue
        for part_index, ring in enumerate(outer_rings(feature)):
            # Use only source coordinates; do not reposition or reshape the GLB.
            lon = sum(p[0] for p in ring) / len(ring)
            lat = sum(p[1] for p in ring) / len(ring)
            if not (bounds.get("west", -180) <= lon <= bounds.get("east", 180)
                    and bounds.get("south", -90) <= lat <= bounds.get("north", 90)):
                outside_bounds += 1
                continue
            tx, ty = math.floor(lon / tile_size), math.floor(lat / tile_size)
            tile = f"{tx}_{ty}"
            glb_file = known_tiles.get(tile)
            if not glb_file:
                missing_tiles += 1
            entries.append({
                "osm_id": osm_id,
                "polygon_part": part_index,
                "glb_node_name_prefix": f"Building_{osm_id}",
                "tile": tile,
                "glb_file": glb_file,
                "longitude": round(lon, 8),
                "latitude": round(lat, 8),
                "name": tag(props, "name", "name:en"),
                "height": tag(props, "height", "building:height", "render_height"),
                "levels": tag(props, "building:levels", "levels"),
                "building": tag(props, "building"),
                "facade_material": tag(props, "facade:material", "building:material", "material"),
                "facade_colour": tag(props, "facade:colour", "building:colour"),
                "roof_shape": tag(props, "roof:shape"),
                "roof_material": tag(props, "roof:material"),
                "roof_colour": tag(props, "roof:colour"),
                "source": "middle east/Jordan/layers/buildings.geojson.gz"
            })

    result = {
        "schema_version": 1,
        "policy": "source-matched metadata only; no geometry, material, texture, or coordinate synthesis",
        "coordinate_reference": "WGS84 longitude/latitude from the saved OSM source",
        "glb_manifest": "middle east/BuildGLB/amman/manifest.json",
        "source": "middle east/Jordan/layers/buildings.geojson.gz",
        "counts": {
            "matched_source_building_parts": len(entries),
            "parts_without_manifest_tile": missing_tiles,
            "parts_outside_glb_bounds": outside_bounds
        },
        "buildings": sorted(entries, key=lambda x: (x["tile"], x["osm_id"], x["polygon_part"]))
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **result["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
