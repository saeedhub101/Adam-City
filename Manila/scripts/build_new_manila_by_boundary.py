#!/usr/bin/env python3
"""Partition Manila building PBF features by complete, identified administrative boundaries.

Source tiles are read-only. Boundary fragments are grouped by stable source ID and
unioned before assignment. If stable IDs or administrative tags are absent, the
build fails rather than inventing areas or assigning buildings by tile fragments.
"""
from __future__ import annotations

import json
import math
import time
import shutil
from collections import defaultdict
from pathlib import Path

import mapbox_vector_tile
from shapely.geometry import shape
from shapely.ops import unary_union, transform

try:
    from shapely import make_valid
except ImportError:
    from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Manila" / "vector-tiles"
OUT = ROOT / "Manila" / "New_Manila"
EARTH_R = 6378137.0
RAD = math.pi / 180
REF_LAT = 14.59
BOUNDARY_NAMES = {"boundary", "boundaries", "admin", "administrative"}
BUILDING_NAMES = {"building", "buildings"}
STABLE_ID_KEYS = ("osm_id", "osm_way_id", "osm_wayid", "way_id", "relation_id", "osm_relation_id", "id")


def tile_lonlat(path: Path, extent: int, x: float, y: float) -> tuple[float, float]:
    z, tx, ty = map(int, path.relative_to(SOURCE).with_suffix("").parts[-3:])
    n = 2 ** z
    lon = (tx + x / extent) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + y / extent) / n))))
    return lon, lat


def metric_xy(lon: float, lat: float) -> tuple[float, float]:
    return EARTH_R * lon * RAD * math.cos(REF_LAT * RAD), EARTH_R * lat * RAD


def convert_geom(path: Path, geometry: dict, extent: int, metric: bool = False):
    geom = shape(geometry)

    def project(x, y, z=None):
        if hasattr(x, "__iter__"):
            coords = []
            for px, py in zip(x, y):
                ll = tile_lonlat(path, extent, float(px), float(py))
                coords.append(metric_xy(*ll) if metric else ll)
            return [p[0] for p in coords], [p[1] for p in coords]
        ll = tile_lonlat(path, extent, float(x), float(y))
        return metric_xy(*ll) if metric else ll

    return transform(project, geom)


def stable_id(props: dict, feature: dict) -> str | None:
    for key in STABLE_ID_KEYS:
        value = props.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    value = feature.get("id")
    if value not in (None, ""):
        return f"feature_id:{value}"
    return None


def polygonal(geom):
    geom = make_valid(geom)
    if geom.geom_type == "Polygon":
        return geom
    if geom.geom_type == "MultiPolygon":
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type in ("Polygon", "MultiPolygon") and not g.is_empty]
    return unary_union(parts) if parts else None


def admin_level(props: dict) -> str | None:
    value = props.get("admin_level")
    if value not in (None, ""):
        return str(value)
    if str(props.get("boundary", "")).lower() == "administrative":
        return "unspecified"
    return None


def main():
    tiles = sorted(p for p in SOURCE.rglob("*.pbf") if p.is_file())
    if not tiles:
        raise RuntimeError("No source PBF tiles found under Manila/vector-tiles.")

    # boundary ID -> all clipped polygon pieces and source attributes
    boundary_parts = defaultdict(list)
    boundary_props = {}
    boundary_layers, building_layers = set(), set()
    boundary_errors, building_errors = [], []
    boundaries_seen = 0
    print(f"Scanning {len(tiles)} source PBF tiles for identified administrative boundaries.", flush=True)

    for ti, path in enumerate(tiles, 1):
        try:
            decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
            for lname, layer in decoded.items():
                if str(lname).lower() not in BOUNDARY_NAMES:
                    continue
                boundary_layers.add(str(lname))
                extent = int(layer.get("extent", 4096))
                for fi, feature in enumerate(layer.get("features", [])):
                    geom_data = feature.get("geometry")
                    if not geom_data or not geom_data.get("coordinates"):
                        continue
                    props = feature.get("properties") or {}
                    level = admin_level(props)
                    if level is None:
                        continue
                    bid = stable_id(props, feature)
                    if bid is None:
                        boundary_errors.append({"tile": str(path.relative_to(ROOT)), "feature": fi,
                                                "reason": "Administrative boundary has no stable source ID"})
                        continue
                    try:
                        geom = convert_geom(path, geom_data, extent, metric=True)
                        geom = polygonal(geom)
                        if geom is None or geom.is_empty:
                            continue
                        # Keep a consistent identity for one source boundary across all tile fragments.
                        identity = {"name": props.get("name"), "admin_level": level,
                                    "boundary": props.get("boundary"), "id_key": bid}
                        previous = boundary_props.get(bid)
                        if previous and (previous.get("name") != identity["name"] or
                                         previous.get("admin_level") != identity["admin_level"]):
                            boundary_errors.append({"boundary_id": bid, "reason": "Conflicting name/admin_level across tile fragments",
                                                    "first": previous, "other": identity})
                            continue
                        boundary_props[bid] = identity
                        boundary_parts[bid].append(geom)
                        boundaries_seen += 1
                    except Exception as exc:
                        boundary_errors.append({"tile": str(path.relative_to(ROOT)), "feature": fi, "error": str(exc)})
        except Exception as exc:
            boundary_errors.append({"tile": str(path.relative_to(ROOT)), "error": str(exc)})
        if ti % 10 == 0 or ti == len(tiles):
            print(f"[boundaries {ti}/{len(tiles)}] unique IDs={len(boundary_parts)} pieces={boundaries_seen}", flush=True)

    if not boundary_parts:
        raise RuntimeError("No administrative polygon boundaries with stable IDs were found. Output was not generated.")

    areas = []
    for bid, pieces in boundary_parts.items():
        try:
            merged = polygonal(unary_union(pieces))
            if merged is None or merged.is_empty or not merged.is_valid or merged.area <= 100:
                boundary_errors.append({"boundary_id": bid, "reason": "Merged boundary geometry invalid, empty, or too small"})
                continue
            areas.append({"id": bid, "properties": boundary_props[bid], "geometry": merged})
        except Exception as exc:
            boundary_errors.append({"boundary_id": bid, "error": f"Union failed: {exc}"})

    if boundary_errors:
        # Do not silently create a partial/guessed administrative map when boundary identity is ambiguous.
        raise RuntimeError(
            f"Boundary validation failed ({len(boundary_errors)} errors). Refusing to partition buildings. "
            "See logs above; source PBFs were not modified."
        )
    if not areas:
        raise RuntimeError("No valid complete administrative boundary geometries after union.")

    # A building's assignment uses its complete cross-tile geometry, not a clipped tile fragment's centroid.
    building_parts = defaultdict(list)
    building_props = {}
    building_layer_for_id = {}
    building_tile_features = defaultdict(dict)
    unique_building_keys = set()
    missing_building_ids = 0

    print(f"Building complete boundary geometries: {len(areas)}. Scanning buildings.", flush=True)
    for ti, path in enumerate(tiles, 1):
        rel = path.relative_to(SOURCE)
        z, tx, ty = map(int, rel.with_suffix("").parts[-3:])
        try:
            decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
            for lname, layer in decoded.items():
                if str(lname).lower() not in BUILDING_NAMES:
                    continue
                building_layers.add(str(lname))
                extent = int(layer.get("extent", 4096))
                for fi, feature in enumerate(layer.get("features", [])):
                    geom_data = feature.get("geometry")
                    if not geom_data or not geom_data.get("coordinates"):
                        continue
                    props = feature.get("properties") or {}
                    bid = stable_id(props, feature)
                    if bid is None:
                        missing_building_ids += 1
                        building_errors.append({"tile": str(rel), "feature": fi,
                                                "reason": "Building has no stable source ID"})
                        continue
                    try:
                        geom = convert_geom(path, geom_data, extent, metric=True)
                        if geom.is_empty:
                            continue
                        building_parts[bid].append(geom)
                        building_props.setdefault(bid, props)
                        building_layer_for_id.setdefault(bid, str(lname))
                        # Preserve the original tile-local feature coordinates for rendering; only route it
                        # to the area determined from the union of all fragments of the same building ID.
                        fingerprint = (str(lname), json.dumps(props, sort_keys=True, ensure_ascii=False),
                                       json.dumps(geom_data, sort_keys=True, ensure_ascii=False))
                        unique_building_keys.add((bid, fingerprint))
                        tile_key = (str(lname), bid, fingerprint)
                        building_tile_features[(z, tx, ty)][tile_key] = {
                            "layer": str(lname), "extent": extent, "feature": feature, "building_id": bid
                        }
                    except Exception as exc:
                        building_errors.append({"tile": str(rel), "feature": fi, "error": str(exc)})
        except Exception as exc:
            building_errors.append({"tile": str(rel), "error": str(exc)})
        if ti % 10 == 0 or ti == len(tiles):
            print(f"[buildings {ti}/{len(tiles)}] unique IDs={len(building_parts)}", flush=True)

    if building_errors:
        raise RuntimeError(
            f"Building scan/identity validation failed ({len(building_errors)} errors; "
            f"{missing_building_ids} features without stable IDs). Refusing to write guessed output."
        )

    assigned = defaultdict(list)
    unassigned = []
    for bid, pieces in building_parts.items():
        try:
            complete = unary_union(pieces)
            center = complete.centroid
            candidates = [a for a in areas if a["geometry"].covers(center)]
            if not candidates:
                unassigned.append(bid)
                continue
            chosen = min(candidates, key=lambda a: a["geometry"].area)
            assigned[bid] = chosen["id"]
        except Exception as exc:
            building_errors.append({"building_id": bid, "error": f"Whole-building union/assignment failed: {exc}"})

    if building_errors:
        raise RuntimeError(f"Building assignment failed ({len(building_errors)} errors); no output written.")

    area_index = {a["id"]: i for i, a in enumerate(areas, 1)}
    output_buckets = defaultdict(lambda: defaultdict(dict))
    for (z, tx, ty), feature_map in building_tile_features.items():
        for (_, bid, fingerprint), item in feature_map.items():
            boundary_id = assigned.get(bid)
            if boundary_id is None:
                continue
            ai = area_index[boundary_id]
            lname = item["layer"]
            output_buckets[(ai, z, tx, ty)][lname][fingerprint] = item["feature"]

    # Only replace the generated output after every source feature and boundary passed validation.
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    area_counts = {a["id"]: set() for a in areas}
    output_files = 0
    for (ai, z, tx, ty), layers in output_buckets.items():
        folder = f"area-{ai:04d}"
        outpath = OUT / folder / str(z) / str(tx) / f"{ty}.pbf"
        outpath.parent.mkdir(parents=True, exist_ok=True)
        payload = []
        for lname, feature_map in layers.items():
            features = list(feature_map.values())
            payload.append({"name": lname, "features": features,
                            "extent": int(mapbox_vector_tile.decode(tiles[0].read_bytes(),
                                default_options={"y_coord_down": True}).get(lname, {}).get("extent", 4096)),
                            "version": 2})
        encoded = mapbox_vector_tile.encode(payload, default_options={"y_coord_down": True})
        check = mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
        expected = sum(len(v["features"]) for v in payload)
        actual = sum(len(v.get("features", [])) for v in check.values())
        if actual != expected:
            raise RuntimeError(f"Verification failed for {outpath}: expected {expected}, got {actual}")
        outpath.write_bytes(encoded)
        output_files += 1

    for bid, area_id in assigned.items():
        area_counts[area_id].add(bid)

    area_rows = []
    for i, area in enumerate(areas, 1):
        area_rows.append({
            "folder": f"area-{i:04d}",
            "boundary_id": area["id"],
            "name": area["properties"].get("name"),
            "admin_level": area["properties"].get("admin_level"),
            "building_features": len(area_counts[area["id"]]),
            "area_m2": round(area["geometry"].area, 2),
        })

    summary = {
        "status": "completed_with_unassigned_buildings" if unassigned else "completed",
        "source": "Manila/vector-tiles",
        "source_pbf_tiles": len(tiles),
        "boundary_layer_names": sorted(boundary_layers),
        "boundary_polygon_fragments_seen": boundaries_seen,
        "unique_boundary_ids": len(boundary_parts),
        "valid_complete_boundaries": len(areas),
        "building_layer_names": sorted(building_layers),
        "unique_building_ids": len(building_parts),
        "unique_buildings_assigned": len(assigned),
        "unique_buildings_unassigned": len(unassigned),
        "new_pbf_files_written": output_files,
        "source_pbf_modified": False,
        "assignment_method": "Union boundary fragments by stable administrative boundary ID; union all tile fragments for each stable building ID; assign by whole-building centroid to the smallest complete administrative polygon that covers it. No nearest-boundary or fragment-centroid fallback.",
        "areas": area_rows,
        "unassigned_building_ids": unassigned,
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# New_Manila: buildings assigned to complete administrative boundaries\n\n"
        f"- Source tiles: {len(tiles)}\n"
        f"- Boundary polygon fragments: {boundaries_seen}\n"
        f"- Unique boundary IDs: {len(boundary_parts)}\n"
        f"- Valid complete boundaries: {len(areas)}\n"
        f"- Unique building IDs assigned: {len(assigned)}\n"
        f"- Unique buildings without a containing boundary: {len(unassigned)}\n"
        f"- New PBF files: {output_files}\n"
        "- Original PBFs modified: no\n"
        "- The build fails closed if stable IDs or valid administrative boundaries are missing.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source_tiles": len(tiles), "unique_boundaries": len(areas),
        "unique_buildings": len(building_parts), "assigned": len(assigned),
        "unassigned": len(unassigned), "pbf_files": output_files,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
