#!/usr/bin/env python3
"""Inventory every Amman GLB building node and cross-reference saved OSM geometry.

This is a city-wide inventory, not a texture generator. Original GLBs, coordinates,
and mesh geometry are never modified. Unmatched assets are retained in the index so
a source-schema mismatch cannot silently erase the entire city's inventory.
"""
import gzip
import json
import math
import re
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GLB_DIR = ROOT / "middle east" / "BuildGLB" / "amman"
SOURCE = ROOT / "middle east" / "Jordan" / "layers" / "buildings.geojson.gz"
MANIFEST = GLB_DIR / "manifest.json"
OUTPUT = GLB_DIR / "building-asset-index.json"
BUILDING_RE = re.compile(r"^Building_(.+?)(?:\.\d+)?$")


def glb_node_names(path):
    """Read GLB JSON chunk and return named nodes without loading mesh payloads."""
    try:
        with path.open("rb") as stream:
            header = stream.read(12)
            if len(header) != 12 or header[:4] != b"glTF":
                return []
            _, version, total_length = struct.unpack("<4sII", header)
            if version != 2:
                return []
            chunk_header = stream.read(8)
            if len(chunk_header) != 8:
                return []
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            if chunk_type != 0x4E4F534A or chunk_length > total_length:
                return []
            payload = stream.read(chunk_length).rstrip(b" \t\r\n\x00")
        doc = json.loads(payload.decode("utf-8"))
        return [n.get("name", "") for n in doc.get("nodes", []) if n.get("name")]
    except (OSError, ValueError, UnicodeDecodeError, struct.error):
        return []


def osm_id(feature):
    props = feature.get("properties") or {}
    values = [feature.get("id")]
    values.extend(props.get(k) for k in (
        "osm_id", "@id", "id", "building_id", "element_id", "osm_way_id", "way_id"
    ))
    for value in values:
        if value in (None, ""):
            continue
        value = str(value).strip()
        m = re.search(r"(?:way|relation|node)/([0-9]+)$", value)
        if m:
            return m.group(1)
        if value.isdigit():
            return value
    return ""


def outer_rings(feature):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if geom.get("type") == "Polygon":
        polys = [coords]
    elif geom.get("type") == "MultiPolygon":
        polys = coords
    else:
        return []
    rings = []
    for poly in polys:
        if not poly or not isinstance(poly[0], list):
            continue
        ring = [p for p in poly[0] if isinstance(p, list) and len(p) >= 2]
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def main():
    if not MANIFEST.is_file() or not SOURCE.is_file():
        raise FileNotFoundError(f"Required local inputs missing: {MANIFEST} or {SOURCE}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bounds = manifest.get("bounds", {})
    tile_size = float(manifest.get("tile_degrees", 0.01))
    tiles = {x.get("tile"): x.get("file") for x in manifest.get("tiles", [])
             if x.get("tile") and x.get("file")}

    # Inventory every existing GLB first. This preserves assets even when source
    # GeoJSON IDs differ from exported node IDs.
    assets = {}
    for tile, filename in tiles.items():
        path = GLB_DIR / filename
        if not path.is_file():
            continue
        for name in glb_node_names(path):
            match = BUILDING_RE.match(name)
            if not match:
                continue
            bid = match.group(1)
            key = (tile, bid, name)
            assets[key] = {
                "osm_id": bid, "tile": tile, "glb_file": filename,
                "glb_node_name": name, "source_match": False,
                "longitude": None, "latitude": None, "name": None,
                "height": None, "levels": None, "building": None,
                "facade_material": None, "facade_colour": None,
                "roof_shape": None, "roof_material": None, "roof_colour": None,
            }

    source_count = 0
    polygon_count = 0
    missing_source_id = 0
    source_by_id = defaultdict(list)
    geometry_samples = defaultdict(int)
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        source = json.load(stream)
    for feature in source.get("features", []):
        geometry_samples[(feature.get("geometry") or {}).get("type", "missing")] += 1
        rings = outer_rings(feature)
        if not rings:
            continue
        source_count += 1
        sid = osm_id(feature)
        if not sid:
            missing_source_id += 1
            continue
        props = feature.get("properties") or {}
        for part, ring in enumerate(rings):
            polygon_count += 1
            lon = sum(float(p[0]) for p in ring) / len(ring)
            lat = sum(float(p[1]) for p in ring) / len(ring)
            if not (bounds.get("west", -180) <= lon <= bounds.get("east", 180)
                    and bounds.get("south", -90) <= lat <= bounds.get("north", 90)):
                continue
            tile = f"{math.floor(lon / tile_size)}_{math.floor(lat / tile_size)}"
            source_by_id[sid].append({
                "tile": tile, "part": part, "longitude": round(lon, 8),
                "latitude": round(lat, 8), "name": props.get("name") or props.get("name:en"),
                "height": props.get("height") or props.get("building:height") or props.get("render_height"),
                "levels": props.get("building:levels") or props.get("levels"),
                "building": props.get("building"),
                "facade_material": props.get("facade:material") or props.get("building:material") or props.get("material"),
                "facade_colour": props.get("facade:colour") or props.get("building:colour"),
                "roof_shape": props.get("roof:shape"),
                "roof_material": props.get("roof:material"),
                "roof_colour": props.get("roof:colour"),
            })

    matched = 0
    for key, asset in assets.items():
        candidates = source_by_id.get(asset["osm_id"], [])
        # A stable OSM ID is the primary join; tile is a consistency check, not
        # a reason to discard the node (exports may place centroids at tile edges).
        candidate = next((c for c in candidates if c["tile"] == asset["tile"]), None)
        if candidate is None and len(candidates) == 1:
            candidate = candidates[0]
        if candidate:
            asset.update(candidate)
            asset["source_match"] = True
            matched += 1

    rows = sorted(assets.values(), key=lambda x: (x["tile"], x["osm_id"], x["glb_node_name"]))
    result = {
        "schema_version": 2,
        "scope": "all existing Amman GLB tiles listed in manifest.json",
        "policy": "inventory all existing exported Building_ nodes; source joins are evidence-based; no geometry, coordinates, materials, or textures are synthesized",
        "coordinate_reference": "WGS84 longitude/latitude only when joined to saved OSM source geometry",
        "glb_manifest": "middle east/BuildGLB/amman/manifest.json",
        "source": "middle east/Jordan/layers/buildings.geojson.gz",
        "counts": {
            "manifest_tiles": len(tiles),
            "existing_glb_files_scanned": len({x["glb_file"] for x in rows}),
            "exported_building_nodes": len(rows),
            "matched_to_osm_source": matched,
            "unmatched_glb_nodes_retained": len(rows) - matched,
            "source_features_with_polygon_geometry": source_count,
            "source_polygon_parts": polygon_count,
            "source_features_missing_osm_id": missing_source_id,
            "source_geometry_types": dict(sorted(geometry_samples.items())),
        },
        "buildings": rows,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **result["counts"]}, ensure_ascii=False))
    if not rows:
        raise RuntimeError("No Building_ nodes were found in manifest GLBs; refusing to call the inventory successful.")


if __name__ == "__main__":
    main()
