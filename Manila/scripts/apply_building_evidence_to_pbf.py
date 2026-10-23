#!/usr/bin/env python3
"""Apply existing Manila building-evidence records directly to source vector tiles."""
from __future__ import annotations
import hashlib, json, os, sys, time
from pathlib import Path
import mapbox_vector_tile

ROOT = Path(__file__).resolve().parents[1]
TILES = ROOT / "vector-tiles"
EVIDENCE = ROOT / "3d-rag" / "building-evidence.jsonl"
OUT = ROOT / "3d-rag"
REPORT = OUT / "apply-report.json"
BUILDING_LAYERS = {"building", "buildings"}

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

def proposed_properties(record):
    rag = record.get("rag_result") or {}
    proposed = rag.get("proposed_attributes") or {}
    result = {}
    if isinstance(proposed, list):
        for item in proposed:
            if not isinstance(item, dict) or "value" not in item:
                continue
            name = item.get("attribute") or item.get("name") or item.get("property") or item.get("key")
            if name and item.get("status") not in ("unknown", "conflicting") and item.get("value") is not None:
                result[str(name)] = item["value"]
    elif isinstance(proposed, dict):
        for name, item in proposed.items():
            if isinstance(item, dict):
                status = item.get("status")
                value = item.get("value")
                if value is not None and status not in ("unknown", "conflicting"):
                    result[str(name)] = value
            elif item is not None:
                result[str(name)] = item
    # Also accept explicit application payloads if present in the saved record.
    direct = record.get("apply_attributes") or rag.get("apply_attributes") or {}
    if isinstance(direct, dict):
        result.update({str(k): v for k, v in direct.items() if v is not None})
    return result

def apply_geometry(feature, record):
    rag = record.get("rag_result") or {}
    geom = rag.get("proposed_geometry") or rag.get("geometry")
    if isinstance(geom, dict) and geom.get("type") in ("Polygon", "MultiPolygon"):
        feature["geometry"] = geom
        return True
    # Do not mistake visual descriptions or geometry hashes for actual geometry.
    return False

def main():
    evidence = evidence_records()
    changed_tiles, changed_features, changed_properties, changed_geometry = [], 0, 0, 0
    matched_keys = set()
    errors = []
    for p in sorted(TILES.rglob("*.pbf")):
        raw = p.read_bytes()
        try:
            decoded = mapbox_vector_tile.decode(raw, default_options={"y_coord_down": True})
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
                attrs = proposed_properties(record)
                for name, value in attrs.items():
                    if props.get(name) != value:
                        props[name] = value
                        changed_properties += 1
                        tile_changed = True
                if apply_geometry(feature, record):
                    changed_geometry += 1
                    tile_changed = True
        if tile_changed:
            layers = []
            for layer_name, layer in decoded.items():
                layers.append({
                    "name": layer_name,
                    "features": layer.get("features", []),
                    "extent": layer.get("extent", 4096),
                    "version": layer.get("version", 2),
                })
            try:
                encoded = mapbox_vector_tile.encode(layers)
                # Verify the output is decodable before replacing the tile.
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
        "evidence_records": len(evidence),
        "matched_building_records": len(matched_keys),
        "unmatched_evidence_records": len(set(evidence) - matched_keys),
        "changed_tile_count": len(changed_tiles),
        "changed_tiles": changed_tiles,
        "changed_property_count": changed_properties,
        "geometry_replacements": changed_geometry,
        "errors": errors,
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not changed_tiles:
        raise RuntimeError("No PBF tiles were changed. Check evidence keys and proposed attributes in apply-report.json.")
    if errors:
        raise RuntimeError(f"Some PBF tiles failed; see {REPORT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
