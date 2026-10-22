#!/usr/bin/env python3
"""Join Button 4 building-part inventories to OSM building records (metadata-only; no GLB regeneration).

Exact OSM IDs are preferred. For unmatched polygon footprints, spatial matching
is attempted against OSM building polygons. Geometry is never changed. A spatial
match is accepted automatically only when the candidate is unambiguous and
passes containment/area checks; uncertain candidates are recorded for review.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform as geom_transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[3]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings"
PARTS = BUILDINGS / "parts"
PARTS_INDEX = PARTS / "parts-inventory-index.json"
DETAILS_GEOJSON = BUILDINGS / "ermita-building-details.geojson"
ROOF_GEOJSON = BUILDINGS / "ermita-building-roof-details.geojson"
FOOTPRINTS_GEOJSON = BUILDINGS / "ermita-building-footprints.geojson"
DETAILS_CSV = BUILDINGS / "osm-building-details.csv"
OUTPUT = PARTS / "building-enrichment-index.json"
REPORT = PARTS / "building-enrichment-report.json"
WEB_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform


def read_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def first(tags: dict, *keys):
    for key in keys:
        value = tags.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def feature_id(props):
    if props.get("osm_feature_id"):
        return str(props["osm_feature_id"])
    if props.get("type") and props.get("id") is not None:
        return f'{props["type"]}/{props["id"]}'
    return None


def main():
    source_index = read_json(PARTS_INDEX)
    detail_sources = [DETAILS_GEOJSON, ROOF_GEOJSON]
    footprints_source = read_json(FOOTPRINTS_GEOJSON)
    footprint_geometries = {}
    for source_index, feature in enumerate(footprints_source.get("features", [])):
        geom_data = feature.get("geometry")
        if not geom_data:
            continue
        try:
            footprint_geometries[source_index] = geom_transform(WEB_MERCATOR, shape(geom_data))
        except Exception:
            continue
    by_osm_id = {}
    polygon_candidates = []
    seen_polygon_geometries = set()

    for source_path in detail_sources:
        source = read_json(source_path)
        for feature in source.get("features", []):
            props = feature.get("properties") or {}
            oid = feature_id(props)
            tags = props.get("tags") if isinstance(props.get("tags"), dict) else {}
            entry = by_osm_id.setdefault(oid, {"tags": {}, "source_files": []}) if oid else None
            if entry is not None:
                entry["tags"].update({k: v for k, v in tags.items() if v not in (None, "")})
                entry["source_files"].append(str(source_path.relative_to(ROOT)))
            geom_data = feature.get("geometry")
            if not geom_data:
                continue
            try:
                geom = geom_transform(WEB_MERCATOR, shape(geom_data))
            except Exception:
                continue
            if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon") or geom.area <= 0:
                continue
            polygon_key = (oid, geom.wkb)
            if polygon_key in seen_polygon_geometries:
                continue
            seen_polygon_geometries.add(polygon_key)
            polygon_candidates.append({
                "osm_id": oid,
                "tags": tags,
                "geom": geom,
                "area": float(geom.area),
                "centroid": geom.centroid,
                "source": str(source_path.relative_to(ROOT)),
                "name": tags.get("name"),
            })

    # CSV supplements the exact-ID tag map only; POIs are not spatially assigned
    # to buildings because proximity alone does not prove building identity.
    with DETAILS_CSV.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            oid = row.get("osm_feature_id")
            if not oid:
                continue
            try:
                tags = json.loads(row.get("tags_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                tags = {}
            entry = by_osm_id.setdefault(oid, {"tags": {}, "source_files": []})
            entry["tags"].update({k: v for k, v in tags.items() if v not in (None, "")})
            entry["source_files"].append(str(DETAILS_CSV.relative_to(ROOT)))

    polygon_tree = STRtree([candidate["geom"] for candidate in polygon_candidates]) if polygon_candidates else None

    inventory_by_key = {}
    for part in range(1, 5):
        path = PARTS / f"part{part}" / f"part{part}-inventory.json"
        if not path.is_file():
            raise FileNotFoundError(f"Required inventory is missing: {path}")
        for feature in read_json(path).get("features", []):
            key = f'{part}:{feature.get("source_key")}:{feature.get("source_feature_index")}'
            inventory_by_key[key] = feature

    records = []
    match_counts = {"exact_osm_id": 0, "spatial_high_confidence": 0, "spatial_geometry_high_confidence": 0, "spatial_review": 0, "unmatched": 0}
    for item in source_index:
        key = f'{item.get("part")}:{item.get("source_key")}:{item.get("source_feature_index")}'
        inventory = inventory_by_key.get(key)
        if inventory is None:
            raise ValueError(f"Inventory entry missing for index key {key}")
        oid = item.get("source_feature_id")
        props = inventory.get("source_properties") or {}
        source_tags = inventory.get("source_tags") or props.get("tags") or {}
        matched_id = oid if oid in by_osm_id else None
        match_method = "exact_osm_id" if matched_id else "unmatched"
        confidence = 1.0 if matched_id else 0.0
        spatial_evidence = None

        centroid_data = inventory.get("centroid_epsg3857_m")
        if not matched_id and isinstance(centroid_data, dict) and "x" in centroid_data and "y" in centroid_data:
            point = Point(float(centroid_data["x"]), float(centroid_data["y"]))
            source_area = float(inventory.get("area_m2") or 0)
            candidate_indices = polygon_tree.query(point) if polygon_tree is not None else []
            containing = [polygon_candidates[int(i)] for i in candidate_indices if polygon_candidates[int(i)]["geom"].covers(point)]
            # If the centroid falls in multiple nested polygons, rank by area
            # similarity, then distance to centroid; never spatially attach a POI.
            ranked = []
            for candidate in containing:
                ratio = (candidate["area"] / source_area) if source_area > 0 else None
                area_penalty = abs(math.log(max(ratio, 1e-9))) if ratio is not None else 99
                distance = float(point.distance(candidate["centroid"]))
                ranked.append((area_penalty, distance, candidate))
            ranked.sort(key=lambda item: (item[0], item[1]))
            if ranked:
                best_penalty, distance, best = ranked[0]
                second = ranked[1] if len(ranked) > 1 else None
                clearly_best = second is None or (second[0] - best_penalty >= 0.35) or (second[1] - distance >= 8.0)
                area_ok = source_area <= 0 or 0.2 <= best["area"] / source_area <= 5.0
                if clearly_best and area_ok and best["osm_id"]:
                    matched_id = best["osm_id"]
                    match_method = "spatial_high_confidence"
                    confidence = 0.9 if len(ranked) == 1 else 0.82
                else:
                    match_method = "spatial_review"
                    confidence = 0.5
                spatial_evidence = {
                    "candidate_osm_id": best["osm_id"],
                    "candidate_name": best["name"],
                    "candidate_source": best["source"],
                    "candidate_count_containing_centroid": len(ranked),
                    "centroid_to_candidate_centroid_m": round(distance, 3),
                    "source_area_m2": round(source_area, 3) if source_area else None,
                    "candidate_area_m2": round(best["area"], 3),
                    "candidate_to_source_area_ratio": round(best["area"] / source_area, 4) if source_area else None,
                    "area_log_error": round(best_penalty, 4),
                    "accepted": match_method == "spatial_high_confidence",
                }

        # Second pass: compare the actual source footprint polygon with OSM
        # building polygons. This can resolve centroid misses while refusing
        # large compounds or overlapping alternatives that remain ambiguous.
        if not matched_id and item.get("source_key") == "footprints":
            source_geom = footprint_geometries.get(int(item.get("source_feature_index", -1)))
            if source_geom is not None and not source_geom.is_empty and source_geom.area > 0 and polygon_tree is not None:
                candidate_indices = polygon_tree.query(source_geom)
                geom_ranked = []
                for candidate_index in candidate_indices:
                    candidate = polygon_candidates[int(candidate_index)]
                    if not candidate["osm_id"]:
                        continue
                    try:
                        intersection_area = float(source_geom.intersection(candidate["geom"]).area)
                    except Exception:
                        continue
                    if intersection_area <= 0:
                        continue
                    smaller_area = min(float(source_geom.area), float(candidate["area"]))
                    overlap_smaller = intersection_area / smaller_area if smaller_area else 0.0
                    union_area = float(source_geom.area) + float(candidate["area"]) - intersection_area
                    iou = intersection_area / union_area if union_area else 0.0
                    ratio = float(candidate["area"]) / float(source_geom.area)
                    if overlap_smaller >= 0.75 and 0.2 <= ratio <= 5.0:
                        geom_ranked.append({
                            "candidate": candidate,
                            "intersection_area_m2": intersection_area,
                            "overlap_smaller": overlap_smaller,
                            "intersection_over_union": iou,
                            "area_ratio": ratio,
                        })
                geom_ranked.sort(key=lambda item: (item["overlap_smaller"], item["intersection_over_union"]), reverse=True)
                if geom_ranked:
                    best = geom_ranked[0]
                    second = geom_ranked[1] if len(geom_ranked) > 1 else None
                    clear_best = second is None or (
                        best["overlap_smaller"] - second["overlap_smaller"] >= 0.15
                        or best["intersection_over_union"] - second["intersection_over_union"] >= 0.15
                    )
                    spatial_evidence = {
                        "candidate_osm_id": best["candidate"]["osm_id"],
                        "candidate_name": best["candidate"]["name"],
                        "candidate_source": best["candidate"]["source"],
                        "candidate_count_passing_overlap_threshold": len(geom_ranked),
                        "intersection_area_m2": round(best["intersection_area_m2"], 3),
                        "overlap_fraction_of_smaller_polygon": round(best["overlap_smaller"], 4),
                        "intersection_over_union": round(best["intersection_over_union"], 4),
                        "candidate_to_source_area_ratio": round(best["area_ratio"], 4),
                        "accepted": bool(clear_best),
                        "method": "source-footprint polygon overlap",
                    }
                    if clear_best:
                        matched_id = best["candidate"]["osm_id"]
                        match_method = "spatial_geometry_high_confidence"
                        confidence = min(0.98, 0.85 + 0.13 * best["intersection_over_union"])
                    else:
                        match_method = "spatial_review"
                        confidence = 0.5

        linked = by_osm_id.get(matched_id) if matched_id else None
        tags = dict(source_tags)
        if linked:
            # Prefer OSM semantic tags, retaining source geometry/render tags as
            # fallback only when the linked OSM record lacks that field.
            tags = {**source_tags, **linked["tags"]}
        if match_method in match_counts:
            match_counts[match_method] += 1

        def pick(*keys):
            return first(tags, *keys)

        record = {
            "part": item.get("part"),
            "source_key": item.get("source_key"),
            "source_path": item.get("source_path"),
            "source_feature_index": item.get("source_feature_index"),
            "source_feature_id": oid,
            "linked_osm_feature_id": matched_id,
            "match_method": match_method,
            "match_confidence": confidence,
            "spatial_match_evidence": spatial_evidence,
            "polygon_components_exported": item.get("polygon_components_exported"),
            "name": pick("name", "official_name", "short_name"),
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
            "osm_tags": linked["tags"] if linked else tags,
            "source_evidence": {
                "linked_osm_sources": linked["source_files"] if linked else [],
                "source_inventory_available": True,
                "basemap_feature_id": props.get("basemap_source_feature_id"),
            },
            "source_inventory_properties": props,
            "enrichment_note": (
                "Exact OSM ID match." if match_method == "exact_osm_id" else
                "Spatial match accepted by centroid containment and ambiguity/area checks; verify before treating the identity as authoritative."
                if match_method == "spatial_high_confidence" else
                "Spatial candidate recorded for manual review; semantic attributes are not attached."
                if match_method == "spatial_review" else
                "No supported exact or spatial match; attributes remain from the source inventory only."
            ),
        }
        if match_method == "spatial_review":
            # Prevent a review candidate from silently enriching semantic fields.
            record["linked_osm_feature_id"] = None
            record["name"] = None
            record["official_name"] = None
            record["brand"] = None
            record["address"] = {k: None for k in record["address"]}
            record["use"] = {k: None for k in record["use"]}
            record["osm_tags"] = source_tags
            record["building"] = {
                "type": first(source_tags, "building"),
                "levels": first(source_tags, "building:levels"),
                "height": first(source_tags, "height"),
                "min_height": first(source_tags, "min_height"),
                "colour": first(source_tags, "building:colour", "colour"),
                "material": first(source_tags, "building:material", "material"),
                "roof_shape": first(source_tags, "roof:shape"),
                "roof_material": first(source_tags, "roof:material"),
                "roof_colour": first(source_tags, "roof:colour"),
            }
        records.append(record)

    counts = {
        "total": len(records),
        **match_counts,
        "named": sum(bool(r["name"]) for r in records),
        "addressed": sum(any(r["address"].values()) for r in records),
        "with_source_material_tag": sum(any(r["building"][k] for k in ("material", "roof_material", "colour", "roof_colour")) for r in records),
        "linked_total": match_counts["exact_osm_id"] + match_counts["spatial_high_confidence"] + match_counts["spatial_geometry_high_confidence"],
    }
    data = {
        "schema_version": "2.0.0",
        "generated_from": {
            "parts_inventory_index": str(PARTS_INDEX.relative_to(ROOT)),
            "footprints_geojson": str(FOOTPRINTS_GEOJSON.relative_to(ROOT)),
            "details_geojson": str(DETAILS_GEOJSON.relative_to(ROOT)),
            "roof_details_geojson": str(ROOF_GEOJSON.relative_to(ROOT)),
            "details_csv": str(DETAILS_CSV.relative_to(ROOT)),
            "parts_inventory": [f"complete_data/OSM/data/buildings/parts/part{i}/part{i}-inventory.json" for i in range(1, 5)],
        },
        "geometry_policy": "Metadata-only join. No GLB, GeoJSON geometry, feature IDs, centroids, coordinates, heights, or colors are changed.",
        "matching_policy": "Exact OSM ID first, then polygon-centroid containment with area and ambiguity checks. Ambiguous matches are listed for review and do not receive semantic tags. Nearby POIs are never attached by proximity alone.",
        "counts": counts,
        "buildings": records,
    }
    report = {
        "schema_version": "2.0.0",
        "status": "generated",
        "created_from": data["generated_from"],
        "geometry_policy": data["geometry_policy"],
        "matching_policy": data["matching_policy"],
        "counts": counts,
        "review_queue": [
            {
                "part": r["part"],
                "source_key": r["source_key"],
                "source_feature_index": r["source_feature_index"],
                "source_feature_id": r["source_feature_id"],
                "spatial_match_evidence": r["spatial_match_evidence"],
            } for r in records if r["match_method"] == "spatial_review"
        ],
        "limitations": [
            "Names, addresses, and material tags are present only when supported by source data.",
            "A spatial match is a candidate identity, not proof that all attributes or facade appearance are correct.",
            "Geometry-overlap matches require strong overlap with one clearly preferred OSM polygon; competing matches remain in the review queue.",
            "This index contains no verified facade photographs or photo-derived materials.",
            "Ambiguous matches remain in the review queue and do not receive candidate semantic tags.",
        ],
        "index_path": str(OUTPUT.relative_to(ROOT)),
    }
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"index": str(OUTPUT), "report": str(REPORT), "counts": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
