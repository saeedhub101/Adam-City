#!/usr/bin/env python3
"""Read-only audit of the current Ermita building-data layout.

The canonical four-part data now lives under complete_data/OSM/data/buildings/Ermita.
This audit validates those committed sources and reports their integrity without
requiring removed legacy directories or regenerating any GLB geometry.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings"
ERM = BUILDINGS / "Ermita"
OUT = ERM / "building-data-full-audit.json"


def read_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main():
    required = [
        ERM / "ermita-building-details.geojson",
        ERM / "osm-building-details.csv",
        ERM / "ermita-building-parts-index.json",
        ERM / "parts-report.json",
        ERM / "building-enrichment-index.json",
        ERM / "building-enrichment-report.json",
    ]
    for part in range(1, 5):
        required.extend([
            ERM / f"Parts{part}.glb",
            ERM / f"part{part}" / f"part{part}-inventory.json",
            ERM / f"part{part}" / f"part{part}-origin.json",
        ])
    required.extend([
        BUILDINGS / "windows" / "ermita-buildings-facade-details.glb",
        BUILDINGS / "windows" / "facade-details-report.json",
        BUILDINGS / "windows" / "facade-signage-index.csv",
    ])
    missing = [rel(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise FileNotFoundError("Required current building assets are missing or empty: " + ", ".join(missing))

    footprint_data = read_json(ROOT / "ermita/maps/generated/ermita-building-footprints.geojson")
    detail_data = read_json(ERM / "ermita-building-details.geojson")
    roof_data = {"features": []}
    parts_index = read_json(ERM / "ermita-building-parts-index.json")
    parts_report = read_json(ERM / "parts-report.json")
    enrichment = read_json(ERM / "building-enrichment-index.json")
    enrichment_report = read_json(ERM / "building-enrichment-report.json")
    windows_report = read_json(BUILDINGS / "windows" / "facade-details-report.json")
    records = enrichment.get("buildings", [])
    counts = enrichment.get("counts", {})
    index_count = len(parts_index) if isinstance(parts_index, list) else len(parts_index.get("entries", []))
    part_assets = []
    for part in range(1, 5):
        glb = ERM / f"Parts{part}.glb"
        inventory_path = ERM / f"part{part}" / f"part{part}-inventory.json"
        origin_path = ERM / f"part{part}" / f"part{part}-origin.json"
        inventory = read_json(inventory_path)
        part_assets.append({
            "part": part,
            "glb": rel(glb),
            "glb_bytes": glb.stat().st_size,
            "inventory": rel(inventory_path),
            "inventory_features": len(inventory.get("features", [])),
            "origin": rel(origin_path),
            "inventory_sha256": sha256(inventory_path),
        })

    report = {
        "schema_version": "2.0.0",
        "status": "audit_completed",
        "read_only": True,
        "canonical_layout": rel(ERM),
        "legacy_paths_required": False,
        "source_counts": {
            "footprints": len(footprint_data.get("features", [])),
            "building_details": len(detail_data.get("features", [])),
            "roof_details": len(roof_data.get("features", [])),
            "parts_index_entries": index_count,
            "parts_report_part_count": parts_report.get("part_count"),
        },
        "full_enrichment_index": {
            "path": rel(ERM / "building-enrichment-index.json"),
            "records_parsed": len(records),
            "reported_total": counts.get("total"),
            "report_total": (enrichment_report.get("counts") or {}).get("total"),
            "records_by_match_method": {
                method: sum(1 for record in records if record.get("match_method") == method)
                for method in sorted({str(record.get("match_method", "missing")) for record in records})
            },
        },
        "original_four_part_assets": part_assets,
        "windows_facade_asset": {
            "glb": rel(BUILDINGS / "windows" / "ermita-buildings-facade-details.glb"),
            "glb_bytes": (BUILDINGS / "windows" / "ermita-buildings-facade-details.glb").stat().st_size,
            "report": windows_report,
        },
        "checks": {
            "enrichment_index_matches_report": len(records) == counts.get("total") == (enrichment_report.get("counts") or {}).get("total"),
            "all_four_glbs_and_sidecars_present": len(part_assets) == 4,
            "all_required_current_assets_nonempty": not missing,
        },
        "source_hashes": {rel(path): sha256(path) for path in required if path.suffix in (".json", ".csv")},
        "notes": [
            "The audit reads the canonical four-part GLBs and metadata. Removed preview-only OSM footprint/roof layers are not required.",
            "The four PartsN.glb assets are distinct from the procedural windows facade overlay.",
            "This structural audit does not claim that building facade appearance has been visually verified.",
        ],
    }
    report["status"] = "audit_completed" if all(report["checks"].values()) else "audit_completed_with_review_items"
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": rel(OUT),
        "status": report["status"],
        "source_counts": report["source_counts"],
        "enrichment_records": len(records),
        "checks": report["checks"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
