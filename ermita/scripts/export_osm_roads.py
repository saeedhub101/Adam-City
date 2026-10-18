#!/usr/bin/env python3
"""Export real mapped OSM road/path centerlines from the existing Ermita cache.

No synthetic streets are created and no network request is made. Geometry is
copied from OSM way node coordinates already stored in ermita-osm-raw.json.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "ermita/maps/generated/ermita-osm-raw.json"
OUT = ROOT / "ermita/maps/generated/ermita-road-network.geojson"
SEGMENTS = ROOT / "ermita/streets/street_segments.csv"
REPORT = ROOT / "ermita/maps/generated/road-network-export-report.json"

FIELDS = [
    "segment_id", "street_name", "alternate_name", "highway_class", "surface",
    "lanes", "oneway", "sidewalk", "lit", "geometry_id", "source_url",
    "source_date", "license", "verification_status", "notes",
]


def main():
    if not RAW.exists():
        raise FileNotFoundError(f"Existing OSM cache not found: {RAW}")
    source = json.loads(RAW.read_text(encoding="utf-8"))
    elements = source.get("elements", [])
    features = []
    rows = []
    counts = {}
    skipped = 0
    for element in elements:
        if element.get("type") != "way":
            continue
        tags = element.get("tags") or {}
        highway = tags.get("highway")
        coords = [
            [node.get("lon"), node.get("lat")]
            for node in (element.get("geometry") or [])
            if node.get("lon") is not None and node.get("lat") is not None
        ]
        if not highway or len(coords) < 2:
            continue
        # A road centerline must have at least two distinct coordinates.
        if len(set((p[0], p[1]) for p in coords)) < 2:
            skipped += 1
            continue
        osm_id = f"way/{element['id']}"
        props = {
            "osm_feature_id": osm_id,
            "osm_way_id": element["id"],
            "name": tags.get("name", ""),
            "official_name": tags.get("official_name", ""),
            "alt_name": tags.get("alt_name", ""),
            "name:en": tags.get("name:en", ""),
            "ref": tags.get("ref", ""),
            "highway": highway,
            "surface": tags.get("surface", ""),
            "lanes": tags.get("lanes", ""),
            "oneway": tags.get("oneway", ""),
            "sidewalk": tags.get("sidewalk", ""),
            "lit": tags.get("lit", ""),
            "maxspeed": tags.get("maxspeed", ""),
            "access": tags.get("access", ""),
            "service": tags.get("service", ""),
            "bridge": tags.get("bridge", ""),
            "tunnel": tags.get("tunnel", ""),
            "layer": tags.get("layer", ""),
            "width": tags.get("width", ""),
            "source": "OpenStreetMap contributors",
            "source_url": f"https://www.openstreetmap.org/way/{element['id']}",
            "license": "ODbL 1.0",
            "geometry_kind": "mapped OSM way centerline",
        }
        features.append({
            "type": "Feature",
            "id": osm_id,
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": props,
        })
        rows.append({
            "segment_id": osm_id,
            "street_name": props["name"],
            "alternate_name": props["alt_name"],
            "highway_class": highway,
            "surface": props["surface"],
            "lanes": props["lanes"],
            "oneway": props["oneway"],
            "sidewalk": props["sidewalk"],
            "lit": props["lit"],
            "geometry_id": osm_id,
            "source_url": props["source_url"],
            "source_date": element.get("timestamp", ""),
            "license": "ODbL 1.0",
            "verification_status": "osm_mapped_geometry",
            "notes": "Actual OSM way centerline from cached source; unnamed ways remain included. Check current imagery/local evidence for completeness.",
        })
        counts[highway] = counts.get(highway, 0) + 1

    if not features:
        raise RuntimeError("No road/path centerlines found in cached OSM elements; refusing to overwrite outputs.")
    collection = {
        "type": "FeatureCollection",
        "name": "Ermita mapped roads and paths — OpenStreetMap",
        "source": "https://www.openstreetmap.org/copyright",
        "license": "OpenStreetMap contributors, ODbL 1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_count": len(features),
        "features": features,
    }
    OUT.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    SEGMENTS.parent.mkdir(parents=True, exist_ok=True)
    with SEGMENTS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "status": "success",
        "source_file": str(RAW.relative_to(ROOT)),
        "road_geojson": str(OUT.relative_to(ROOT)),
        "street_segments_csv": str(SEGMENTS.relative_to(ROOT)),
        "source_element_count": len(elements),
        "road_path_way_count": len(features),
        "skipped_degenerate_way_count": skipped,
        "highway_class_counts": dict(sorted(counts.items())),
        "named_way_count": sum(1 for f in features if f["properties"]["name"]),
        "unnamed_way_count": sum(1 for f in features if not f["properties"]["name"]),
        "geometry": "Original OSM way node coordinates represented as LineString; no synthetic or straightened roads.",
        "limitations": [
            "This exports existing cached OSM geometry and does not fetch live updates.",
            "OSM coverage may omit real roads or tags; blank name means the source way is unnamed, not that a name was invented.",
            "Highway includes roads, paths, pedestrian ways, service roads and other OSM highway classes; filter by properties.highway for a specific display.",
            "Road lines are centerlines, not road-surface polygons or lane-level surveyed geometry.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
