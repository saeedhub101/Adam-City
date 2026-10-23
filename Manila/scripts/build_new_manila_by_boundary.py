#!/usr/bin/env python3
"""Partition every feature in every Manila vector PBF into 51 spatial groups.

All source layers are retained (buildings, roads, water, landuse, names, POIs, etc.).
The source Manila/vector-tiles directory is read-only. Every group gets one valid
z/x/y.pbf output for each source tile, including empty feature layers where needed.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import mapbox_vector_tile
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Manila" / "vector-tiles"
BOUNDARY_PATH = ROOT / "complete_data" / "open free tile" / "layers" / "boundary.geojsonl"
OUT = ROOT / "Manila" / "New_Manila"
STAGE = ROOT / "Manila" / "New_Manila.staging"
EARTH_R = 6371008.8
RAD = math.pi / 180.0
REF_LAT = 14.45


def project(lon: float, lat: float) -> tuple[float, float]:
    return EARTH_R * lon * RAD * math.cos(REF_LAT * RAD), EARTH_R * lat * RAD


def read_boundaries() -> list[dict[str, Any]]:
    result = []
    for record, line in enumerate(BOUNDARY_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        feature = json.loads(line)
        geom = feature.get("geometry") or {}
        kind = geom.get("type")
        raw = [geom.get("coordinates", [])] if kind == "LineString" else geom.get("coordinates", [])
        if kind not in ("LineString", "MultiLineString"):
            raise ValueError(f"Boundary record {record}: unsupported geometry {kind}")
        parts = [LineString([project(float(p[0]), float(p[1])) for p in coords if len(p) >= 2])
                 for coords in raw]
        parts = [p for p in parts if not p.is_empty and len(p.coords) >= 2]
        if not parts:
            raise ValueError(f"Boundary record {record} has no usable lines")
        result.append({"record": record, "geometry": unary_union(parts),
                       "feature_id": feature.get("id"), "properties": feature.get("properties") or {}})
    if len(result) != 51:
        raise ValueError(f"Expected 51 boundary records, found {len(result)}")
    return result


def tile_lonlat(path: Path, extent: int, x: float, y: float) -> tuple[float, float]:
    z, tx, ty = map(int, path.relative_to(SOURCE).with_suffix("").parts[-3:])
    n = 2 ** z
    lon = (tx + x / extent) / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + y / extent) / n))))
    return lon, lat


def feature_center(path: Path, feature: dict, extent: int) -> tuple[float, float] | None:
    geom_data = feature.get("geometry") or {}
    if not geom_data.get("coordinates"):
        return None
    try:
        centroid = shape(geom_data).centroid
        return tile_lonlat(path, extent, float(centroid.x), float(centroid.y))
    except Exception:
        return None


def assign_group(lon: float, lat: float, boundaries: list[dict]) -> int:
    point = Point(*project(lon, lat))
    return min(boundaries, key=lambda item: (float(item["geometry"].distance(point)),
                                             int(item["record"])))["record"]


def main() -> None:
    if not BOUNDARY_PATH.is_file():
        raise FileNotFoundError(f"Missing boundary input: {BOUNDARY_PATH}")
    tiles = sorted(p for p in SOURCE.rglob("*.pbf") if p.is_file())
    if len(tiles) != 141:
        raise RuntimeError(f"Expected exactly 141 source PBF tiles; found {len(tiles)}")
    boundaries = read_boundaries()
    print(f"Source tiles={len(tiles)}; groups={len(boundaries)}; all layers will be partitioned.", flush=True)

    # Each tile is kept as a schema of layer names/extents/version. Feature occurrences
    # are assigned to one spatial group by their own geometry centroid.
    tile_schemas: dict[str, list[dict[str, Any]]] = {}
    buckets: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    layer_totals: dict[str, int] = defaultdict(int)
    group_totals = {i: 0 for i in range(1, 52)}
    decode_errors = []
    skipped_no_geometry = 0

    for tile_index, path in enumerate(tiles, 1):
        rel = path.relative_to(SOURCE).as_posix()
        decoded = None
        try:
            decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
            schemas = []
            z, tx, ty = map(int, path.relative_to(SOURCE).with_suffix("").parts[-3:])
            # Use tile center as a fallback for features without geometry so data is not lost.
            tile_lon = ((tx + 0.5) / (2 ** z)) * 360.0 - 180.0
            tile_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + 0.5) / (2 ** z))))
            fallback_group = assign_group(tile_lon, tile_lat, boundaries)
            for layer_name, layer in decoded.items():
                extent = int(layer.get("extent", 4096))
                schemas.append({"name": str(layer_name), "extent": extent,
                                "version": int(layer.get("version", 2))})
                for feature in layer.get("features", []):
                    center = feature_center(path, feature, extent)
                    if center is None:
                        group_id = fallback_group
                        skipped_no_geometry += 1
                    else:
                        group_id = assign_group(*center, boundaries)
                    buckets[(group_id, rel, str(layer_name))].append(feature)
                    group_totals[group_id] += 1
                    layer_totals[str(layer_name)] += 1
            tile_schemas[rel] = schemas
        except Exception as exc:
            decode_errors.append({"tile": rel, "error": str(exc)})
        if tile_index % 10 == 0 or tile_index == len(tiles):
            print(f"[{tile_index}/{len(tiles)}] features assigned; layer types={len(layer_totals)}", flush=True)

    if decode_errors:
        raise RuntimeError(f"{len(decode_errors)} source PBFs failed to decode; refusing partial output: {decode_errors[0]}")
    total_features = sum(group_totals.values())
    if total_features == 0:
        raise RuntimeError("No vector features were decoded; refusing to create empty output.")

    # Build in staging. Existing New_Manila remains untouched unless every output passes.
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    output_count = 0
    validation_features = 0
    for group_id in range(1, 52):
        group_root = STAGE / f"boundary-{group_id:02d}"
        for path in tiles:
            rel = path.relative_to(SOURCE)
            rel_posix = rel.as_posix()
            schemas = tile_schemas[rel_posix]
            payload = []
            for schema in schemas:
                feats = buckets.get((group_id, rel_posix, schema["name"]), [])
                payload.append({"name": schema["name"], "features": feats,
                                "extent": schema["extent"], "version": schema["version"]})
            # Use tile-local coordinate bounds to preserve decoded vector-tile geometry
            # coordinates during re-encoding instead of interpreting them as lon/lat.
            encoded = mapbox_vector_tile.encode(
                payload,
                default_options={"y_coord_down": True, "quantize_bounds": (0, 0, 4096, 4096)}
            )
            check = mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
            expected = sum(len(item["features"]) for item in payload)
            actual = sum(len(item.get("features", [])) for item in check.values())
            if actual != expected:
                raise RuntimeError(f"Feature-count validation failed: group={group_id:02d}, tile={rel_posix}, expected={expected}, got={actual}")
            # Validate layer names are preserved, including empty layers.
            if set(check) != {item["name"] for item in payload}:
                raise RuntimeError(f"Layer-name validation failed: group={group_id:02d}, tile={rel_posix}")
            outpath = group_root / rel
            outpath.parent.mkdir(parents=True, exist_ok=True)
            outpath.write_bytes(encoded)
            output_count += 1
            validation_features += actual
        if group_id % 5 == 0 or group_id == 51:
            print(f"Validated groups through boundary-{group_id:02d}; output files={output_count}", flush=True)

    expected_files = 51 * len(tiles)
    if output_count != expected_files:
        raise RuntimeError(f"Expected {expected_files} output PBFs, got {output_count}")
    # Verify every folder has the exact same 141 relative tile paths.
    source_rel = {p.relative_to(SOURCE).as_posix() for p in tiles}
    for group_id in range(1, 52):
        root = STAGE / f"boundary-{group_id:02d}"
        out_rel = {p.relative_to(root).as_posix() for p in root.rglob("*.pbf")}
        if out_rel != source_rel:
            raise RuntimeError(f"Tile path mismatch in boundary-{group_id:02d}: expected {len(source_rel)}, found {len(out_rel)}")

    summary = {
        "status": "validated",
        "source_directory": "Manila/vector-tiles",
        "source_pbf_tiles": len(tiles),
        "source_pbf_modified": False,
        "boundary_source": "complete_data/open free tile/layers/boundary.geojsonl",
        "group_count": 51,
        "assignment_method": "Each feature from every source layer is assigned by geometry centroid to the nearest of the 51 supplied boundary lines; features without geometry use the tile center. This is approximate spatial grouping, not exact administrative clipping.",
        "all_source_layer_names": sorted(layer_totals),
        "source_feature_occurrences_decoded": total_features,
        "output_feature_occurrences_after_roundtrip": validation_features,
        "features_without_geometry_assigned_by_tile_center": skipped_no_geometry,
        "output_pbf_files": output_count,
        "expected_output_pbf_files": expected_files,
        "all_51_groups_have_all_source_tile_paths": True,
        "feature_occurrences_by_group": [{"group": f"{i:02d}", "feature_occurrences": group_totals[i]} for i in range(1, 52)],
        "feature_occurrences_by_layer": [{"layer": name, "feature_occurrences": layer_totals[name]} for name in sorted(layer_totals)],
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (STAGE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (STAGE / "README.md").write_text(
        "# New_Manila — all-layer PBF partition\n\n"
        f"- Source tiles read: {len(tiles)}\n- Groups: 51\n- PBF files generated: {output_count}\n"
        f"- Features assigned across all layers: {total_features}\n- Source files modified: no\n"
        "- Each boundary-XX folder contains the same 141 z/x/y.pbf paths as the source.\n"
        "- All vector layers are retained; features are assigned spatially by centroid to the nearest supplied boundary line.\n"
        "- This is approximate grouping, not exact polygon clipping.\n",
        encoding="utf-8")
    # Replace the previous output only after all 7,191 files have passed validation.
    if OUT.exists():
        shutil.rmtree(OUT)
    STAGE.rename(OUT)
    print(json.dumps({"status": "completed", "source_tiles": len(tiles), "groups": 51,
                      "output_pbf_files": output_count, "features": total_features,
                      "layers": len(layer_totals), "output": "Manila/New_Manila"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
