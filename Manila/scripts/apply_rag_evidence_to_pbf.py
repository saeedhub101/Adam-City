#!/usr/bin/env python3
"""Apply high-confidence, identity-confirmed RAG attributes to Manila vector-tile PBFs.

Only feature properties are changed. Geometry is verified byte-for-byte at the decoded
coordinate-array level before a tile is replaced. Unverified/inferred/conflicting values
remain in the evidence JSONL and are not applied to rendering properties.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys, time
from pathlib import Path
from typing import Any
import mapbox_vector_tile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TILES = ROOT / "vector-tiles"
RAG = ROOT / "3d-rag" / "building-evidence.jsonl"
OUT = ROOT / "3d-rag"
REPORT = OUT / "apply-report.json"
CHECKPOINT_EVERY = 5
MIN_CONFIDENCE = 0.80

def git(*args: str, check: bool = True):
    return subprocess.run(["git", *args], cwd=REPO, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=check)

def load_evidence():
    records = {}
    with RAG.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("building_key") and r.get("rag_result"):
                    records[r["building_key"]] = r
            except json.JSONDecodeError:
                continue
    return records

def geometry_hash(g):
    return hashlib.sha1(json.dumps(g, sort_keys=True).encode()).hexdigest()

def truth_confirmed(value):
    if value is True:
        return True
    return str(value or "").strip().lower() in {"confirmed", "verified", "true", "exact_match", "exact match"}

def confidence(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def scalar(value):
    if value is None or isinstance(value, (dict, list)):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)

def norm_key(key):
    return str(key or "").strip().lower().replace("-", "_").replace(" ", "_").replace(":", "_")

# Only these allowlisted attributes can affect visible rendering or standard building labels.
ALIASES = {
    "name": "name", "building_name": "name", "official_name": "name",
    "height": "height", "building_height": "height", "render_height": "render_height",
    "building_levels": "building:levels", "levels": "building:levels", "building_levels_count": "building:levels",
    "facade_colour": "render_facade_color", "facade_color": "render_facade_color",
    "building_colour": "render_facade_color", "building_color": "render_facade_color",
    "render_facade_color": "render_facade_color",
    "roof_colour": "render_roof_color", "roof_color": "render_roof_color",
    "render_roof_color": "render_roof_color",
    "facade_material": "render_facade_material", "building_material": "render_facade_material",
    "render_facade_material": "render_facade_material",
    "roof_material": "render_roof_material", "render_roof_material": "render_roof_material",
    "roof_shape": "render_roof_shape", "render_roof_shape": "render_roof_shape",
}

def prepare_changes(record):
    result = record.get("rag_result") or {}
    if not truth_confirmed(result.get("identity_match")):
        return {}, "identity_not_confirmed"
    attrs = result.get("proposed_attributes") or {}
    if not isinstance(attrs, dict):
        return {}, "attributes_not_object"
    changes = {}
    for raw_key, detail in attrs.items():
        if not isinstance(detail, dict):
            continue
        status = str(detail.get("status") or "").strip().lower()
        conf = confidence(detail.get("confidence"))
        if status != "verified" or conf < MIN_CONFIDENCE:
            continue
        dest = ALIASES.get(norm_key(raw_key))
        value = scalar(detail.get("value"))
        if not dest or value in (None, ""):
            continue
        if dest in {"height", "render_height", "building:levels"}:
            try:
                n = float(value)
                if n <= 0 or n > 1000:
                    continue
                value = int(n) if n.is_integer() else n
            except (TypeError, ValueError):
                continue
        if dest in {"render_facade_color", "render_roof_color"}:
            value = str(value).strip()
            if not value or len(value) > 40:
                continue
        # Prefer the highest-confidence value if the model emits aliases for one field.
        prior = changes.get(dest)
        if prior is None or conf > prior["confidence"]:
            changes[dest] = {"value": value, "confidence": conf}
    return changes, "eligible" if changes else "no_verified_high_confidence_attributes"

def checkpoint(report, changed_paths, final=False):
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths = [str(p.relative_to(REPO)) for p in changed_paths] + [str(REPORT.relative_to(REPO))]
    git("add", "--", *paths)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("commit", "-m", "Apply verified Manila RAG building attributes")
    for _ in range(5):
        p = git("push", "origin", "HEAD:main", check=False)
        if p.returncode == 0:
            print("CHECKPOINT SAVED: PBF property updates and apply report", flush=True)
            return
        print(p.stdout, file=sys.stderr, flush=True)
        if git("fetch", "origin", "main", check=False).returncode:
            break
        if git("rebase", "origin/main", check=False).returncode:
            git("rebase", "--abort", check=False)
            break
    raise RuntimeError("Unable to push apply checkpoint; no success is claimed.")

def main():
    if not RAG.exists():
        print(f"Missing RAG evidence file: {RAG}", file=sys.stderr); return 2
    evidence = load_evidence()
    paths = sorted(TILES.rglob("*.pbf"))
    report = {
        "status": "running", "operation": "apply_verified_rag_attributes_to_pbf",
        "evidence_file": "Manila/3d-rag/building-evidence.jsonl",
        "pbf_root": "Manila/vector-tiles", "tiles_found": len(paths),
        "evidence_records_with_model_output": len(evidence), "minimum_confidence": MIN_CONFIDENCE,
        "policy": "Only status=verified, confidence>=0.80, and identity_match=confirmed; never overwrite existing properties; preserve geometry.",
        "tiles_processed": 0, "tiles_changed": 0, "buildings_matched": 0,
        "buildings_updated": 0, "properties_added": 0, "names_added": 0,
        "facade_colors_added": 0, "roof_colors_added": 0, "heights_added": 0,
        "skipped_identity_unconfirmed": 0, "skipped_no_verified_attributes": 0,
        "geometry_changed": False, "errors": []
    }
    dirty = []
    pending = 0
    for path in paths:
        rel = str(path.relative_to(REPO))
        try:
            original = path.read_bytes()
            decoded = mapbox_vector_tile.decode(original, default_options={"y_coord_down": True})
        except Exception as exc:
            report["errors"].append({"tile": rel, "stage": "decode", "error": str(exc)[:300]})
            continue
        tile_changes = 0
        tile_buildings_updated = 0
        original_geometries = {name: [f.get("geometry") for f in layer.get("features", [])]
                               for name, layer in decoded.items()}
        for layer_name, layer in decoded.items():
            if str(layer_name).lower() not in {"building", "buildings"}:
                continue
            for index, feature in enumerate(layer.get("features", [])):
                geom = feature.get("geometry") or {}
                if geom.get("type") not in {"Polygon", "MultiPolygon"}:
                    continue
                props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
                uid = props.get("building_uid") or props.get("osm_id") or feature.get("id")
                key = f"{layer_name}:{uid}" if uid else "tile:" + hashlib.sha1(
                    f"{rel}|{layer_name}|{index}|{json.dumps(geom, sort_keys=True)}".encode()
                ).hexdigest()[:20]
                rec = evidence.get(key)
                if not rec or rec.get("tile") != rel or rec.get("layer") != layer_name or rec.get("feature_index") != index:
                    continue
                if rec.get("geometry_sha1") != geometry_hash(geom):
                    report["errors"].append({"tile": rel, "building_key": key, "stage": "match",
                                             "error": "geometry hash mismatch; skipped to prevent wrong-building edits"})
                    continue
                report["buildings_matched"] += 1
                changes, reason = prepare_changes(rec)
                if reason == "identity_not_confirmed":
                    report["skipped_identity_unconfirmed"] += 1
                    continue
                if not changes:
                    report["skipped_no_verified_attributes"] += 1
                    continue
                props = feature.setdefault("properties", {})
                added_here = 0
                for dest, item in changes.items():
                    if props.get(dest) not in (None, ""):
                        continue
                    props[dest] = item["value"]
                    added_here += 1
                    report["properties_added"] += 1
                    if dest == "name": report["names_added"] += 1
                    if dest == "render_facade_color": report["facade_colors_added"] += 1
                    if dest == "render_roof_color": report["roof_colors_added"] += 1
                    if dest in {"height", "render_height", "building:levels"}: report["heights_added"] += 1
                if added_here:
                    tile_changes += added_here
                    tile_buildings_updated += 1
        if tile_changes:
            layer_list = [{"name": name, "features": layer.get("features", []),
                           "extent": layer.get("extent", 4096), "version": layer.get("version", 2)}
                          for name, layer in decoded.items()]
            try:
                encoded = mapbox_vector_tile.encode(layer_list, default_options={"y_coord_down": True})
                checked = mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
                for name, expected in original_geometries.items():
                    actual = checked.get(name)
                    if actual is None or expected != [f.get("geometry") for f in actual.get("features", [])]:
                        raise RuntimeError(f"geometry verification failed for layer {name}")
                path.write_bytes(encoded)
                dirty.append(path)
                report["tiles_changed"] += 1
                report["buildings_updated"] += tile_buildings_updated
                pending += 1
            except Exception as exc:
                path.write_bytes(original)
                report["errors"].append({"tile": rel, "stage": "encode_verify", "error": str(exc)[:300]})
                # Roll back counters for this tile, since no changes were retained.
                report["properties_added"] -= tile_changes
                report["names_added"] = max(0, report["names_added"])
                report["facade_colors_added"] = max(0, report["facade_colors_added"])
                report["roof_colors_added"] = max(0, report["roof_colors_added"])
                report["heights_added"] = max(0, report["heights_added"])
        report["tiles_processed"] += 1
        if pending >= CHECKPOINT_EVERY:
            checkpoint(report, dirty)
            dirty.clear(); pending = 0
        print(f"Processed {rel}: matched={report['buildings_matched']} tiles_changed={report['tiles_changed']}", flush=True)
    if dirty or report["tiles_processed"]:
        report["status"] = "completed"
        report["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        checkpoint(report, dirty, final=True)
    else:
        report["status"] = "completed_with_errors" if report["errors"] else "completed"
        report["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        checkpoint(report, [])
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0 if not report["errors"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

# Workflow execution is triggered by changes to this script.
