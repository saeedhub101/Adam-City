#!/usr/bin/env python3
"""Build a read-only feature-level crosswalk for the Ermita master GeoJSON/CSV.

The master CSV is a union of heterogeneous source tables, not a one-row-per-building
register. This script preserves every GeoJSON feature and every CSV source row,
matches explicit identifiers first, and emits ambiguous/multiple matches for review.
It never edits source GeoJSON, source CSV, coordinates, or building geometry.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import ijson
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "complete_data/OSM/data/buildings/Ermita"
MASTER_CSV = DATA / "ermita-buildings-master.csv"
GEO_PARTS = [
    DATA / "ermita-buildings-master.parts/part-001.geojson",
    DATA / "ermita-buildings-master.parts/part-002.geojson",
]
OUT_CSV = ROOT / "complete_data/open free tile/ermita-master-feature-crosswalk.csv"
OUT_JSON = ROOT / "complete_data/open free tile/ermita-master-feature-crosswalk-report.json"

CSV_KEYS = (
    "osm_feature_id", "linked_osm_feature_id", "building_osm_id",
    "nearest_building_osm_id", "source_feature_id", "source_id",
    "feature_id", "source_element_id", "google_feature_id",
    "microsoft_feature_id", "record_id", "candidate_id", "store_osm_id",
)
FEATURE_KEYS = (
    "osm_feature_id", "source_feature_id", "source_id", "feature_id",
    "source_element_id", "google_feature_id", "microsoft_feature_id",
    "record_id", "candidate_id", "store_osm_id",
)
NAME_FIELDS = (
    "name", "official_name", "building_name", "source_name_or_brand",
    "candidate_name_for_review_only", "openfreemap_candidate_name",
    "mapped_name_or_use", "store_name", "nearest_building_name",
)
TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform


def text(value) -> str:
    return "" if value is None else str(value).strip()


def osm_id_from_properties(props: dict, feature: dict) -> str:
    value = text(props.get("osm_feature_id"))
    if value:
        return value
    value = text(props.get("osm_id"))
    kind = text(props.get("osm_type") or props.get("type"))
    if value and kind in {"way", "node", "relation"}:
        return f"{kind}/{value}"
    raw_id = text(feature.get("id"))
    if raw_id and kind in {"way", "node", "relation"}:
        return f"{kind}/{raw_id}"
    if raw_id.startswith(("way/", "node/", "relation/")):
        return raw_id
    return ""


def index_key(key: str, value: str) -> tuple[str, str] | None:
    value = text(value)
    if not value:
        return None
    return key, value


def read_csv_index(path: Path):
    index = defaultdict(list)
    row_count = 0
    source_counts = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            source = text(row.get("_source_file"))
            source_counts[source or "(source missing)"] += 1
            row["_master_csv_row_number"] = str(row_number)
            for key in CSV_KEYS:
                key_value = index_key(key, row.get(key, ""))
                if key_value:
                    index[key_value].append(row)
    return index, row_count, source_counts


def geometry_metrics(geometry_data: dict):
    if not geometry_data:
        return "", "", "", ""
    geom = shape(geometry_data)
    if geom.is_empty:
        return "", "", "", ""
    bounds = geom.bounds
    projected = bool(bounds) and (
        abs(bounds[0]) > 180 or abs(bounds[2]) > 180
        or abs(bounds[1]) > 90 or abs(bounds[3]) > 90
    )
    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty:
        return "", "", "", ""
    if projected:
        geom_m = geom
        centroid_ll = geom_transform(TO_4326, geom.centroid)
    else:
        geom_m = geom_transform(TO_3857, geom)
        centroid_ll = geom.centroid
    return (
        centroid_ll.x,
        centroid_ll.y,
        float(geom_m.area),
        "EPSG:3857" if projected else "EPSG:4326",
    )


def main():
    if not MASTER_CSV.is_file():
        raise FileNotFoundError(MASTER_CSV)
    missing = [p for p in GEO_PARTS if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing GeoJSON parts: " + ", ".join(map(str, missing)))

    csv_index, csv_rows, source_counts = read_csv_index(MASTER_CSV)
    output_rows = []
    report = {
        "schema_version": "1.0",
        "status": "completed",
        "master_csv": str(MASTER_CSV.relative_to(ROOT)),
        "master_csv_rows": csv_rows,
        "master_geojson_parts": [str(p.relative_to(ROOT)) for p in GEO_PARTS],
        "matching_policy": (
            "Explicit source identifiers first. OSM IDs are not inferred from proximity. "
            "All matched CSV rows and source names are preserved as candidate evidence; "
            "multiple source rows are not automatically collapsed or treated as conflicts."
        ),
        "geometry_policy": "Read-only. Source geometry, coordinates, IDs and heights are not modified.",
        "csv_source_row_counts": dict(sorted(source_counts.items())),
    }
    source_feature_counts = Counter()
    match_counts = Counter()
    geometry_counts = Counter()
    exact_osm_ids = set()
    features_per_osm_id = Counter()
    total = 0

    for part_path in GEO_PARTS:
        with part_path.open("rb") as stream:
            for feature_index, feature in enumerate(ijson.items(stream, "features.item"), start=1):
                if not isinstance(feature, dict):
                    continue
                total += 1
                props = feature.get("properties") or {}
                source_file = text(props.get("_source_file")) or str(part_path.relative_to(ROOT))
                source_feature_counts[source_file] += 1
                geometry_type = text((feature.get("geometry") or {}).get("type"))
                geometry_counts[geometry_type or "(missing)"] += 1
                osm_id = osm_id_from_properties(props, feature)
                if osm_id:
                    exact_osm_ids.add(osm_id)
                    features_per_osm_id[osm_id] += 1

                feature_key_values = []
                for key in FEATURE_KEYS:
                    value = text(props.get(key))
                    if value:
                        feature_key_values.append((key, value))
                if osm_id:
                    feature_key_values.append(("osm_feature_id", osm_id))

                matched_by_key = defaultdict(list)
                seen_row_numbers = set()
                for key, value in feature_key_values:
                    for csv_row in csv_index.get((key, value), []):
                        row_number = csv_row["_master_csv_row_number"]
                        if row_number not in seen_row_numbers:
                            matched_by_key[key].append(csv_row)
                            seen_row_numbers.add(row_number)

                matched_rows = [row for rows in matched_by_key.values() for row in rows]
                # Deduplicate a CSV row that matched through more than one explicit key.
                deduped = {}
                for row in matched_rows:
                    deduped[row["_master_csv_row_number"]] = row
                matched_rows = list(deduped.values())
                osm_matches = matched_by_key.get("osm_feature_id", [])
                non_osm_match_keys = sorted(
                    key for key, rows in matched_by_key.items()
                    if key != "osm_feature_id" and rows
                )
                if osm_matches:
                    status = "exact_osm_id_single_csv_row" if len(osm_matches) == 1 else "exact_osm_id_multiple_csv_rows"
                elif matched_rows:
                    status = "exact_non_osm_source_key"
                else:
                    status = "no_exact_identifier_match"
                match_counts[status] += 1

                try:
                    lon, lat, area_m2, detected_crs = geometry_metrics(feature.get("geometry"))
                except Exception:
                    lon, lat, area_m2, detected_crs = "", "", "", "geometry_error"
                if isinstance(lon, (float, int)) and isinstance(lat, (float, int)):
                    sector = f"L{math.floor(lon * 1000)}_B{math.floor(lat * 1000)}"
                    lon_out, lat_out = f"{lon:.8f}", f"{lat:.8f}"
                else:
                    sector, lon_out, lat_out = "", "", ""

                names = []
                matched_sources = set()
                matched_rows_numbers = []
                for row in matched_rows:
                    matched_rows_numbers.append(row["_master_csv_row_number"])
                    if text(row.get("_source_file")):
                        matched_sources.add(text(row["_source_file"]))
                    for name_field in NAME_FIELDS:
                        value = text(row.get(name_field))
                        if value and value not in names:
                            names.append(value)
                output_rows.append({
                    "geographic_sector": sector,
                    "centroid_latitude": lat_out,
                    "centroid_longitude": lon_out,
                    "source_geojson_part": str(part_path.relative_to(ROOT)),
                    "source_feature_index_in_part": feature_index,
                    "source_file": source_file,
                    "source_sha256": text(props.get("_source_sha256")),
                    "source_feature_id": next((text(props.get(k)) for k in ("source_feature_id", "source_id", "feature_id", "id") if text(props.get(k))), ""),
                    "osm_feature_id": osm_id,
                    "geometry_type": geometry_type,
                    "geometry_crs_detected": detected_crs,
                    "geometry_area_m2": f"{area_m2:.3f}" if isinstance(area_m2, (float, int)) else "",
                    "exact_match_status": status,
                    "exact_osm_id_csv_rows": len(osm_matches),
                    "all_exact_csv_rows": len(matched_rows),
                    "matched_key_types": ";".join(sorted(matched_by_key)),
                    "matched_csv_source_files": ";".join(sorted(matched_sources)),
                    "matched_csv_row_numbers": ";".join(sorted(matched_rows_numbers, key=int)),
                    "matched_name_candidates": ";".join(names),
                    "review_note": (
                        "Multiple CSV source rows; retain provenance and resolve source differences."
                        if status == "exact_osm_id_multiple_csv_rows"
                        else "No exact source key; keep unmatched until a geometry crosswalk is reviewed."
                        if status == "no_exact_identifier_match"
                        else "Exact identifier evidence only; this is not a photo-verified real-building record."
                    ),
                })

    output_rows.sort(key=lambda r: (
        r["geographic_sector"], r["centroid_latitude"], r["centroid_longitude"],
        r["source_file"], r["source_feature_index_in_part"]
    ))
    sector_order = Counter()
    for row in output_rows:
        sector_order[row["geographic_sector"]] += 1
        row["geographic_order_in_sector"] = sector_order[row["geographic_sector"]]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output_rows[0]) if output_rows else []
    with OUT_CSV.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    report.update({
        "geojson_feature_count": total,
        "geojson_source_feature_counts": dict(sorted(source_feature_counts.items())),
        "geometry_type_counts": dict(geometry_counts),
        "exact_match_status_counts": dict(match_counts),
        "distinct_osm_ids_in_geojson_properties": len(exact_osm_ids),
        "osm_ids_represented_by_multiple_geojson_features": sum(1 for n in features_per_osm_id.values() if n > 1),
        "geographic_sector_count": len({row["geographic_sector"] for row in output_rows if row["geographic_sector"]}),
        "output_csv": str(OUT_CSV.relative_to(ROOT)),
        "output_rows": len(output_rows),
        "limitations": [
            "A source feature is not automatically a unique physical building.",
            "An exact OSM ID can legitimately occur in multiple source datasets or geometry components.",
            "Rows without exact identifiers need a separate geometry-overlap review; proximity alone does not authorize copying semantic attributes.",
            "This crosswalk does not decide completeness or assign photo textures. Those are later stages after source identity is resolved.",
        ],
    })
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "features": total,
        "source_csv_rows": csv_rows,
        "match_counts": dict(match_counts),
        "sectors": report["geographic_sector_count"],
        "output_csv": str(OUT_CSV.relative_to(ROOT)),
        "output_report": str(OUT_JSON.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
