#!/usr/bin/env python3
"""Convert the original Manila vector-tile PBFs into geographic GeoJSON.

Reads Manila/vector-tiles/{z}/{x}/{y}.pbf without modifying source files.
Writes one GeoJSON FeatureCollection per source tile under Manila/GeoJSON_Source,
preserving the z/x/y layout. Every feature includes its source layer and source
tile; MVT tile-local coordinates are converted to WGS84 longitude/latitude.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import mapbox_vector_tile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Manila" / "vector-tiles"
DEFAULT_OUTPUT = ROOT / "Manila" / "GeoJSON_Source"


def tile_xy_to_lonlat(z: int, x_tile: int, y_tile: int, px: float, py: float, extent: int) -> list[float]:
    n = 2 ** z
    world_x = x_tile + px / extent
    world_y = y_tile + py / extent
    lon = world_x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * world_y / n)))
    lat = math.degrees(lat_rad)
    return [lon, lat]


def transform_coords(value: Any, z: int, tx: int, ty: int, extent: int) -> Any:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
            return tile_xy_to_lonlat(z, tx, ty, float(value[0]), float(value[1]), extent)
        return [transform_coords(item, z, tx, ty, extent) for item in value]
    return value


def convert_tile(path: Path, source_root: Path) -> dict[str, Any]:
    relative = path.relative_to(source_root)
    z, tx, ty = map(int, relative.with_suffix("").parts[-3:])
    decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
    features: list[dict[str, Any]] = []
    layer_summary: dict[str, int] = {}
    for layer_name, layer in decoded.items():
        extent = int(layer.get("extent") or 4096)
        layer_features = layer.get("features") or []
        layer_summary[layer_name] = len(layer_features)
        for item in layer_features:
            geometry = item.get("geometry")
            if not geometry:
                continue
            properties = dict(item.get("properties") or {})
            properties["_source_layer"] = layer_name
            properties["_source_tile"] = relative.as_posix()
            if item.get("id") is not None:
                properties["_source_feature_id"] = item["id"]
            features.append({
                "type": "Feature",
                "id": f"{layer_name}:{item.get('id')}" if item.get("id") is not None else None,
                "properties": properties,
                "geometry": {
                    "type": geometry["type"],
                    "coordinates": transform_coords(geometry["coordinates"], z, tx, ty, extent),
                },
            })
    return {
        "type": "FeatureCollection",
        "name": relative.as_posix(),
        "metadata": {
            "source_pbf": f"Manila/vector-tiles/{relative.as_posix()}",
            "z": z, "x": tx, "y": ty,
            "feature_count": len(features),
            "source_layer_feature_counts": layer_summary,
            "coordinate_system": "WGS84 (EPSG:4326)",
        },
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="Convert only the first N tiles (0 = all).")
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    paths = sorted(source.rglob("*.pbf"), key=lambda p: p.as_posix())
    if not paths:
        raise SystemExit(f"No source PBF files found under {source}")
    if args.limit > 0:
        paths = paths[:args.limit]
    total_features = 0
    for index, path in enumerate(paths, 1):
        relative = path.relative_to(source).with_suffix(".geojson")
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = convert_tile(path, source)
        temp = destination.with_suffix(destination.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        temp.replace(destination)
        total_features += data["metadata"]["feature_count"]
        print(json.dumps({
            "event": "tile_converted", "completed": index, "total": len(paths),
            "source": path.relative_to(source).as_posix(),
            "output": destination.relative_to(output).as_posix(),
            "features": data["metadata"]["feature_count"],
            "layers": data["metadata"]["source_layer_feature_counts"],
        }, ensure_ascii=False), flush=True)
    report = {
        "status": "completed",
        "source_directory": "Manila/vector-tiles",
        "output_directory": "Manila/GeoJSON_Source",
        "tiles_converted": len(paths),
        "feature_count": total_features,
        "source_files_modified": False,
        "coordinate_system": "WGS84 (EPSG:4326)",
        "note": "Each tile is exported independently; repeated features across zoom levels or tiles are not deduplicated.",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "conversion-summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
