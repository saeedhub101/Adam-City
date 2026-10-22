#!/usr/bin/env python3
"""Read-only audit of building sources, inventories, enrichment index, and GLB derivatives.

This script never modifies source data, inventories, indexes, or GLB assets.
It writes only complete_data/OSM/data/buildings/parts/building-data-full-audit.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings"
PARTS = BUILDINGS / "parts"
OUT = PARTS / "building-data-full-audit.json"


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main():
    required = [
        BUILDINGS / "ermita-building-footprints.geojson",
        BUILDINGS / "ermita-building-details.geojson",
        BUILDINGS / "ermita-building-roof-details.geojson",
        BUILDINGS / "osm-building-details.csv",
        PARTS / "parts-inventory-index.json",
        PARTS / "parts-report.json",
        PARTS / "building-enrichment-index.json",
        PARTS / "building-enrichment-report.json",
        PARTS / "enhanced" / "enhancement-report.json",
        BUILDINGS / "ermita-glb-parts" / "buildings_parts_index.json",
        BUILDINGS / "ermita-glb-parts" / "buildings_parts_report.json",
    ]
    missing = [rel(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Required building data is missing: " + ", ".join(missing))

    footprints_path = BUILDINGS / "ermita-building-footprints.geojson"
    details_path = BUILDINGS / "ermita-building-details.geojson"
    roofs_path = BUILDINGS / "ermita-building-roof-details.geojson"
    csv_path = BUILDINGS / "osm-building-details.csv"
    footprints = read_json(footprints_path)
    details = read_json(details_path)
    roofs = read_json(roofs_path)
    parts_index = read_json(PARTS / "parts-inventory-index.json")
    parts_report = read_json(PARTS / "parts-report.json")
    enrichment = read_json(PARTS / "building-enrichment-index.json")
    enrichment_report = read_json(PARTS / "building-enrichment-report.json")
    enhancement_report = read_json(PARTS / "enhanced" / "enhancement-report.json")
    six_index = read_json(BUILDINGS / "ermita-glb-parts" / "buildings_parts_index.json")
    six_report = read_json(BUILDINGS / "ermita-glb-parts" / "buildings_parts_report.json")

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    csv_ids = [r.get("osm_feature_id", "").strip() for r in csv_rows if r.get("osm_feature_id", "").strip()]

    records = enrichment.get("buildings", [])
    match_counts = Counter(r.get("match_method", "missing") for r in records)
    per_part = Counter(str(r.get("part", "missing")) for r in records)
    source_key_counts = Counter(str(r.get("source_key", "missing")) for r in records)
    field_coverage = {
        "name": sum(bool(r.get("name")) for r in records),
        "official_name": sum(bool(r.get("official_name")) for r in records),
        "brand": sum(bool(r.get("brand")) for r in records),
        "address": sum(any((r.get("address") or {}).values()) for r in records),
        "height": sum(bool((r.get("building") or {}).get("height")) for r in records),
        "levels": sum(bool((r.get("building") or {}).get("levels")) for r in records),
        "material_or_colour": sum(any((r.get("building") or {}).get(k) for k in ("material", "colour", "roof_material", "roof_colour")) for r in records),
        "source_evidence": sum(bool(r.get("source_evidence")) for r in records),
        "original_inventory_properties": sum(bool(r.get("source_inventory_properties")) for r in records),
    }
    duplicate_keys = Counter(
        (r.get("part"), r.get("source_key"), r.get("source_feature_index"))
        for r in records
    )
    duplicates = [
        {"part": k[0], "source_key": k[1], "source_feature_index": k[2], "count": n}
        for k, n in duplicate_keys.items() if n > 1
    ]

    inventories = []
    for part in range(1, 5):
        folder = PARTS / f"part{part}"
        inventory_path = folder / f"part{part}-inventory.json"
        origin_path = folder / f"part{part}-origin.json"
        glb_path = folder / f"part{part}.glb"
        if not all(p.is_file() for p in (inventory_path, origin_path, glb_path)):
            raise FileNotFoundError(f"Missing original part assets for part {part}")
        inventory = read_json(inventory_path)
        features = inventory.get("features", [])
        enhanced_glb = PARTS / "enhanced" / f"part{part}-detailed.glb"
        enhanced_report = PARTS / "enhanced" / f"part{part}-detailed-report.json"
        if not enhanced_glb.is_file() or not enhanced_report.is_file():
            raise FileNotFoundError(f"Missing enhanced output/report for part {part}")
        inventories.append({
            "part": part,
            "original_glb": rel(glb_path),
            "original_glb_bytes": glb_path.stat().st_size,
            "origin_sidecar": rel(origin_path),
            "inventory": rel(inventory_path),
            "inventory_feature_count": len(features),
            "inventory_sha256": sha256(inventory_path),
            "origin_sha256": sha256(origin_path),
            "enhanced_glb": rel(enhanced_glb),
            "enhanced_glb_bytes": enhanced_glb.stat().st_size,
            "enhanced_report": rel(enhanced_report),
            "enhanced_report_sha256": sha256(enhanced_report),
        })

    six_parts = []
    for item in six_index.get("parts", []):
        glb = BUILDINGS / "ermita-glb-parts" / item.get("file", "")
        inv = BUILDINGS / "ermita-glb-parts" / item.get("inventory", "")
        origin = BUILDINGS / "ermita-glb-parts" / item.get("origin", "")
        six_parts.append({
            "part": item.get("part"),
            "file": rel(glb) if glb.is_file() else item.get("file"),
            "glb_bytes": glb.stat().st_size if glb.is_file() else None,
            "inventory": rel(inv) if inv.is_file() else item.get("inventory"),
            "inventory_exists": inv.is_file(),
            "origin": rel(origin) if origin.is_file() else item.get("origin"),
            "origin_exists": origin.is_file(),
            "feature_count": item.get("feature_count"),
            "polygon_components": item.get("polygon_components"),
        })

    building_files = []
    for path in sorted(BUILDINGS.rglob("*")):
        if path.is_file() and path != OUT:
            building_files.append({"path": rel(path), "bytes": path.stat().st_size})

    checks = {
        "enrichment_index_records_match_report_total": len(records) == (enrichment_report.get("counts") or {}).get("total"),
        "parts_index_count_matches_parts_report": len(parts_index) == parts_report.get("source_feature_assignments"),
        "all_four_original_and_enhanced_parts_present": len(inventories) == 4,
        "all_six_permanent_parts_listed": len(six_parts) == 6 and all(p["glb_bytes"] for p in six_parts),
        "all_source_features_accounted_for_in_six_part_report": six_report.get("source_feature_count") == six_report.get("exported_source_feature_count"),
        "six_part_report_has_no_omitted_source_features": not six_report.get("omitted_source_features"),
        "all_original_inventory_properties_preserved_flag": six_report.get("all_source_tags_preserved_in_inventory") is True,
        "all_material_properties_preserved_flag": six_report.get("material_properties_preserved_in_inventory") is True,
        "duplicate_enrichment_identity_keys_found": bool(duplicates),
    }

    report = {
        "schema_version": "1.0.0",
        "status": "audit_completed_with_review_items" if duplicates or not all(checks.values()) else "audit_completed",
        "read_only": True,
        "purpose": "Full parsed audit of building sources, every enrichment-index record, all original four-part inventories, enhanced derivatives, and the separate six-part permanent GLB set.",
        "policy": "This audit reads source files and writes only this report. It does not modify source GeoJSON, CSV, GLBs, inventories, origin sidecars, or enrichment indexes.",
        "source_files": {
            rel(p): {"bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in (footprints_path, details_path, roofs_path, csv_path,
                      PARTS / "parts-inventory-index.json",
                      PARTS / "building-enrichment-index.json",
                      PARTS / "building-enrichment-report.json")
        },
        "source_counts": {
            "footprint_geojson_features": len(footprints.get("features", [])),
            "building_details_geojson_features": len(details.get("features", [])),
            "roof_details_geojson_features": len(roofs.get("features", [])),
            "building_details_csv_rows": len(csv_rows),
            "building_details_csv_rows_with_osm_id": len(csv_ids),
            "unique_osm_ids_in_csv": len(set(csv_ids)),
            "parts_inventory_index_entries": len(parts_index),
            "parts_report": {
                "source_feature_count": parts_report.get("source_polygon_feature_count_exported"),
                "polygon_components": parts_report.get("polygon_components_exported"),
                "part_count": parts_report.get("part_count"),
                "all_exported_polygon_features_assigned_once": parts_report.get("all_exported_polygon_features_assigned_once"),
            },
        },
        "full_enrichment_index": {
            "path": rel(PARTS / "building-enrichment-index.json"),
            "schema_version": enrichment.get("schema_version"),
            "records_parsed": len(records),
            "reported_counts": enrichment.get("counts"),
            "report_counts": enrichment_report.get("counts"),
            "records_by_part": dict(sorted(per_part.items())),
            "records_by_source_key": dict(sorted(source_key_counts.items())),
            "records_by_match_method": dict(sorted(match_counts.items())),
            "field_coverage": field_coverage,
            "duplicate_identity_keys": duplicates,
            "review_queue_count": len(enrichment_report.get("review_queue", [])),
            "matching_policy": enrichment.get("matching_policy"),
            "geometry_policy": enrichment.get("geometry_policy"),
        },
        "original_four_part_assets": inventories,
        "separate_six_part_assets": {
            "index": rel(BUILDINGS / "ermita-glb-parts" / "buildings_parts_index.json"),
            "report": rel(BUILDINGS / "ermita-glb-parts" / "buildings_parts_report.json"),
            "index_source_features": six_index.get("total_source_features"),
            "index_polygon_components": six_index.get("total_polygon_components"),
            "report_source_features": six_report.get("source_feature_count"),
            "report_exported_features": six_report.get("exported_source_feature_count"),
            "report_polygon_components": six_report.get("polygon_components_exported"),
            "omitted_source_features": six_report.get("omitted_source_features"),
            "parts": six_parts,
        },
        "enhanced_parts_report": enhancement_report,
        "checks": checks,
        "repository_building_data_file_inventory": {
            "file_count": len(building_files),
            "files": building_files,
        },
        "review_notes": [
            "A successful parse and consistent count do not establish visual accuracy of generated facade details.",
            "The enrichment index has unmatched and spatial-review records; preserve them and do not invent building identity or facade attributes.",
            "The four-part source GLBs and the separate six-part permanent GLB set are distinct assets and must not be substituted for one another.",
            "The report records file paths and sizes for all files under the buildings data folder; source hashes are recorded for key text data and inventories.",
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": rel(OUT),
        "status": report["status"],
        "source_counts": report["source_counts"],
        "full_enrichment_index": {
            "records_parsed": len(records),
            "reported_counts": enrichment.get("counts"),
            "records_by_match_method": dict(sorted(match_counts.items())),
            "review_queue_count": len(enrichment_report.get("review_queue", [])),
        },
        "checks": checks,
        "building_data_files": len(building_files),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
