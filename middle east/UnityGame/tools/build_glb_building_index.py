#!/usr/bin/env python3
"""Inventory Amman GLB building nodes and join them to saved OSM GeoJSON.

Never modifies source GLBs or invents geometry/materials. The workflow must fail
closed when source identities cannot be extracted; an unmatched index is not success.
"""
import gzip, json, math, re, struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GLB_DIR = ROOT / "middle east" / "BuildGLB" / "amman"
SOURCE = ROOT / "middle east" / "Jordan" / "layers" / "buildings.geojson.gz"
MANIFEST = GLB_DIR / "manifest.json"
OUTPUT = GLB_DIR / "building-asset-index.json"
DIAGNOSTICS = ROOT / "middle east" / "UnityGame" / "BuildData" / "AMMAN-GLB-INDEX-DIAGNOSTICS.json"
BUILDING_RE = re.compile(r"^Building_(.+?)(?:\.\d+)?$")


def glb_node_names(path):
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


def normalize_osm_id(value):
    if value is None or isinstance(value, (dict, list, tuple)):
        return ""
    value = str(value).strip()
    if not value:
        return ""
    match = re.search(r"(?:^|/)(?:way|relation|node)[/:]([0-9]+)$", value)
    if match:
        return match.group(1)
    match = re.fullmatch(r"(?:way|relation|node)[_-]([0-9]+)", value, re.I)
    if match:
        return match.group(1)
    return value if value.isdigit() else ""


def osm_id(feature):
    props = feature.get("properties") or {}
    candidates = [feature.get(k) for k in ("id", "@id", "osm_id")]
    candidates.extend(props.get(k) for k in (
        "osm_id", "@id", "id", "building_id", "element_id",
        "osm_way_id", "way_id", "osm_relation_id", "relation_id"
    ))
    for wrapper in ("tags", "attributes", "osm", "metadata", "properties"):
        nested = props.get(wrapper)
        if isinstance(nested, dict):
            candidates.extend(nested.get(k) for k in (
                "@id", "osm_id", "id", "osm_way_id", "way_id", "element_id",
                "osm_relation_id", "relation_id"
            ))
    for value in candidates:
        result = normalize_osm_id(value)
        if result:
            return result
    return ""


def outer_rings(feature):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    polys = [coords] if geom.get("type") == "Polygon" else coords if geom.get("type") == "MultiPolygon" else []
    rings = []
    for poly in polys:
        if not poly or not isinstance(poly[0], list):
            continue
        ring = [p for p in poly[0] if isinstance(p, list) and len(p) >= 2
                and isinstance(p[0], (int, float)) and isinstance(p[1], (int, float))]
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
    assets = {}
    glb_files_present = glb_headers_valid = glb_files_with_nodes = 0
    glb_file_samples = []
    glb_node_name_samples = []
    for tile, filename in tiles.items():
        path = GLB_DIR / filename
        if not path.is_file():
            continue
        glb_files_present += 1
        try:
            with path.open("rb") as probe:
                header = probe.read(12)
            magic = header[:4].decode("ascii", errors="replace")
            if header[:4] == b"glTF" and len(header) == 12:
                glb_headers_valid += 1
        except OSError:
            magic = "read-error"
        names = glb_node_names(path)
        if names:
            glb_files_with_nodes += 1
        if len(glb_file_samples) < 5:
            glb_file_samples.append({"file": filename, "exists": True, "bytes": path.stat().st_size,
                                     "header_magic": magic, "node_names_count": len(names),
                                     "first_node_names": names[:8]})
        if len(glb_node_name_samples) < 20:
            glb_node_name_samples.extend(names[:20-len(glb_node_name_samples)])
        for name in names:
            match = BUILDING_RE.match(name)
            if not match:
                continue
            bid = normalize_osm_id(match.group(1))
            if bid:
                assets[(tile, bid, name)] = {
                    "osm_id": bid, "tile": tile, "glb_file": filename,
                    "glb_node_name": name, "source_match": False,
                    "longitude": None, "latitude": None, "name": None,
                    "height": None, "levels": None, "building": None,
                    "facade_material": None, "facade_colour": None,
                    "roof_shape": None, "roof_material": None, "roof_colour": None,
                }

    source_by_id = defaultdict(list)
    source_features = polygon_parts = missing_id = 0
    geometry_types = defaultdict(int)
    samples = []
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        source = json.load(stream)
    for feature in source.get("features", []):
        geom = feature.get("geometry") or {}
        geometry_types[geom.get("type", "missing")] += 1
        rings = outer_rings(feature)
        if not rings:
            continue
        source_features += 1
        sid = osm_id(feature)
        if not sid:
            missing_id += 1
            if len(samples) < 3:
                props = feature.get("properties") or {}
                samples.append({
                    "feature_keys": list(feature.keys())[:20],
                    "properties_keys": list(props.keys())[:40],
                    "geometry_keys": list(geom.keys())[:10],
                    "geometry_type": geom.get("type"),
                    "sample_id": feature.get("id"),
                    "sample_properties": {k: props.get(k) for k in list(props)[:8]},
                })
            continue
        props = feature.get("properties") or {}
        for part, ring in enumerate(rings):
            polygon_parts += 1
            lon = sum(float(p[0]) for p in ring) / len(ring)
            lat = sum(float(p[1]) for p in ring) / len(ring)
            if not (bounds.get("west", -180) <= lon <= bounds.get("east", 180)
                    and bounds.get("south", -90) <= lat <= bounds.get("north", 90)):
                continue
            tile = f"{math.floor(lon / tile_size)}_{math.floor(lat / tile_size)}"
            source_by_id[sid].append({
                "tile": tile, "part": part, "longitude": round(lon, 8), "latitude": round(lat, 8),
                "name": props.get("name") or props.get("name:en"),
                "height": props.get("height") or props.get("building:height") or props.get("render_height"),
                "levels": props.get("building:levels") or props.get("levels"),
                "building": props.get("building"),
                "facade_material": props.get("facade:material") or props.get("building:material") or props.get("material"),
                "facade_colour": props.get("facade:colour") or props.get("building:colour"),
                "roof_shape": props.get("roof:shape"), "roof_material": props.get("roof:material"),
                "roof_colour": props.get("roof:colour"),
            })

    matched = 0
    for asset in assets.values():
        candidates = source_by_id.get(asset["osm_id"], [])
        candidate = next((c for c in candidates if c["tile"] == asset["tile"]), None)
        if candidate is None and len(candidates) == 1:
            candidate = candidates[0]
        if candidate:
            asset.update(candidate)
            asset["source_match"] = True
            matched += 1

    counts = {
        "manifest_tiles": len(tiles),
        "manifest_glb_files_present": glb_files_present,
        "glb_files_with_valid_header": glb_headers_valid,
        "glb_files_with_named_nodes": glb_files_with_nodes,
        "existing_glb_files_scanned": len({x["glb_file"] for x in assets.values()}),
        "exported_building_nodes": len(assets), "matched_to_osm_source": matched,
        "unmatched_glb_nodes_retained": len(assets) - matched,
        "source_features_with_polygon_geometry": source_features,
        "source_polygon_parts": polygon_parts, "source_features_missing_osm_id": missing_id,
        "source_geometry_types": dict(sorted(geometry_types.items())),
    }
    diagnostic = {
        "schema_version": 1, "status": "passed" if matched else "blocked_zero_matches",
        "repository": "saeedhub101/Adam-City", "branch": "main",
        "source": "middle east/Jordan/layers/buildings.geojson.gz",
        "manifest": "middle east/BuildGLB/amman/manifest.json",
        "next_action": "Inspect unmatched_source_samples to determine the actual exported OSM ID schema; do not generate facade textures until stable identity joins work.",
        "counts": counts, "unmatched_source_samples": samples,
        "glb_file_samples": glb_file_samples, "glb_node_name_samples": glb_node_name_samples,
    }
    DIAGNOSTICS.parent.mkdir(parents=True, exist_ok=True)
    DIAGNOSTICS.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(diagnostic, ensure_ascii=False))
    if not assets:
        raise RuntimeError("No Building_ nodes found in manifest GLBs; diagnostic saved.")
    if matched == 0:
        raise RuntimeError("Zero GLB nodes matched saved OSM geometry. Diagnostic saved; refusing to publish an unmatched index.")

    rows = sorted(assets.values(), key=lambda x: (x["tile"], x["osm_id"], x["glb_node_name"]))
    result = {
        "schema_version": 2, "scope": "all existing Amman GLB tiles listed in manifest.json",
        "policy": "only identity-matched buildings are marked source_match; unmatched nodes remain explicit; no geometry or facade appearance is synthesized",
        "coordinate_reference": "WGS84 longitude/latitude only when joined to saved OSM source geometry",
        "glb_manifest": "middle east/BuildGLB/amman/manifest.json",
        "source": "middle east/Jordan/layers/buildings.geojson.gz",
        "counts": counts, "buildings": rows,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
