#!/usr/bin/env python3
"""Create genuinely new PBF tile sets, partitioning source building features into 51 boundary groups.

The source vector tiles are read-only. Group assignment uses each building feature's
centroid and the nearest of the 51 line geometries in complete_data/open free tile/layers/boundary.geojsonl.
Original tile-local feature coordinates, properties, layer names and extents are preserved.
"""
from __future__ import annotations

import json
import math
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
EARTH_R = 6371008.8
RAD = math.pi / 180.0
REF_LAT = 14.45
BUILDING_LAYERS = {"building", "buildings"}


def project(lon: float, lat: float) -> tuple[float, float]:
    return EARTH_R * lon * RAD * math.cos(REF_LAT * RAD), EARTH_R * lat * RAD


def read_boundaries() -> list[dict[str, Any]]:
    if not BOUNDARY_PATH.is_file():
        raise FileNotFoundError(f"Boundary input missing: {BOUNDARY_PATH}")
    result = []
    for record, line in enumerate(BOUNDARY_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        feature = json.loads(line)
        geom = feature.get("geometry") or {}
        if geom.get("type") not in ("LineString", "MultiLineString"):
            raise ValueError(f"Boundary record {record} has unsupported geometry {geom.get('type')}")
        parts = [LineString([project(float(p[0]), float(p[1])) for p in coords if len(p) >= 2])
                 for coords in ( [geom.get("coordinates", [])] if geom["type"] == "LineString"
                                 else geom.get("coordinates", []) )]
        parts = [part for part in parts if not part.is_empty and len(part.coords) >= 2]
        if not parts:
            raise ValueError(f"Boundary record {record} contains no usable lines")
        result.append({"record": record, "feature_id": feature.get("id"),
                       "properties": feature.get("properties") or {},
                       "geometry": unary_union(parts)})
    if len(result) != 51:
        raise ValueError(f"Expected exactly 51 boundary records, found {len(result)}")
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


def assign_boundary(lon: float, lat: float, boundaries: list[dict]) -> tuple[int, float]:
    point = Point(*project(lon, lat))
    distances = [(float(item["geometry"].distance(point)), int(item["record"])) for item in boundaries]
    distance, record = min(distances)
    return record, distance


def main() -> None:
    tiles = sorted(p for p in SOURCE.rglob("*.pbf") if p.is_file())
    if not tiles:
        raise RuntimeError(f"No source PBF tiles found in {SOURCE}")
    boundaries = read_boundaries()
    print(f"Input PBF tiles: {len(tiles)}; boundary records: {len(boundaries)}", flush=True)

    # Accumulate the original encoded feature objects per output boundary and source tile.
    buckets: dict[tuple[int, int, int, int], dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
    assigned_features = 0
    skipped_no_geometry = 0
    layer_names: set[str] = set()
    errors = []

    for tile_index, path in enumerate(tiles, 1):
        rel = path.relative_to(SOURCE)
        z, tx, ty = map(int, rel.with_suffix("").parts[-3:])
        try:
            decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
            for layer_name, layer in decoded.items():
                if str(layer_name).lower() not in BUILDING_LAYERS:
                    continue
                layer_names.add(str(layer_name))
                extent = int(layer.get("extent", 4096))
                for feature_index, feature in enumerate(layer.get("features", [])):
                    center = feature_center(path, feature, extent)
                    if center is None:
                        skipped_no_geometry += 1
                        continue
                    boundary_record, _distance = assign_boundary(*center, boundaries)
                    # Key each feature occurrence uniquely within this source tile/layer.
                    key = f"{layer_name}:{feature_index}"
                    buckets[(boundary_record, z, tx, ty)][str(layer_name)][key] = {
                        "feature": feature, "extent": extent
                    }
                    assigned_features += 1
        except Exception as exc:
            errors.append({"tile": rel.as_posix(), "error": str(exc)})
        if tile_index % 10 == 0 or tile_index == len(tiles):
            print(f"[{tile_index}/{len(tiles)}] building features assigned={assigned_features}; output tile groups={len(buckets)}", flush=True)

    if errors:
        raise RuntimeError(f"{len(errors)} source PBF tiles failed to decode; refusing to publish partial output. First: {errors[0]}")
    if not assigned_features:
        raise RuntimeError("No building features found in source PBF tiles; no output written.")

    # Replace only generated outputs, and only after all source tiles passed validation.
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    counts = {i: 0 for i in range(1, 52)}
    output_files = 0

    for (boundary_record, z, tx, ty), layers in sorted(buckets.items()):
        outpath = OUT / f"boundary-{boundary_record:02d}" / str(z) / str(tx) / f"{ty}.pbf"
        outpath.parent.mkdir(parents=True, exist_ok=True)
        payload = []
        for layer_name, items in layers.items():
            extents = {int(item["extent"]) for item in items.values()}
            if len(extents) != 1:
                raise RuntimeError(f"Mixed layer extents for {outpath} / {layer_name}: {sorted(extents)}")
            features = [item["feature"] for item in items.values()]
            payload.append({"name": layer_name, "features": features, "extent": extents.pop(), "version": 2})
            counts[boundary_record] += len(features)
        encoded = mapbox_vector_tile.encode(payload, default_options={"y_coord_down": True})
        decoded_check = mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
        expected = sum(len(layer["features"]) for layer in payload)
        actual = sum(len(layer.get("features", [])) for layer in decoded_check.values())
        if actual != expected:
            raise RuntimeError(f"PBF validation failed for {outpath}: expected {expected} features, got {actual}")
        outpath.write_bytes(encoded)
        output_files += 1

    summary = {
        "status": "completed",
        "source_directory": "Manila/vector-tiles",
        "source_pbf_tiles_scanned": len(tiles),
        "source_pbf_modified": False,
        "boundary_source": "complete_data/open free tile/layers/boundary.geojsonl",
        "boundary_records": 51,
        "assignment_method": "For each original building feature, convert its tile-local geometry centroid to lon/lat, then assign to the nearest of the 51 supplied boundary line geometries. This deliberately follows the existing 51-record grouping method; it does not infer administrative polygons.",
        "building_layer_names": sorted(layer_names),
        "building_feature_occurrences_assigned": assigned_features,
        "features_skipped_without_geometry": skipped_no_geometry,
        "new_pbf_files_written": output_files,
        "output_directories": [f"boundary-{i:02d}" for i in range(1, 52)],
        "building_feature_occurrences_by_boundary": [
            {"boundary_record": f"{i:02d}", "feature_occurrences": counts[i]} for i in range(1, 52)
        ],
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# New_Manila — newly generated boundary-partitioned PBF tiles\n\n"
        f"- Source PBF tiles scanned: {len(tiles)}\n"
        f"- Building feature occurrences assigned: {assigned_features}\n"
        f"- New PBF files written: {output_files}\n"
        "- Original PBF files were not modified.\n"
        "- Each boundary-XX folder contains newly encoded PBF tiles at z/x/y.pbf.\n"
        "- Assignment uses the nearest of the 51 supplied boundary lines and each feature centroid.\n",
        encoding="utf-8"
    )
    print(json.dumps({"status": "completed", "source_tiles": len(tiles), "assigned_features": assigned_features,
                      "new_pbf_files_written": output_files, "boundary_counts": counts}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
