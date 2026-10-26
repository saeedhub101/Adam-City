#!/usr/bin/env python3
"""Build an offline index matching existing Amman GLB building nodes to saved OSM records.

This script does not generate geometry, alter GLBs, add textures, or download anything.
It writes an auditable source-to-asset index from the repository's compressed source data.
"""
import gzip
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GLB_DIR = ROOT / "middle east" / "BuildGLB" / "amman"
SOURCE = ROOT / "middle east" / "Jordan" / "layers" / "buildings.geojson.gz"
MANIFEST = GLB_DIR / "manifest.json"
OUTPUT = GLB_DIR / "building-asset-index.json"

def glb_node_names(path):
    """Read only the GLB JSON chunk and return exported node names."""
    if not path.is_file():
        return set()
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b"glTF":
            return set()
        _magic, version, total_length = struct.unpack("<4sII", header)
        if version != 2:
            return set()
        chunk_header = stream.read(8)
        if len(chunk_header) != 8:
            return set()
        chunk_length, chunk_type = struct.unpack("<II", chunk_header)
        if chunk_type != 0x4E4F534A or chunk_length > total_length:
            return set()
        payload = stream.read(chunk_length).rstrip(bytes([0x20, 0x09, 0x0D, 0x0A, 0x00]))
    try:
        gltf = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return set()
    return {node.get("name", "") for node in gltf.get("nodes", []) if node.get("name")}



def source_building_id(feature):
    """Return the stable OSM identity regardless of GeoJSON exporter conventions."""
    props = feature.get("properties") or {}
    value = feature.get("id")
    if value in (None, ""):
        for key in ("osm_id", "@id", "id", "building_id", "element_id"):
            value = props.get(key)
            if value not in (None, ""):
                break
    if value in (None, ""):
        return ""
    value = str(value).strip()
    if "/" in value and value.split("/", 1)[0] in ("way", "relation", "node"):
        value = value.split("/", 1)[1]
    return value


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
    node_names_by_file = {}
    missing_tiles = 0
    missing_glb_nodes = 0
    outside_bounds = 0
    bounds = manifest.get("bounds", {})
    tile_size = float(manifest.get("tile_degrees", 0.01))

    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        source = json.load(stream)

    for feature in source.get("features", []):
        props = feature.get("properties") or {}
        osm_id = source_building_id(feature)
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
            glb_path = GLB_DIR / glb_file if glb_file else None
            if not glb_file or not glb_path.is_file():
                missing_tiles += 1
                node_match = False
            else:
                if glb_file not in node_names_by_file:
                    node_names_by_file[glb_file] = glb_node_names(glb_path)
                names = node_names_by_file[glb_file]
                node_match = any(name == f"Building_{osm_id}" or name.startswith(f"Building_{osm_id}.")
                                 for name in names)
                if not node_match:
                    missing_glb_nodes += 1
            entries.append({
                "osm_id": osm_id,
                "polygon_part": part_index,
                "glb_node_name_prefix": f"Building_{osm_id}",
                "tile": tile,
                "glb_file": glb_file,
                "glb_node_verified": node_match,
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

    if not entries:
        raise RuntimeError(
            "No OSM building records were indexed. Refusing to publish an empty index; "
            "check the source feature IDs, bounds, and GLB manifest."
        )

    result = {
        "schema_version": 1,
        "policy": "verify exported GLB node identity against saved OSM IDs; no geometry, material, texture, or coordinate synthesis",
        "coordinate_reference": "WGS84 longitude/latitude from the saved OSM source",
        "glb_manifest": "middle east/BuildGLB/amman/manifest.json",
        "source": "middle east/Jordan/layers/buildings.geojson.gz",
        "counts": {
            "matched_source_building_parts": len(entries),
            "parts_without_existing_glb_tile": missing_tiles,
            "parts_without_matching_exported_glb_node": missing_glb_nodes,
            "parts_outside_glb_bounds": outside_bounds
        },
        "buildings": sorted(entries, key=lambda x: (x["tile"], x["osm_id"], x["polygon_part"]))
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **result["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
