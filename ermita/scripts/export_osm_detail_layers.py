#!/usr/bin/env python3
"""Export separate, geometry-preserving OSM detail layers into complete_data/OSM.

Reads the committed OSM feature snapshot. It does not merge categories, alter source
features, fabricate missing tags, or call Overpass. Re-run the OSM import first when
the source snapshot needs refreshing.
"""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ermita/maps/generated/ermita-features.geojson"
OSM = ROOT / "complete_data/OSM"
PEDESTRIAN = OSM / "data/pedestrian"
ROADS = OSM / "data/roads"
BUILDINGS = OSM / "data/buildings"
for folder in (PEDESTRIAN, ROADS, BUILDINGS, OSM / "quality"):
    folder.mkdir(parents=True, exist_ok=True)

PEDESTRIAN_KEYS = {
    "sidewalk", "sidewalk:both", "sidewalk:left", "sidewalk:right",
    "sidewalk:surface", "sidewalk:both:surface", "sidewalk:left:surface", "sidewalk:right:surface",
    "footway", "foot", "crossing", "crossing:markings", "crossing:signals",
    "crossing:island", "crossing:surface", "tactile_paving", "kerb", "ramp",
    "wheelchair", "incline", "lit", "smoothness", "width", "surface",
    "entrance", "door", "barrier", "bollard", "fence", "gate", "handrail",
    "steps", "conveying", "bench", "waste_basket", "street_lamp", "traffic_sign",
    "traffic_signals", "highway", "amenity", "man_made"
}
PEDESTRIAN_HIGHWAYS = {
    "footway", "pedestrian", "path", "steps", "crossing", "corridor",
    "bridleway", "living_street", "platform", "track"
}
ROAD_KEYS = {
    "highway", "name", "official_name", "alt_name", "ref", "surface", "smoothness",
    "width", "est_width", "lanes", "lanes:forward", "lanes:backward", "lanes:both_ways",
    "oneway", "oneway:bicycle", "turn", "turn:lanes", "change", "destination",
    "maxspeed", "maxspeed:forward", "maxspeed:backward", "access", "vehicle", "motor_vehicle",
    "foot", "bicycle", "cycleway", "cycleway:left", "cycleway:right", "cycleway:both",
    "cycleway:surface", "sidewalk", "sidewalk:left", "sidewalk:right", "sidewalk:both",
    "sidewalk:surface", "lit", "lanes", "parking:lane:both", "parking:lane:left",
    "parking:lane:right", "shoulder", "shoulder:width", "bridge", "bridge:name",
    "tunnel", "layer", "covered", "ford", "service", "junction", "tracktype",
    "incline", "segregated", "access:conditional", "traffic_calming", "crossing",
    "railway", "route", "public_transport"
}
BUILDING_KEYS = {
    "building", "building:part", "building:use", "building:levels", "building:levels:underground",
    "building:min_level", "building:material", "building:colour", "building:color",
    "building:condition", "building:structure", "height", "min_height", "min_level",
    "roof:shape", "roof:height", "roof:levels", "roof:material", "roof:colour", "roof:color",
    "roof:angle", "roof:direction", "roof:orientation", "roof:ridge", "roof:ridge:height",
    "roof:edge", "roof:colour", "roof:colour", "roof:solar", "roof:shape",
    "name", "official_name", "alt_name", "addr:housenumber", "addr:street", "addr:full",
    "addr:suburb", "addr:city", "addr:postcode", "start_date", "construction_date",
    "architect", "heritage", "historic", "wikidata", "wikipedia", "entrance", "level"
}

def tags(feature):
    p = feature.get("properties") or {}
    t = p.get("tags")
    if isinstance(t, dict):
        return t
    # Some existing exports flatten tags directly into properties.
    return {k: v for k, v in p.items() if k not in {
        "osm_feature_id", "osm_id", "type", "id", "source", "license"
    }}

def osm_id(feature):
    p = feature.get("properties") or {}
    return str(p.get("osm_feature_id") or feature.get("id") or
               f'{p.get("type", "feature")}/{p.get("id", "unknown")}')

def is_pedestrian(feature):
    t = tags(feature)
    highway_value = t.get("highway")
    amenity_value = t.get("amenity")
    return (
        highway_value in PEDESTRIAN_HIGHWAYS
        or highway_value in {"street_lamp", "traffic_signals", "stop", "give_way"}
        or amenity_value in {"bench", "waste_basket", "drinking_water", "fountain"}
        or t.get("man_made") == "street_lamp"
        or (
            bool(PEDESTRIAN_KEYS.intersection(t))
            and bool({
                "sidewalk", "sidewalk:both", "sidewalk:left", "sidewalk:right",
                "tactile_paving", "kerb", "ramp", "entrance", "door", "barrier",
                "bollard", "fence", "gate", "bench", "waste_basket", "street_lamp",
                "crossing", "crossing:markings", "crossing:signals", "wheelchair",
                "footway", "handrail", "steps", "traffic_sign", "traffic_signals"
            }.intersection(t))
        )
    )

def is_road(feature):
    t = tags(feature)
    return "highway" in t or "railway" in t or "route" in t or "public_transport" in t

def is_building(feature):
    t = tags(feature)
    return "building" in t or "building:part" in t

def write_geojson(path, name, features, layer):
    collection = {
        "type": "FeatureCollection", "name": name,
        "source": "https://www.openstreetmap.org/copyright",
        "license": "OpenStreetMap contributors, ODbL 1.0",
        "layer": layer,
        "feature_count": len(features),
        "features": features,
    }
    path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

def write_index(path, features, selected_keys):
    fields = ["osm_feature_id", "name", "geometry_type", "tags_json", "selected_detail_tags", "source", "license"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for feat in features:
            t = tags(feat)
            geom = feat.get("geometry") or {}
            chosen = {k: t[k] for k in sorted(selected_keys.intersection(t)) if k in t}
            w.writerow({
                "osm_feature_id": osm_id(feat),
                "name": t.get("name", ""),
                "geometry_type": geom.get("type", ""),
                "tags_json": json.dumps(t, ensure_ascii=False, sort_keys=True),
                "selected_detail_tags": json.dumps(chosen, ensure_ascii=False, sort_keys=True),
                "source": "OpenStreetMap contributors",
                "license": "ODbL 1.0",
            })

def main():
    if not SOURCE.is_file():
        raise SystemExit(f"Missing committed OSM snapshot: {SOURCE}")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    all_features = source.get("features", [])
    pedestrian = [f for f in all_features if f.get("geometry") and is_pedestrian(f)]
    roads = [f for f in all_features if f.get("geometry") and is_road(f)]
    buildings = [f for f in all_features if f.get("geometry") and is_building(f)]

    write_geojson(PEDESTRIAN / "ermita-pedestrian-street-details.geojson",
                  "Ermita pedestrian street details — separate OSM layer", pedestrian, "pedestrian")
    write_index(PEDESTRIAN / "ermita-pedestrian-street-details.csv", pedestrian, PEDESTRIAN_KEYS)

    write_geojson(ROADS / "ermita-road-engineering-details.geojson",
                  "Ermita road engineering details — separate OSM layer", roads, "road-engineering")
    write_index(ROADS / "ermita-road-engineering-details.csv", roads, ROAD_KEYS)

    write_geojson(BUILDINGS / "ermita-building-roof-details.geojson",
                  "Ermita building and roof details — separate OSM layer", buildings, "building-roof-details")
    write_index(BUILDINGS / "ermita-building-roof-details.csv", buildings, BUILDING_KEYS)

    report = {
        "source_file": "ermita/maps/generated/ermita-features.geojson",
        "source_feature_count": len(all_features),
        "layers": {
            "pedestrian_street_details": {
                "feature_count": len(pedestrian),
                "files": ["data/pedestrian/ermita-pedestrian-street-details.geojson",
                          "data/pedestrian/ermita-pedestrian-street-details.csv"],
                "tag_key_presence_counts": dict(sorted(Counter(k for f in pedestrian for k in tags(f)).items())),
            },
            "road_engineering_details": {
                "feature_count": len(roads),
                "files": ["data/roads/ermita-road-engineering-details.geojson",
                          "data/roads/ermita-road-engineering-details.csv"],
                "tag_key_presence_counts": dict(sorted(Counter(k for f in roads for k in tags(f)).items())),
            },
            "building_roof_details": {
                "feature_count": len(buildings),
                "files": ["data/buildings/ermita-building-roof-details.geojson",
                          "data/buildings/ermita-building-roof-details.csv"],
                "tag_key_presence_counts": dict(sorted(Counter(k for f in buildings for k in tags(f)).items())),
            },
        },
        "policy": "Separate layers; no cross-category merging; original feature geometries and complete OSM tags preserved; missing tags are not fabricated.",
        "source": "OpenStreetMap contributors",
        "license": "ODbL 1.0",
    }
    (OSM / "quality/osm-detail-layer-export-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["feature_count"] for k, v in report["layers"].items()}, ensure_ascii=False))

if __name__ == "__main__":
    main()
