#!/usr/bin/env python3
"""Apply explicit, identity-matched attributes from saved Manila evidence to source PBF tiles."""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path
import mapbox_vector_tile

ROOT = Path(__file__).resolve().parents[1]
TILES = ROOT / "vector-tiles"
EVIDENCE = ROOT / "3d-rag" / "building-evidence.jsonl"
OUT = ROOT / "3d-rag"
REPORT = OUT / "apply-report.json"
BUILDING_LAYERS = {"building", "buildings"}
BLOCKED_KEYS = {"geometry", "id", "osm_id", "building_uid", "record_id", "source_file", "distance_m", "lat", "lon", "latitude", "longitude"}

def key_for(layer, feature, tile_rel, index):
    props = feature.get("properties") or {}
    uid = props.get("building_uid") or props.get("osm_id") or feature.get("id")
    if uid not in (None, ""):
        return f"{layer}:{uid}"
    geom = feature.get("geometry") or {}
    digest = hashlib.sha1(f"{tile_rel}|{layer}|{index}|{json.dumps(geom, sort_keys=True)}".encode()).hexdigest()[:20]
    return "tile:" + digest

def evidence_records():
    if not EVIDENCE.is_file():
        raise RuntimeError(f"Evidence report missing: {EVIDENCE}")
    records = {}
    with EVIDENCE.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid evidence JSONL line {n}: {exc}") from exc
            key = row.get("building_key")
            if key:
                records[key] = row
    if not records:
        raise RuntimeError("Evidence report contains no usable building records; no PBF files changed.")
    return records

def normalize_attribute_map(value):
    result = {}
    if isinstance(value, dict):
        for name, item in value.items():
            if isinstance(item, dict):
                val = item.get("value")
                status = str(item.get("status", "")).lower()
                if val is not None and status not in {"conflicting", "unknown", "rejected"}:
                    result[str(name)] = val
            elif item is not None:
                result[str(name)] = item
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            name = item.get("attribute") or item.get("name") or item.get("property") or item.get("key") or item.get("tag")
            if name and item.get("value") is not None and str(item.get("status", "")).lower() not in {"conflicting", "unknown", "rejected"}:
                result[str(name)] = item["value"]
    return result

def proposed_properties(record, existing_props):
    rag = record.get("rag_result")
    if not isinstance(rag, dict):
        rag = {}
    result = {}
    for container in (rag, record):
        for field in ("proposed_attributes", "apply_attributes", "property_updates", "attribute_updates", "building_attributes", "proposed_properties", "changes"):
            result.update(normalize_attribute_map(container.get(field)))

    # Local repository facts are applied only when the evidence record's OSM/building ID
    # exactly matches the feature ID; proximity-only records are never treated as identity.
    feature_ids = {str(v) for v in (
        existing_props.get("building_uid"), existing_props.get("osm_id"),
        existing_props.get("@id"), existing_props.get("id")
    ) if v not in (None, "")}
    for local in record.get("local_evidence", []) if isinstance(record.get("local_evidence"), list) else []:
        if not isinstance(local, dict) or local.get("record_id") in (None, ""):
            continue
        if str(local["record_id"]) not in feature_ids:
            continue
        attrs = local.get("attributes")
        if isinstance(attrs, dict):
            for k, v in attrs.items():
                if k not in BLOCKED_KEYS and v not in (None, ""):
                    result.setdefault(str(k), v)
        if local.get("name") not in (None, ""):
            result.setdefault("name", local["name"])

    # High-confidence visual facts are usable only for confirmed/likely building matches
    # and only when the finding explicitly names a known OSM property/tag.
    visual = record.get("visual_analysis")
    if isinstance(visual, dict) and str(visual.get("building_match", "")).lower() in {"confirmed", "likely"}:
        allowed = {"name", "height", "building:levels", "building:colour", "building:material",
                   "roof:colour", "roof:material", "roof:shape", "building", "shop", "amenity"}
        findings = visual.get("visible_features")
        if isinstance(findings, list):
            for item in findings:
                if not isinstance(item, dict) or item.get("value") is None:
                    continue
                confidence = str(item.get("confidence", "")).lower()
                name = item.get("attribute") or item.get("property") or item.get("tag") or item.get("key")
                if name and str(name) in allowed and confidence in {"high", "verified"}:
                    result[str(name)] = item["value"]
    return {k: v for k, v in result.items() if k not in BLOCKED_KEYS and v is not None}

def main():
    evidence = evidence_records()
    changed_tiles, changed_features, changed_properties = [], 0, 0
    matched_keys, errors = set(), []
    evidence_with_attributes = proposed_attribute_count = unchanged_property_count = 0
    rag_result_counts = {}
    for record in evidence.values():
        rr = record.get("rag_result")
        kind = "null" if rr is None else ("dict:" + ",".join(sorted(rr.keys())[:8]) if isinstance(rr, dict) else type(rr).__name__)
        rag_result_counts[kind] = rag_result_counts.get(kind, 0) + 1
    pbf_count = 0
    for p in sorted(TILES.rglob("*.pbf")):
        pbf_count += 1
        try:
            decoded = mapbox_vector_tile.decode(p.read_bytes(), default_options={"y_coord_down": True})
        except Exception as exc:
            errors.append({"tile": str(p.relative_to(ROOT)), "error": f"decode: {exc}"})
            continue
        tile_rel = str(p.relative_to(ROOT))
        tile_changed = False
        for layer_name, layer in decoded.items():
            if str(layer_name).lower() not in BUILDING_LAYERS:
                continue
            for i, feature in enumerate(layer.get("features", [])):
                key = key_for(layer_name, feature, tile_rel, i)
                record = evidence.get(key)
                if not record:
                    continue
                matched_keys.add(key)
                props = feature.setdefault("properties", {})
                attrs = proposed_properties(record, props)
                if attrs:
                    evidence_with_attributes += 1
                feature_changed = False
                for name, value in attrs.items():
                    proposed_attribute_count += 1
                    old = props.get(name)
                    if old == value or (old is not None and str(old) == str(value)):
                        unchanged_property_count += 1
                        continue
                    props[name] = value
                    changed_properties += 1
                    feature_changed = True
                if feature_changed:
                    changed_features += 1
                    tile_changed = True
        if tile_changed:
            layers = [{"name": name, "features": layer.get("features", []),
                       "extent": layer.get("extent", 4096), "version": layer.get("version", 2)}
                      for name, layer in decoded.items()]
            try:
                encoded = mapbox_vector_tile.encode(layers)
                mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
                p.write_bytes(encoded)
                changed_tiles.append(tile_rel)
            except Exception as exc:
                errors.append({"tile": tile_rel, "error": f"encode/write: {exc}"})
                raise RuntimeError(f"Failed to safely encode {tile_rel}: {exc}") from exc
    report = {
        "status": "completed" if not errors else "completed_with_errors",
        "operation": "apply_existing_evidence_to_pbf",
        "evidence_file": "Manila/3d-rag/building-evidence.jsonl",
        "pbf_root": "Manila/vector-tiles",
        "pbf_files_scanned": pbf_count,
        "evidence_records": len(evidence),
        "matched_building_records": len(matched_keys),
        "unmatched_evidence_records": len(set(evidence) - matched_keys),
        "rag_result_shape_counts": rag_result_counts,
        "records_with_actionable_attributes": evidence_with_attributes,
        "proposed_attribute_count": proposed_attribute_count,
        "properties_already_matching_evidence": unchanged_property_count,
        "changed_tile_count": len(changed_tiles),
        "changed_tiles": changed_tiles,
        "changed_building_features": changed_features,
        "changed_property_count": changed_properties,
        "geometry_replacements": 0,
        "geometry_policy": "Geometry and coordinates preserved; evidence does not provide tile-coordinate-safe geometry patches.",
        "errors": errors,
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not changed_tiles:
        raise RuntimeError("No supported PBF property changes were available. See aggregate evidence diagnostics in apply-report.json; do not fabricate changes.")
    if errors:
        raise RuntimeError(f"Some PBF tiles failed; see {REPORT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
