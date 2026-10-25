#!/usr/bin/env python3
"""Export polygon buildings from saved OSM GeoJSON.gz into game-streamable geographic tiles.

Tiles are GeoJSON FeatureCollection JSONL streams (.geojsonl.gz): one compact feature
per line. Geometry coordinates are preserved unchanged (WGS84 lon/lat). Tiles are
assigned by geometry bbox centre, so each source feature appears once. Height
metadata explicitly distinguishes mapped values from level-based estimates.
"""
import gzip
import json
import math
import numbers
import os
from collections import OrderedDict, Counter
from pathlib import Path

ROOT = Path("middle east")
OUT = ROOT / "game-world" / "building-tiles"
TILE_DEGREES = float(os.environ.get("BUILDING_TILE_DEGREES", "0.05"))
MAX_OPEN_FILES = 48
HEIGHT_KEYS = ("height", "building:height", "building_height")
LEVEL_KEYS = ("building:levels", "levels")
MAX_LEVELS_ESTIMATE_M = 60.0


def numbers_in_coords(value):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[0], numbers.Number) and isinstance(value[1], numbers.Number):
            yield float(value[0]), float(value[1])
        else:
            for child in value:
                yield from numbers_in_coords(child)


def parse_height(props):
    for key in HEIGHT_KEYS:
        raw = props.get(key)
        if raw is None or raw == "":
            continue
        try:
            value = float(str(raw).strip().lower().replace(" metres", "").replace(" meters", "").replace(" m", ""))
            if math.isfinite(value) and 0.5 <= value <= 1000:
                return round(value, 2), "osm_height", key
        except (ValueError, TypeError):
            pass
    for key in LEVEL_KEYS:
        raw = props.get(key)
        if raw is None or raw == "":
            continue
        try:
            levels = float(raw)
            if math.isfinite(levels) and 0 < levels <= 200:
                return round(min(levels * 3.0, MAX_LEVELS_ESTIMATE_M), 2), "levels_estimate", key
        except (ValueError, TypeError):
            pass
    return None, "unknown", None


def is_building(props):
    return (props.get("building") not in (None, "", "no")
            or props.get("building:part") not in (None, "", "no"))


def safe_id(feature, props, country, layer, sequence):
    value = feature.get("id", props.get("@id", props.get("osm_id")))
    if value is None:
        value = f"{country.lower()}:{layer}:{sequence}"
    return str(value)


def main():
    try:
        import ijson
    except ImportError as exc:
        raise SystemExit("Install ijson: python -m pip install ijson") from exc
    if not (0.001 <= TILE_DEGREES <= 1.0):
        raise SystemExit("BUILDING_TILE_DEGREES must be between 0.001 and 1.0")

    OUT.mkdir(parents=True, exist_ok=True)
    # Remove only previous generated tile outputs, never source layers or unrelated files.
    for country_dir in OUT.iterdir() if OUT.exists() else []:
        if country_dir.is_dir():
            for old in country_dir.rglob("*.geojsonl.gz"):
                old.unlink()
            for old in sorted(country_dir.rglob("*"), reverse=True):
                if old.is_dir():
                    try: old.rmdir()
                    except OSError: pass

    report = {
        "schema": "adam-city-game-building-tiles-v1",
        "source": "Repository-stored OpenStreetMap GeoJSON exports",
        "license": "OpenStreetMap ODbL; retain attribution and comply with ODbL",
        "coordinate_reference_system": "EPSG:4326 (longitude, latitude)",
        "tile_scheme": {"type": "fixed geographic grid", "tile_degrees": TILE_DEGREES,
                        "assignment": "centre of source geometry bounding box; no geometry simplification or coordinate transformation"},
        "format": "gzip-compressed newline-delimited GeoJSON Features; one feature per line",
        "height_policy": {
            "osm_height": "parsed from explicit OSM height tag; units assumed metres unless suffix indicates metres",
            "levels_estimate": "building levels multiplied by 3 m; approximate, not surveyed",
            "unknown": "no usable height tag; do not silently invent a height"
        },
        "countries": {}
    }

    for country in ("Jordan", "Palestine"):
        country_stats = Counter()
        tile_counts = Counter()
        country_out = OUT / country
        country_out.mkdir(parents=True, exist_ok=True)
        handles = OrderedDict()

        def write_tile(tile_key, record):
            path = country_out / f"{tile_key}.geojsonl.gz"
            handle = handles.pop(path, None)
            if handle is None:
                handle = gzip.open(path, "at", encoding="utf-8", compresslevel=6)
            handles[path] = handle
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=float) + "\n")
            if len(handles) > MAX_OPEN_FILES:
                _, old_handle = handles.popitem(last=False)
                old_handle.close()

        for layer in ("buildings",):
            path = ROOT / country / "layers" / f"{layer}.geojson.gz"
            if not path.is_file():
                country_stats[f"missing_{layer}_source"] += 1
                continue
            with gzip.open(path, "rb") as stream:
                for sequence, feature in enumerate(ijson.items(stream, "features.item"), 1):
                    country_stats[f"{layer}_features_scanned"] += 1
                    props = feature.get("properties") or {}
                    geom = feature.get("geometry") or {}
                    if not is_building(props) or geom.get("type") not in ("Polygon", "MultiPolygon"):
                        continue
                    coords = geom.get("coordinates")
                    points = list(numbers_in_coords(coords))
                    if not points:
                        country_stats["skipped_empty_geometry"] += 1
                        continue
                    min_lon = min(p[0] for p in points); max_lon = max(p[0] for p in points)
                    min_lat = min(p[1] for p in points); max_lat = max(p[1] for p in points)
                    if not all(math.isfinite(v) for v in (min_lon, max_lon, min_lat, max_lat)):
                        country_stats["skipped_invalid_coordinates"] += 1
                        continue
                    lon = (min_lon + max_lon) / 2
                    lat = (min_lat + max_lat) / 2
                    x = math.floor(lon / TILE_DEGREES)
                    y = math.floor(lat / TILE_DEGREES)
                    tile_key = f"{x}_{y}"
                    height, height_source, height_tag = parse_height(props)
                    out_props = dict(props)
                    out_props["game_height_m"] = height
                    out_props["game_height_source"] = height_source
                    if height_tag:
                        out_props["game_height_tag"] = height_tag
                    out_props["source_layer"] = layer
                    out_props["source_country"] = country
                    out_props["source_license"] = "OpenStreetMap ODbL"
                    record = {
                        "type": "Feature",
                        "id": safe_id(feature, props, country, layer, sequence),
                        "geometry": geom,
                        "properties": out_props
                    }
                    write_tile(tile_key, record)
                    tile_counts[tile_key] += 1
                    country_stats[f"{layer}_polygon_buildings_exported"] += 1
                    country_stats[f"height_{height_source}"] += 1
        for handle in handles.values():
            handle.close()

        country_stats["unique_tiles"] = len(tile_counts)
        country_stats["features_exported_total"] = sum(tile_counts.values())
        country_stats["warning"] = "Game tiles use the canonical buildings layer only to prevent duplicate physical buildings from the overlapping building_details export. building_details remains available separately in the source layers."
        report["countries"][country] = dict(country_stats)
        # Per-country manifest lists relative tile path and feature count.
        manifest = {
            "schema": "adam-city-building-tile-manifest-v1",
            "country": country,
            "tile_degrees": TILE_DEGREES,
            "format": "GeoJSONL gzip; one Feature per line",
            "tiles": [{"id": key, "path": f"{key}.geojsonl.gz", "feature_count": count}
                      for key, count in sorted(tile_counts.items())]
        }
        (country_out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    (ROOT / "game-world-building-tiles-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
