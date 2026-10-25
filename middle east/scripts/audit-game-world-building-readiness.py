#!/usr/bin/env python3
"""Audit saved OSM building layers for game-world readiness.

Uses ijson so large compressed GeoJSON files can be scanned without loading
whole-country datasets into memory. Install with: python -m pip install ijson
"""
import gzip
import json
from collections import Counter
from pathlib import Path

ROOT = Path("middle east")
LAYER_NAMES = ("buildings", "building_details")
HEIGHT_KEYS = ("height", "building:height", "building_height")
LEVEL_KEYS = ("building:levels", "levels")
ROOF_KEYS = ("roof:shape", "roof:material", "roof:colour", "roof:levels")
FACADE_KEYS = ("building:material", "building:colour", "facade:material", "facade:colour")
DETAIL_KEYS = ("window", "door", "entrance")


def present(props, keys):
    return any(props.get(k) not in (None, "", "no", "none") for k in keys)


def main():
    try:
        import ijson
    except ImportError as exc:
        raise SystemExit("Missing dependency: install ijson with python -m pip install ijson") from exc

    reports = []
    for country in ("Jordan", "Palestine"):
        for layer in LAYER_NAMES:
            path = ROOT / country / "layers" / f"{layer}.geojson.gz"
            if not path.is_file():
                reports.append({"country": country, "layer": layer, "status": "missing", "path": str(path)})
                continue
            total = 0
            geometry_types = Counter()
            counts = Counter()
            height_values = Counter()
            polygon_buildings = 0
            tagged_building_features = 0
            with gzip.open(path, "rb") as stream:
                for feature in ijson.items(stream, "features.item"):
                    total += 1
                    geom = feature.get("geometry") or {}
                    geometry_types[geom.get("type", "missing")] += 1
                    props = feature.get("properties") or {}
                    is_building = props.get("building") not in (None, "", "no") or props.get("building:part") not in (None, "", "no")
                    is_polygon = geom.get("type") in ("Polygon", "MultiPolygon")
                    if is_building:
                        tagged_building_features += 1
                    if is_building and is_polygon:
                        polygon_buildings += 1
                    if not (is_building and is_polygon):
                        continue
                    for group, keys in (
                        ("explicit_height", HEIGHT_KEYS),
                        ("levels", LEVEL_KEYS),
                        ("roof_detail", ROOF_KEYS),
                        ("facade_material_or_colour", FACADE_KEYS),
                        ("window_door_entrance", DETAIL_KEYS),
                    ):
                        if present(props, keys):
                            counts[group] += 1
                    for key in HEIGHT_KEYS:
                        if props.get(key) not in (None, ""):
                            height_values[key] += 1
            reports.append({
                "country": country,
                "layer": layer,
                "status": "ok",
                "path": str(path),
                "features_scanned": total,
                "geometry_types": dict(geometry_types),
                "features_tagged_as_building_or_part": tagged_building_features,
                "polygon_building_features": polygon_buildings,
                "features_with_any_tag_group": dict(counts),
                "explicit_height_tag_counts": dict(height_values),
                "note": "Coverage counts below are only for polygon features tagged building/building:part; groups overlap and OSM tags are not proof of a field survey."
            })

    output = ROOT / "game-world-building-readiness.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "schema": "adam-city-game-world-building-readiness-v1",
        "source_licence": "OpenStreetMap ODbL",
        "purpose": "Audit mapped building attributes before game export; does not generate or invent building geometry.",
        "reports": reports
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)
    print(json.dumps(reports, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
