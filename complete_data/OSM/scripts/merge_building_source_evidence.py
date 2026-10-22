#!/usr/bin/env python3
"""Merge OpenFreeMap fallback, house numbers, facade metadata and image evidence into the existing building index.

Metadata-only: never changes GLBs, geometry, coordinates, heights, source IDs or materials.
Spatial links are accepted only when geometry evidence is unambiguous; all other candidates are recorded for review.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform as geom_transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[3]
PARTS = ROOT / "complete_data/OSM/data/buildings/parts"
BUILDINGS = ROOT / "complete_data/OSM/data/buildings"
OPENFREE = ROOT / "complete_data/open free tile"
INDEX = PARTS / "building-enrichment-index.json"
REPORT = PARTS / "building-source-merge-report.json"
AUDIT = PARTS / "building-source-link-audit.csv"
FALLBACK = OPENFREE / "building-fallback.geojson"
HOUSENUMBERS = OPENFREE / "layers/housenumber.geojsonl"
IMAGE_LINKS = PARTS / "building-image-links.json"
IMAGE_CANDIDATES = PARTS / "building-image-candidates.json"
SIGNAGE_CSV = BUILDINGS / "windows/facade-signage-index.csv"
FACADE_REPORT = BUILDINGS / "windows/facade-details-report.json"
COMMERCIAL_REPORT = ROOT / "complete_data/OSM/Markets/commercial-facades-report.json"
SUPREME_REPORT = ROOT / "complete_data/OSM/Buildings/supreme-court-main-facade-report.json"
ROBINSONS_PHOTOS = ROOT / "complete_data/OSM/Markets/reference_photos/robinsons-manila/reference-index.json"
TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def feature_id(props: dict) -> str | None:
    for key in ("osm_feature_id", "osm_id", "feature_id", "source_feature_id", "id"):
        value = props.get(key)
        if value is None or str(value).strip() == "":
            continue
        text = str(value).strip()
        if "/" in text and text.split("/", 1)[0] in ("way", "node", "relation"):
            return text
        if key == "id" and props.get("type") in ("way", "node", "relation"):
            return f'{props["type"]}/{text}'
        if key == "osm_id":
            typ = props.get("osm_type") or props.get("type")
            if typ in ("way", "node", "relation"):
                return f"{typ}/{text}"
    typ, oid = props.get("osm_type") or props.get("type"), props.get("osm_id") or props.get("id")
    if typ in ("way", "node", "relation") and oid is not None:
        return f"{typ}/{oid}"
    return None


def flatten_tags(props: dict) -> dict:
    tags = props.get("tags")
    result = dict(tags) if isinstance(tags, dict) else {}
    for key, value in props.items():
        if key in ("tags", "geometry", "type", "_source") or value is None:
            continue
        if isinstance(value, (str, int, float, bool)) and str(value).strip():
            result.setdefault(key, value)
    return result


def first(tags: dict, *keys):
    for key in keys:
        value = tags.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def osm_aliases(value) -> set[str]:
    if value is None:
        return set()
    text = str(value).strip()
    out = {text} if text else set()
    if text.isdigit():
        out.update((f"way/{text}", f"node/{text}", f"relation/{text}"))
    return out


def read_features(path: Path) -> list[dict]:
    data = read_json(path, {})
    return data.get("features", []) if isinstance(data, dict) else []


def load_fallback():
    if not FALLBACK.exists():
        raise FileNotFoundError(f"Required OpenFreeMap fallback is missing: {FALLBACK}")
    rows, exact = [], defaultdict(list)
    for feature in read_features(FALLBACK):
        props = feature.get("properties") or {}
        geom_data = feature.get("geometry")
        if not geom_data:
            continue
        try:
            geom = geom_transform(TO_3857, shape(geom_data))
        except Exception:
            continue
        if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon") or geom.area <= 0:
            continue
        tags = flatten_tags(props)
        oid = feature_id(props)
        row = {
            "id": oid, "props": props, "tags": tags, "geom": geom,
            "area": float(geom.area), "centroid": geom.centroid,
            "name": first(tags, "name", "official_name", "name:en"),
        }
        rows.append(row)
        for alias in osm_aliases(oid):
            exact[alias].append(row)
    tree = STRtree([row["geom"] for row in rows]) if rows else None
    return rows, exact, tree


def query_rows(tree, geometries, query_geom):
    if tree is None:
        return []
    result = tree.query(query_geom)
    rows = []
    for item in result:
        if isinstance(item, int) or hasattr(item, "item"):
            rows.append(geometries[int(item)])
        else:
            # Shapely 1.x returns geometry objects.
            for row in geometries:
                if row["geom"].equals(item):
                    rows.append(row)
                    break
    return rows


def make_openfreemap_fields(tags: dict) -> dict:
    return {
        "name": first(tags, "name", "official_name", "name:en"),
        "official_name": first(tags, "official_name"),
        "brand": first(tags, "brand"),
        "housenumber": first(tags, "housenumber", "house_number", "addr:housenumber"),
        "street": first(tags, "street", "addr:street"),
        "building_type": first(tags, "building", "class", "subclass"),
        "levels": first(tags, "building:levels", "render_height", "height"),
        "height": first(tags, "height", "render_height"),
        "min_height": first(tags, "min_height", "render_min_height"),
        "material": first(tags, "building:material", "material"),
        "colour": first(tags, "building:colour", "colour"),
        "roof_shape": first(tags, "roof:shape"),
        "roof_material": first(tags, "roof:material"),
        "roof_colour": first(tags, "roof:colour"),
        "use": first(tags, "amenity", "shop", "office", "tourism", "historic"),
    }


def choose_spatial_candidate(source_point, source_area, candidates):
    ranked = []
    for candidate in candidates:
        geom = candidate["geom"]
        if not geom.covers(source_point):
            continue
        ratio = candidate["area"] / source_area if source_area > 0 else 1.0
        penalty = abs(math.log(max(ratio, 1e-9)))
        distance = float(source_point.distance(candidate["centroid"]))
        ranked.append((penalty, distance, candidate, ratio))
    ranked.sort(key=lambda x: (x[0], x[1]))
    if not ranked:
        return None, None, "no-containing-polygon"
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    area_ok = 0.2 <= best[3] <= 5.0
    clearly_best = second is None or (second[0] - best[0] >= 0.35) or (second[1] - best[1] >= 8.0)
    evidence = {
        "candidate_osm_id": best[2]["id"],
        "candidate_name": best[2]["name"],
        "candidate_area_ratio": round(best[3], 4),
        "centroid_distance_m": round(best[1], 3),
        "candidate_count": len(ranked),
        "accepted": bool(area_ok and clearly_best and best[2]["id"]),
        "method": "OpenFreeMap fallback polygon containment and area similarity",
    }
    return (best[2] if evidence["accepted"] else None), evidence, ("accepted" if evidence["accepted"] else "ambiguous-or-area-mismatch")


def load_source_geometries():
    # Build target geometry lookup for safe address-number matching.
    sources = {}
    for key, path in (
        ("footprints", BUILDINGS / "ermita-building-footprints.geojson"),
        ("roof_details", BUILDINGS / "ermita-building-roof-details.geojson"),
    ):
        for i, feature in enumerate(read_features(path)):
            geom_data = feature.get("geometry")
            if not geom_data:
                continue
            try:
                geom = geom_transform(TO_3857, shape(geom_data))
            except Exception:
                continue
            if geom.is_empty or geom.area <= 0:
                continue
            sources[(key, i)] = geom
    return sources


def load_housenumbers():
    rows = []
    if not HOUSENUMBERS.exists():
        return rows
    with HOUSENUMBERS.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                feature = json.loads(line)
                geom_data = feature.get("geometry")
                props = feature.get("properties") or {}
                number = first(props, "housenumber", "house_number", "addr:housenumber", "housenumber_label", "name")
                if not number or not geom_data:
                    continue
                geom = geom_transform(TO_3857, shape(geom_data))
                if geom.is_empty:
                    continue
                rows.append({"number": str(number), "props": props, "geom": geom, "line": line_no})
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    return rows


def attach_housenumbers(records, source_geometries):
    counts = Counter()
    candidates = []
    for i, record in enumerate(records):
        if record.get("source_key") != "footprints":
            continue
        geom = source_geometries.get(("footprints", int(record.get("source_feature_index", -1))))
        if geom is not None:
            candidates.append((i, geom))
    for house in load_housenumbers():
        point = house["geom"] if house["geom"].geom_type == "Point" else house["geom"].representative_point()
        matches = [(i, geom) for i, geom in candidates if geom.covers(point) or geom.distance(point) <= 2.5]
        if len(matches) != 1:
            counts["unlinked_or_ambiguous"] += 1
            continue
        i, _ = matches[0]
        record = records[i]
        record.setdefault("openfreemap_house_numbers", [])
        item = {"value": house["number"], "source": "complete_data/open free tile/layers/housenumber.geojsonl", "source_properties": house["props"]}
        if item not in record["openfreemap_house_numbers"]:
            record["openfreemap_house_numbers"].append(item)
        if not record.get("address", {}).get("housenumber"):
            unique_values = sorted({x["value"] for x in record["openfreemap_house_numbers"]})
            if len(unique_values) == 1:
                record.setdefault("address", {})["housenumber"] = unique_values[0]
                record["address"].setdefault("housenumber_source", "OpenFreeMap housenumber point matched to exactly one footprint")
        counts["linked"] += 1
    return counts


def load_image_metadata():
    links = read_json(IMAGE_LINKS, {"records": []}).get("records", [])
    candidates = read_json(IMAGE_CANDIDATES, [])
    if isinstance(candidates, dict):
        candidates = candidates.get("candidates", candidates.get("records", []))
    if not isinstance(candidates, list):
        candidates = []
    signage = []
    if SIGNAGE_CSV.exists():
        with SIGNAGE_CSV.open(encoding="utf-8-sig", newline="") as stream:
            signage = list(csv.DictReader(stream))
    commercial = read_json(COMMERCIAL_REPORT, {})
    supreme = read_json(SUPREME_REPORT, {})
    robinsons = read_json(ROBINSONS_PHOTOS, {})
    facade = read_json(FACADE_REPORT, {})
    return links, candidates, signage, commercial, supreme, robinsons, facade


def attach_images_and_facades(records, metadata):
    links, candidates, signage, commercial, supreme, robinsons, facade = metadata
    by_osm = defaultdict(list)
    for record in records:
        for value in (record.get("source_feature_id"), record.get("linked_osm_feature_id")):
            for alias in osm_aliases(value):
                by_osm[alias].append(record)
    counts = Counter()
    # Evidence-backed identity records only attach by exact OSM ID; pending candidates remain clearly marked.
    for link in links:
        ident = link.get("identity") or {}
        oid = f'{ident.get("osm_type")}/{ident.get("osm_id")}' if ident.get("osm_type") and ident.get("osm_id") is not None else None
        targets = by_osm.get(oid, []) if oid else []
        for record in targets:
            record.setdefault("image_evidence", []).append({
                "evidence_type": "named-building-source-image",
                "building_name": link.get("building_name"),
                "identity_status": "exact-osm-id",
                "images": link.get("image_evidence", []),
                "target_link": link.get("adam_city_target"),
                "applied_to_model": bool(link.get("applied_to_model", False)),
                "source_manifest": "complete_data/OSM/data/buildings/parts/building-image-links.json",
            })
            counts["exact_image_identity_links"] += 1
    # Nearby Commons search results are leads, not verified depictions.
    for candidate in candidates:
        source_id = candidate.get("source_feature_id")
        if not source_id:
            continue
        targets = by_osm.get(str(source_id), [])
        for record in targets:
            record.setdefault("image_candidates", []).append({
                "status": "unverified-candidate",
                "image_title": candidate.get("image_title"),
                "image_page": candidate.get("image_page"),
                "image_url": candidate.get("image_url"),
                "thumbnail_url": candidate.get("thumbnail_url"),
                "license_short_name": candidate.get("license_short_name"),
                "artist": candidate.get("artist"),
                "distance_m": candidate.get("distance_m"),
                "description": candidate.get("description"),
                "review_decision": candidate.get("review_decision"),
                "source": "Wikimedia Commons geosearch candidate; not automatically a building match",
            })
            counts["image_candidate_links"] += 1
    # Procedural facade panels: link by exact OSM identity and retain their verified/generic status.
    for item in signage:
        oid = item.get("osm_feature_id")
        if not oid:
            continue
        for record in by_osm.get(oid, []):
            record["procedural_facade_detail"] = {
                "asset": "complete_data/OSM/data/buildings/windows/ermita-buildings-facade-details.glb",
                "index_source": "complete_data/OSM/data/buildings/windows/facade-signage-index.csv",
                "mapped_name_or_use": item.get("mapped_name_or_use") or None,
                "building_height_m": item.get("building_height_m") or None,
                "estimated_floor_count": item.get("estimated_floor_count") or None,
                "sign_panel_generated": str(item.get("sign_panel_generated", "")).lower() == "true",
                "sign_text_or_logo_verified": str(item.get("sign_text_or_logo_verified", "")).lower() == "true",
                "note": item.get("note"),
                "identity_match": "exact OSM feature ID",
            }
            counts["procedural_facade_links"] += 1
    # Commercial photo/sign overlays: exact OSM target IDs only.
    for sign in commercial.get("store_signs", []):
        oid = sign.get("building_osm_id")
        if not oid:
            continue
        for record in by_osm.get(oid, []):
            record.setdefault("commercial_visual_assets", []).append({
                **sign,
                "report_source": "complete_data/OSM/Markets/commercial-facades-report.json",
                "status": "asset-placement-recorded; visual alignment still requires page inspection",
            })
            counts["commercial_asset_links"] += 1
    supreme_id = supreme.get("osm_feature_id")
    if supreme_id:
        for record in by_osm.get(supreme_id, []):
            record.setdefault("image_evidence", []).append({
                "evidence_type": "facade-photo-overlay-report",
                "building_name": supreme.get("target"),
                "source_photo": supreme.get("source_photo"),
                "photographer": supreme.get("photographer"),
                "license": supreme.get("license"),
                "texture": supreme.get("texture"),
                "glb": supreme.get("glb"),
                "panel_width_m": supreme.get("panel_width_m"),
                "panel_height_m": supreme.get("panel_height_m"),
                "limitations": supreme.get("limitations"),
                "applied_to_model": True,
                "source_manifest": "complete_data/OSM/Buildings/supreme-court-main-facade-report.json",
            })
            counts["verified_facade_overlay_links"] += 1
    # Photo catalogue for Robinsons Manila is retained as project-level evidence, and attached only to name-matched records.
    photos = robinsons.get("photos", [])
    if photos:
        for record in records:
            name = " ".join(str(record.get(k) or "") for k in ("name", "official_name", "brand")).casefold()
            if "robinsons" in name and ("manila" in name or "place" in name):
                record.setdefault("image_evidence", []).append({
                    "evidence_type": "named-reference-photo-catalogue",
                    "subject": robinsons.get("subject", "Robinsons Manila"),
                    "photos": photos,
                    "note": "Name-based evidence link; verify exact target facade and alignment before texture assignment.",
                    "applied_to_model": False,
                })
                counts["reference_photo_catalogue_links"] += 1
    return counts, {
        "procedural_facade_model": {
            "path": "complete_data/OSM/data/buildings/windows/ermita-buildings-facade-details.glb",
            "report": "complete_data/OSM/data/buildings/windows/facade-details-report.json",
            "window_panels": facade.get("window_panels"),
            "window_frames": facade.get("window_frames"),
            "window_sills": facade.get("window_sills"),
            "balcony_parts": facade.get("balcony_parts"),
            "door_placeholders": facade.get("door_placeholders"),
            "named_signboard_placeholders": facade.get("named_signboard_placeholders"),
            "limitation": "Procedural details; sign wording/logos are not verified unless sign_text_or_logo_verified is true.",
        },
        "commercial_facade_report": "complete_data/OSM/Markets/commercial-facades-report.json",
        "supreme_court_overlay_report": "complete_data/OSM/Buildings/supreme-court-main-facade-report.json",
        "robinsons_reference_catalogue": "complete_data/OSM/Markets/reference_photos/robinsons-manila/reference-index.json",
        "named_image_links": "complete_data/OSM/data/buildings/parts/building-image-links.json",
        "commons_candidate_source": "complete_data/OSM/data/buildings/parts/building-image-candidates.json",
    }


def main():
    data = read_json(INDEX)
    records = data.get("buildings", [])
    if not records:
        raise ValueError(f"No building records found in {INDEX}")
    fallback_rows, fallback_by_id, fallback_tree = load_fallback()
    source_geometries = load_source_geometries()
    counts = Counter()
    audit = []
    diagnostics = {"fallback_property_keys": sorted({str(k) for row in fallback_rows[:30] for k in row["props"].keys()}), "fallback_sample": [], "spatial_ratio_samples": []}
    for record in records:
        source_id = record.get("source_feature_id")
        linked_id = record.get("linked_osm_feature_id")
        exact = []
        for alias in osm_aliases(linked_id) | osm_aliases(source_id):
            exact.extend(fallback_by_id.get(alias, []))
        # Deduplicate candidates by object identity.
        exact = list({id(row): row for row in exact}.values())
        selected = exact[0] if len(exact) == 1 else None
        method = "exact-osm-id" if selected else "none"
        evidence = None
        if len(exact) > 1:
            counts["fallback_exact_ambiguous"] += 1
        if selected is None and record.get("source_key") in ("footprints", "roof_details"):
            geom = source_geometries.get((record.get("source_key"), int(record.get("source_feature_index", -1))))
            if geom is not None:
                point = geom.centroid
                candidates = query_rows(fallback_tree, fallback_rows, point)
                selected, evidence, status = choose_spatial_candidate(point, float(geom.area), candidates)
                if selected:
                    method = "spatial-high-confidence"
                    counts["fallback_spatial_linked"] += 1
                elif evidence:
                    method = "spatial-review"
                    counts["fallback_spatial_review"] += 1
        if evidence:
            counts["fallback_spatial_candidate_total"] += 1
            if len(diagnostics["spatial_ratio_samples"]) < 30:
                diagnostics["spatial_ratio_samples"].append({
                    "source_feature_id": source_id,
                    "source_key": record.get("source_key"),
                    "candidate_osm_id": evidence.get("candidate_osm_id"),
                    "candidate_area_ratio": evidence.get("candidate_area_ratio"),
                    "centroid_distance_m": evidence.get("centroid_distance_m"),
                    "candidate_count": evidence.get("candidate_count"),
                    "accepted": evidence.get("accepted"),
                })
        if selected:
            tags = selected["tags"]
            normalized = make_openfreemap_fields(tags)
            record["openfreemap"] = {
                "source": "complete_data/open free tile/building-fallback.geojson",
                "match_method": method,
                "match_confidence": 1.0 if method == "exact-osm-id" else 0.85,
                "source_feature_id": selected["id"],
                "raw_properties": selected["props"],
                "normalized": normalized,
                "source_geometry_used_for_matching_only": True,
            }
            # Supplement missing fields only; never replace existing OSM attributes or model geometry.
            if not record.get("name") and normalized.get("name"):
                record["name"] = normalized["name"]
            if not record.get("official_name") and normalized.get("official_name"):
                record["official_name"] = normalized["official_name"]
            if not record.get("brand") and normalized.get("brand"):
                record["brand"] = normalized["brand"]
            address = record.setdefault("address", {})
            for field, value in (("housenumber", normalized.get("housenumber")), ("street", normalized.get("street"))):
                if value and not address.get(field):
                    address[field] = value
            building = record.setdefault("building", {})
            for field, value in (
                ("type", normalized.get("building_type")), ("levels", normalized.get("levels")),
                ("height", normalized.get("height")), ("min_height", normalized.get("min_height")),
                ("material", normalized.get("material")), ("colour", normalized.get("colour")),
                ("roof_shape", normalized.get("roof_shape")), ("roof_material", normalized.get("roof_material")),
                ("roof_colour", normalized.get("roof_colour")),
            ):
                if value is not None and not building.get(field):
                    building[field] = value
            use = record.setdefault("use", {})
            if normalized.get("use") and not any(use.get(k) for k in ("amenity", "shop", "office", "tourism", "historic")):
                use["openfreemap_use"] = normalized["use"]
            counts["fallback_linked"] += 1
        else:
            if method == "spatial-review":
                counts["fallback_unmatched_after_review"] += 1
            else:
                counts["fallback_unmatched"] += 1
            if evidence:
                record["openfreemap_candidate"] = evidence
        audit.append({
            "part": record.get("part"), "source_key": record.get("source_key"),
            "source_feature_index": record.get("source_feature_index"), "source_feature_id": source_id,
            "linked_osm_feature_id": linked_id, "openfreemap_match_method": method,
            "openfreemap_source_feature_id": selected["id"] if selected else "",
            "openfreemap_candidate_name": selected["name"] if selected else (evidence or {}).get("candidate_name", ""),
            "openfreemap_candidate_count": (evidence or {}).get("candidate_count", 0),
            "openfreemap_candidate_area_ratio": (evidence or {}).get("candidate_area_ratio", ""),
            "openfreemap_candidate_distance_m": (evidence or {}).get("centroid_distance_m", ""),
            "openfreemap_candidate_accepted": bool(selected),
        })
    counts.update(attach_housenumbers(records, source_geometries))
    image_counts, asset_catalogue = attach_images_and_facades(records, load_image_metadata())
    counts.update(image_counts)
    for row in fallback_rows[:5]:
        diagnostics["fallback_sample"].append({"id": row["id"], "name": row["name"], "properties": row["props"], "bounds": list(row["geom"].bounds), "area_m2": round(row["area"], 2)})
    data["schema_version"] = "2.1.0"
    data["additional_sources"] = {
        "openfreemap_building_fallback": "complete_data/open free tile/building-fallback.geojson",
        "openfreemap_housenumbers": "complete_data/open free tile/layers/housenumber.geojsonl",
        "image_and_facade_evidence": asset_catalogue,
    }
    data["geometry_policy"] = "Metadata-only join. GLB files, geometries, coordinates, feature IDs, heights and existing material assignments are never modified by this process."
    data["matching_policy"] = "Exact OSM IDs first. OpenFreeMap fallback spatial links require centroid containment, acceptable area ratio and an unambiguous candidate; ambiguous candidates are recorded but do not supply semantic tags. House numbers are linked only when a single building footprint covers or is within 2.5 m of the label point. Image candidates remain unverified until reviewed."
    INDEX.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": "1.0.0",
        "status": "generated",
        "generated_from": [
            "complete_data/OSM/data/buildings/parts/building-enrichment-index.json",
            "complete_data/open free tile/building-fallback.geojson",
            "complete_data/open free tile/layers/housenumber.geojsonl",
            "complete_data/OSM/data/buildings/parts/building-image-links.json",
            "complete_data/OSM/data/buildings/parts/building-image-candidates.json (optional if workflow output exists)",
            "complete_data/OSM/data/buildings/windows/facade-signage-index.csv",
            "complete_data/OSM/Markets/commercial-facades-report.json",
            "complete_data/OSM/Buildings/supreme-court-main-facade-report.json",
        ],
        "building_records": len(records),
        "counts": dict(counts),
        "fallback_feature_count": len(fallback_rows),
        "diagnostics": diagnostics,
        "housenumber_source_records": len(load_housenumbers()),
        "image_asset_catalogue": asset_catalogue,
        "limitations": [
            "This is a metadata/evidence join, not proof of 100% real-world identity or visual fidelity.",
            "OpenFreeMap fallback records that cannot be matched safely remain unmatched or in the review queue.",
            "Wikimedia geosearch results are image candidates, not verified building photographs; they are never automatically applied as textures.",
            "The procedural facade GLB contains generic placeholders; sign text/logo verification is recorded separately.",
            "Photographic overlay reports describe intended/applied overlay assets but require visual alignment review in the viewer.",
            "No GLB, geometry, coordinates, heights, or material assignments are changed by this workflow.",
        ],
        "audit_csv": str(AUDIT.relative_to(ROOT)),
        "index_path": str(INDEX.relative_to(ROOT)),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with AUDIT.open("w", encoding="utf-8", newline="") as stream:
        fields = list(audit[0].keys()) if audit else ["part", "source_key", "source_feature_index", "source_feature_id"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit)
    print(json.dumps({"index": str(INDEX), "report": str(REPORT), "audit": str(AUDIT), "building_records": len(records), "fallback_features": len(fallback_rows), "counts": dict(counts), "diagnostics": diagnostics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
