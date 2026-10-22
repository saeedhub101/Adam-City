#!/usr/bin/env python3
"""Build a metadata-only enrichment index for Button 4 building parts.

This joins existing GLB inventories to the existing OSM building details files.
It never changes or regenerates GLB/GeoJSON geometry and only uses exact OSM IDs.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings"
PARTS = BUILDINGS / "parts"
PARTS_INDEX = PARTS / "parts-inventory-index.json"
DETAILS_GEOJSON = BUILDINGS / "ermita-building-details.geojson"
DETAILS_CSV = BUILDINGS / "osm-building-details.csv"
OUTPUT = PARTS / "building-enrichment-index.json"
REPORT = PARTS / "building-enrichment-report.json"


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def first(tags: dict, *keys):
    for key in keys:
        value = tags.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def main():
    source_index = read_json(PARTS_INDEX)
    details = read_json(DETAILS_GEOJSON)
    by_osm_id = {}

    for feature in details.get("features", []):
        props = feature.get("properties") or {}
        osm_id = props.get("osm_feature_id")
        if not osm_id and props.get("type") and props.get("id") is not None:
            osm_id = f'{props["type"]}/{props["id"]}'
        if osm_id:
            row = by_osm_id.setdefault(osm_id, {})
            row["geojson"] = {
                "geometry_type": (feature.get("geometry") or {}).get("type"),
                "tags": props.get("tags") or {},
                "type": props.get("type"),
                "id": props.get("id"),
            }

    with DETAILS_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            osm_id = row.get("osm_feature_id")
            if not osm_id:
                continue
            try:
                tags = json.loads(row.get("tags_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                tags = {}
            by_osm_id.setdefault(osm_id, {})["csv"] = {
                "name": row.get("name") or "",
                "geometry_type": row.get("geometry_type") or "",
                "latitude": row.get("latitude") or "",
                "longitude": row.get("longitude") or "",
                "tags": tags,
                "source": row.get("source") or "",
                "license": row.get("license") or "",
            }

    inventory_by_key = {}
    for part in range(1, 5):
        path = PARTS / f"part{part}" / f"part{part}-inventory.json"
        if not path.exists():
            continue
        for feature in read_json(path).get("features", []):
            key = f'{feature.get("part")}:{feature.get("source_key")}:{feature.get("source_feature_index")}'
            inventory_by_key[key] = feature

    records = []
    for item in source_index:
        key = f'{item.get("part")}:{item.get("source_key")}:{item.get("source_feature_index")}'
        inventory = inventory_by_key.get(key)
        osm_id = item.get("source_feature_id")
        match = by_osm_id.get(osm_id) if osm_id else None
        source_tags = (match or {}).get("geojson", {}).get("tags") or (match or {}).get("csv", {}).get("tags") or (inventory or {}).get("source_tags") or {}
        props = (inventory or {}).get("source_properties") or {}
        tags = source_tags or props.get("tags") or {}

        def pick(*keys):
            return first(tags, *keys)

        record = {
            "part": item.get("part"),
            "source_key": item.get("source_key"),
            "source_path": item.get("source_path"),
            "source_feature_index": item.get("source_feature_index"),
            "source_feature_id": osm_id,
            "polygon_components_exported": item.get("polygon_components_exported"),
            "identity_match": "exact_osm_id" if match else (
                "basemap_id_only" if props.get("basemap_source_feature_id") else "no_external_identity_match"
            ),
            "name": pick("name", "official_name", "short_name") or (match or {}).get("csv", {}).get("name") or None,
            "official_name": pick("official_name"),
            "brand": pick("brand"),
            "address": {
                "housenumber": pick("addr:housenumber"),
                "street": pick("addr:street"),
                "unit": pick("addr:unit"),
                "postcode": pick("addr:postcode"),
                "city": pick("addr:city"),
                "neighbourhood": pick("addr:neighbourhood"),
                "province": pick("addr:province"),
            },
            "building": {
                "type": pick("building"),
                "levels": pick("building:levels", "building:levels:underground"),
                "height": pick("height"),
                "min_height": pick("min_height"),
                "colour": pick("building:colour", "colour"),
                "material": pick("building:material", "material"),
                "roof_shape": pick("roof:shape"),
                "roof_material": pick("roof:material"),
                "roof_colour": pick("roof:colour"),
            },
            "use": {
                "amenity": pick("amenity"),
                "shop": pick("shop"),
                "office": pick("office"),
                "tourism": pick("tourism"),
                "historic": pick("historic"),
            },
            "osm_tags": tags,
            "source_evidence": {
                "details_geojson": bool(match and match.get("geojson")),
                "details_csv": bool(match and match.get("csv")),
                "source_inventory": bool(inventory),
                "basemap_feature_id": props.get("basemap_source_feature_id"),
            },
            "source_inventory_properties": props or None,
            "enrichment_note": (
                "Attributes joined by exact OSM feature ID; geometry and coordinates were not modified."
                if match else
                "No exact OSM ID match found in current detail sources; no name/address/material was guessed."
            ),
        }
        records.append(record)

    counts = {
        "total": len(records),
        "exact_osm_id": sum(r["identity_match"] == "exact_osm_id" for r in records),
        "basemap_id_only": sum(r["identity_match"] == "basemap_id_only" for r in records),
        "no_external_identity_match": sum(r["identity_match"] == "no_external_identity_match" for r in records),
        "named": sum(bool(r["name"]) for r in records),
        "addressed": sum(any(r["address"].values()) for r in records),
        "with_source_material_tag": sum(any(r["building"][k] for k in ("material", "roof_material", "colour", "roof_colour")) for r in records),
    }
    data = {
        "schema_version": "1.0.0",
        "generated_from": {
            "parts_inventory_index": str(PARTS_INDEX.relative_to(ROOT)),
            "details_geojson": str(DETAILS_GEOJSON.relative_to(ROOT)),
            "details_csv": str(DETAILS_CSV.relative_to(ROOT)),
            "parts_inventory": [f"complete_data/OSM/data/buildings/parts/part{i}/part{i}-inventory.json" for i in range(1, 5)],
        },
        "geometry_policy": "Metadata-only join. No GLB, GeoJSON geometry, feature IDs, centroids, coordinates, heights, or colors are changed.",
        "matching_policy": "Exact OSM feature ID only. No proximity-based guesses.",
        "counts": counts,
        "buildings": records,
    }
    report = {
        "schema_version": "1.0.0",
        "status": "generated",
        "created_from": data["generated_from"],
        "geometry_policy": data["geometry_policy"],
        "matching_policy": data["matching_policy"],
        "counts": counts,
        "limitations": [
            "Names, addresses, and material tags are only present where source data provides them.",
            "An exact OSM ID match does not guarantee that an address or facade material is populated.",
            "This index does not contain facade photographs or inferred photographic materials.",
            "Buildings without exact OSM IDs are intentionally left unguessed; spatial matches require a separate confidence-labelled review.",
        ],
        "index_path": str(OUTPUT.relative_to(ROOT)),
    }
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"index": str(OUTPUT), "report": str(REPORT), "counts": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
