#!/usr/bin/env python3
"""Audit OSM building-height evidence without inventing heights."""
import csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ermita/maps/generated/ermita-building-footprints.geojson"
OUT = ROOT / "ermita/maps/qa"
CSV_OUT = OUT / "building-height-evidence.csv"
REPORT_OUT = OUT / "building-height-evidence-report.json"


def main():
    raw = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows, counts = [], Counter()
    for feature in raw.get("features", []):
        props = feature.get("properties") or {}
        tags = props.get("tags") or {}
        if not (tags.get("building") or tags.get("building:part")):
            continue
        geom = feature.get("geometry") or {}
        if geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        height = str(tags.get("height", "")).strip()
        levels = str(tags.get("building:levels", "")).strip()
        min_height = str(tags.get("min_height", "")).strip()
        if height:
            evidence = "height_tagged"
            counts["height_tagged"] += 1
        elif levels:
            evidence = "levels_only_no_height_inferred"
            counts["levels_only_no_height_inferred"] += 1
        else:
            evidence = "height_unknown"
            counts["height_unknown"] += 1
        rows.append({
            "source_id": props.get("osm_feature_id", ""),
            "name": tags.get("name", ""),
            "building": tags.get("building", ""),
            "building_part": tags.get("building:part", ""),
            "height_tag_m": height,
            "building_levels_tag": levels,
            "min_height_tag_m": min_height,
            "roof_shape_tag": tags.get("roof:shape", ""),
            "evidence_class": evidence,
            "geometry_type": geom.get("type", ""),
            "source_url": "https://www.openstreetmap.org/" + str(props.get("osm_feature_id", "")),
            "license": "ODbL 1.0",
        })
    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["source_id","name","building","building_part","height_tag_m","building_levels_tag","min_height_tag_m","roof_shape_tag","evidence_class","geometry_type","source_url","license"]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "status": "success",
        "source_file": str(SOURCE.relative_to(ROOT)),
        "output_csv": str(CSV_OUT.relative_to(ROOT)),
        "polygon_feature_count": len(rows),
        "evidence_class_counts": dict(counts),
        "tag_counts": {
            "height": sum(bool(r["height_tag_m"]) for r in rows),
            "building_levels": sum(bool(r["building_levels_tag"]) for r in rows),
            "min_height": sum(bool(r["min_height_tag_m"]) for r in rows),
            "roof_shape": sum(bool(r["roof_shape_tag"]) for r in rows),
        },
        "policy": "Only source-tagged height is reported as height. Levels are retained as levels and are never converted to meters. Missing height remains unknown.",
        "limitations": [
            "OSM tags are contributor-mapped and may be missing or outdated; this is not a field survey.",
            "Building parts may overlap parent buildings and are not necessarily unique buildings.",
            "No heights are inferred from imagery or from storey counts.",
        ],
    }
    REPORT_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
