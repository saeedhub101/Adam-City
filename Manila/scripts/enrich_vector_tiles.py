#!/usr/bin/env python3
"""Incrementally enrich Manila PBF render properties and collect public KartaView photo references.

No OpenStreetMap/Overpass API is used. Existing building geometry is never intentionally
changed. KartaView imagery metadata is saved as review evidence; the script does not claim
to have visually interpreted a photograph or invent a sign/logo from metadata alone.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import mapbox_vector_tile
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
TILES_ROOT = ROOT / "vector-tiles"
OUTPUT_ROOT = ROOT / "3d-enrichment"
REPORT_PATH = OUTPUT_ROOT / "progress-report.json"
PLAN_PATH = OUTPUT_ROOT / "building-render-plan.jsonl"
KARTAVIEW_URL = "https://api.openstreetcam.org/1.0/list/nearby-photos/"
TIMEOUT = 25
MAX_RETRIES = 4
session = requests.Session()
session.headers.update({"User-Agent": "Adam-City-Manila-3D-Enrichment/1.0 (public KartaView imagery lookup)"})

COMMERCIAL_KEYS = ("shop", "brand", "operator", "office")
FACADE_KEYS = ("facade:colour", "building:colour", "colour")
ROOF_KEYS = ("roof:material", "roof:colour", "roof:shape", "roof:levels", "roof:height")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def checkpoint(path: Path, report: dict[str, Any]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rel = [str(path.relative_to(REPO_ROOT)), str(REPORT_PATH.relative_to(REPO_ROOT)),
           str(PLAN_PATH.relative_to(REPO_ROOT))]
    git("add", "--", *rel)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("commit", "-m", "Checkpoint Manila 3D building enrichment")
    for attempt in range(5):
        pushed = git("push", "origin", "HEAD:main", check=False)
        if pushed.returncode == 0:
            print(f"CHECKPOINT SAVED: {path.relative_to(REPO_ROOT)}", flush=True)
            return
        print(pushed.stdout, file=sys.stderr, flush=True)
        if git("fetch", "origin", "main", check=False).returncode:
            break
        if git("rebase", "origin/main", check=False).returncode:
            git("rebase", "--abort", check=False)
            break
    raise RuntimeError("Checkpoint push failed; local runner state retained until job ends.")


def feature_center(path: Path, feature: dict[str, Any], extent: int) -> tuple[float, float] | None:
    try:
        z, x, y = map(int, path.relative_to(TILES_ROOT).with_suffix("").parts[-3:])
        coords: list[tuple[float, float]] = []
        def walk(v: Any) -> None:
            if isinstance(v, (list, tuple)):
                if len(v) >= 2 and isinstance(v[0], (int, float)) and isinstance(v[1], (int, float)):
                    coords.append((float(v[0]), float(v[1])))
                else:
                    for child in v:
                        walk(child)
        walk((feature.get("geometry") or {}).get("coordinates"))
        if not coords:
            return None
        # Unique vertices avoid overweighting repeated polygon closure points.
        coords = list(dict.fromkeys(coords))
        px = sum(p[0] for p in coords) / len(coords)
        py = sum(p[1] for p in coords) / len(coords)
        n = 2 ** z
        lon = (x + px / extent) / n * 360.0 - 180.0
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
        return lat, lon
    except (ValueError, IndexError, TypeError):
        return None


def nearby_photos(lat: float, lon: float, radius: int = 250) -> list[dict[str, Any]]:
    """Use the public anonymous KartaView 1.0 endpoint; no token or OSM API."""
    for attempt in range(MAX_RETRIES):
        try:
            response = session.post(KARTAVIEW_URL, data={"lat": lat, "lng": lon, "radius": radius}, timeout=TIMEOUT)
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(20, 2 ** attempt))
                continue
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status") or {}
            if status.get("apiCode") not in (None, 600, "600"):
                print(f"KartaView returned apiCode={status.get('apiCode')}; no photos recorded for this query.", flush=True)
                return []
            result = payload.get("result") or {}
            data = result.get("data") or []
            if isinstance(data, dict):
                data = data.get("photos") or data.get("data") or []
            return [item for item in data if isinstance(item, dict)]
        except (requests.RequestException, ValueError) as exc:
            if attempt == MAX_RETRIES - 1:
                print(f"KartaView query skipped: {exc}", file=sys.stderr, flush=True)
            else:
                time.sleep(min(20, 2 ** attempt))
    return []


def photo_fields(photo: dict[str, Any]) -> dict[str, Any]:
    def first(*keys: str) -> Any:
        for key in keys:
            if photo.get(key) not in (None, ""):
                return photo[key]
        return None
    file_url = first("fileurl", "fileUrl", "fileurlProc", "fileurlTh", "url")
    if file_url and str(file_url).startswith("/"):
        file_url = "https://api.openstreetcam.org" + str(file_url)
    return {
        "photo_id": first("id", "photoId", "photo_id"),
        "sequence_id": first("sequenceId", "sequence_id", "sequence"),
        "lat": as_float(first("lat", "latitude")),
        "lon": as_float(first("lng", "lon", "longitude")),
        "heading": as_float(first("heading", "direction")),
        "shot_date": first("shotDate", "dateAdded", "date"),
        "image_url": file_url,
        "source": "KartaView",
    }


def as_float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat, lon = a
    olat, olon = b
    dy = (olat - lat) * 111320.0
    dx = (olon - lon) * 111320.0 * math.cos(math.radians(lat))
    return math.hypot(dx, dy)


def add_render_properties(props: dict[str, Any]) -> int:
    """Only add missing, evidence-backed or explicitly labelled estimated render hints."""
    added = 0
    def set_missing(key: str, value: Any) -> None:
        nonlocal added
        if value not in (None, "") and props.get(key) in (None, ""):
            props[key] = value
            added += 1

    facade = next((props.get(k) for k in FACADE_KEYS if props.get(k)), None)
    roof = next((props.get(k) for k in ROOF_KEYS if props.get(k)), None)
    set_missing("render_facade_color", facade)
    set_missing("render_facade_material", props.get("facade:material") or props.get("building:material"))
    set_missing("render_roof_material", props.get("roof:material"))
    set_missing("render_roof_color", props.get("roof:colour"))
    set_missing("render_roof_shape", props.get("roof:shape"))
    set_missing("render_style_source", "existing_building_properties" if (facade or roof) else "conservative_default")
    set_missing("render_geometry_source", "original_pbf_geometry")
    # A shop tag is evidence of commercial use; amenity alone is not treated as a shop.
    shop = props.get("shop")
    if shop:
        set_missing("render_commercial_frontage", True)
        set_missing("render_sign_candidate", True)
        set_missing("render_sign_text", props.get("name") or props.get("brand") or props.get("operator"))
        set_missing("render_sign_position", "street-facing_ground-floor_candidate")
        set_missing("render_sign_position_confidence", "needs_KartaView_visual_confirmation")
    elif props.get("brand") or props.get("operator"):
        set_missing("render_commercial_frontage", True)
        set_missing("render_sign_candidate", True)
        set_missing("render_sign_text", props.get("name") or props.get("brand") or props.get("operator"))
        set_missing("render_sign_position", "street-facing_candidate")
        set_missing("render_sign_position_confidence", "needs_KartaView_visual_confirmation")
    height = as_float(props.get("render_height") or props.get("height"))
    min_height = as_float(props.get("render_min_height") or props.get("min_height")) or 0.0
    if height and height > min_height:
        set_missing("render_facade_detail_level", "evidence_based" if facade else "basic")
    return added


def load_plan() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if PLAN_PATH.exists():
        for line in PLAN_PATH.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                if item.get("building_key"):
                    records[item["building_key"]] = item
            except json.JSONDecodeError:
                continue
    return records


def write_plan(records: dict[str, dict[str, Any]]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with PLAN_PATH.open("w", encoding="utf-8") as f:
        for key in sorted(records):
            f.write(json.dumps(records[key], ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    paths = sorted(p for p in TILES_ROOT.rglob("*.pbf") if p.is_file())
    if not paths:
        print(f"No PBF files found in {TILES_ROOT}", file=sys.stderr)
        return 2
    report: dict[str, Any] = {
        "status": "running", "tile_files_found": len(paths), "tiles_processed": 0,
        "tiles_changed": 0, "decode_errors": 0, "buildings_seen": 0,
        "render_properties_added": 0, "kartaview_queries": 0, "kartaview_photos_found": 0,
        "buildings_with_nearby_photos": 0, "geometry_changed": False,
        "osm_api_used": False, "kartaview_requires_api_key": False,
        "note": "KartaView metadata is a photo reference only; sign placement/appearance needs visual confirmation.",
    }
    plan = load_plan()
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Starting {len(paths)} PBF tiles; checkpoint after every tile; workflow limit is 6 hours.", flush=True)

    # Resume from the set of tiles already listed in the durable report.
    done = set(report.get("completed_tiles", []))
    for path in paths:
        rel = str(path.relative_to(REPO_ROOT))
        if rel in done:
            continue
        try:
            original_bytes = path.read_bytes()
            decoded = mapbox_vector_tile.decode(original_bytes, default_options={"y_coord_down": True})
        except Exception as exc:
            report["decode_errors"] += 1
            report.setdefault("errors", []).append({"tile": rel, "error": str(exc)[:500]})
            report.setdefault("completed_tiles", []).append(rel)
            checkpoint(path, report)
            continue

        tile_features = 0
        tile_added = 0
        for layer_name, layer in decoded.items():
            if str(layer_name).lower() not in ("building", "buildings"):
                continue
            extent = int(layer.get("extent", 4096))
            for index, feature in enumerate(layer.get("features", [])):
                tile_features += 1
                props = feature.get("properties")
                if not isinstance(props, dict):
                    props = {}
                    feature["properties"] = props
                center = feature_center(path, feature, extent)
                uid = props.get("building_uid") or props.get("osm_id") or hashlib.sha1(f"{rel}|{layer_name}|{index}".encode()).hexdigest()[:20]
                key = f"{rel}|{layer_name}|{index}|{uid}"
                before = dict(props)
                tile_added += add_render_properties(props)
                rec = plan.get(key) or {
                    "building_key": key, "tile": rel, "layer": layer_name, "feature_index": index,
                    "building_uid": uid, "name": props.get("building_name") or props.get("name"),
                    "center": {"lat": center[0], "lon": center[1]} if center else None,
                    "height_m": as_float(props.get("render_height") or props.get("height")),
                    "facade": {"color": props.get("render_facade_color"), "material": props.get("render_facade_material")},
                    "roof": {"color": props.get("render_roof_color"), "material": props.get("render_roof_material"), "shape": props.get("render_roof_shape")},
                    "commercial": bool(props.get("render_commercial_frontage") or props.get("shop")),
                    "sign_candidate": bool(props.get("render_sign_candidate") or props.get("shop")),
                    "sign_text_candidate": props.get("render_sign_text") or props.get("name") or props.get("brand"),
                    "sign_position": props.get("render_sign_position"),
                    "sign_position_confidence": props.get("render_sign_position_confidence"),
                    "properties_before": before,
                }
                if center and len(plan) < 100000 and not rec.get("kartaview_photos_checked"):
                    # Query one public coverage sample per zoom-14 tile; broader zooms are too large.
                    try:
                        z = int(path.relative_to(TILES_ROOT).parts[-3])
                    except (ValueError, IndexError):
                        z = 0
                    if z >= 14:
                        photos = nearby_photos(center[0], center[1], 250)
                        report["kartaview_queries"] += 1
                        normalized = [photo_fields(p) for p in photos]
                        normalized = [p for p in normalized if p.get("lat") is not None and p.get("lon") is not None]
                        normalized.sort(key=lambda p: distance_m(center, (p["lat"], p["lon"])))
                        rec["kartaview_photos"] = [
                            {**p, "distance_to_building_center_m": round(distance_m(center, (p["lat"], p["lon"])), 1)}
                            for p in normalized[:8]
                        ]
                        rec["kartaview_photos_checked"] = True
                        report["kartaview_photos_found"] += len(normalized)
                        if normalized:
                            report["buildings_with_nearby_photos"] += 1
                plan[key] = rec

        if tile_added:
            layer_list = [{"name": name, "features": layer.get("features", []),
                           "extent": layer.get("extent", 4096), "version": layer.get("version", 2)}
                          for name, layer in decoded.items()]
            encoded = mapbox_vector_tile.encode(layer_list, default_options={"y_coord_down": True})
            check_decoded = mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
            # Verify the exact decoded geometry payload for every layer before replacing the PBF.
            for name, layer in decoded.items():
                check_layer = check_decoded.get(name)
                if check_layer is None or [f.get("geometry") for f in layer.get("features", [])] != [f.get("geometry") for f in check_layer.get("features", [])]:
                    raise RuntimeError(f"Geometry verification failed for {rel}; original tile was not replaced.")
            path.write_bytes(encoded)
            report["tiles_changed"] += 1
        report["tiles_processed"] += 1
        report["buildings_seen"] += tile_features
        report["render_properties_added"] += tile_added
        report.setdefault("completed_tiles", []).append(rel)
        write_plan(plan)
        checkpoint(path, report)
        print(f"Processed {rel}: buildings={tile_features}, render properties added={tile_added}", flush=True)

    report["status"] = "completed"
    report["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_plan(plan)
    git("add", "--", str(REPORT_PATH.relative_to(REPO_ROOT)), str(PLAN_PATH.relative_to(REPO_ROOT)))
    if git("diff", "--cached", "--quiet", check=False).returncode:
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        git("commit", "-m", "Finalize Manila 3D enrichment report")
        git("push", "origin", "HEAD:main")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
