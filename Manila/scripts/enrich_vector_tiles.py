#!/usr/bin/env python3
"""Incrementally enrich Manila PBF building properties from verified OSM data.

Processes one tile at a time, preserves feature geometry, and pushes each changed
tile to main immediately so completed work survives interruption.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
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
REPORT_PATH = ROOT / "pbf-enrichment-report.json"
OVERPASS_URL = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
USER_AGENT = "Adam-City-Manila-PBF-Enrichment/2.0 (incremental checkpoints)"
REQUEST_TIMEOUT = 90
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

OSM_TAGS = (
    "name", "name:en", "name:tl", "building", "building:levels",
    "building:levels:underground", "height", "min_height",
    "building:colour", "building:material", "roof:colour", "roof:material",
    "roof:shape", "roof:levels", "roof:height", "addr:housenumber",
    "addr:street", "addr:city", "addr:postcode", "addr:suburb",
    "addr:district", "addr:place", "addr:full", "colour", "facade:colour",
    "facade:material", "building:use", "building:architecture", "start_date",
    "architect", "shop", "amenity", "office", "tourism", "historic",
    "wikidata", "wikipedia", "website", "operator", "brand", "landuse",
)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def save_checkpoint(path: Path, report: dict[str, Any]) -> None:
    """Commit and push each processed tile and the current resumable report."""
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git("add", "--", str(path.relative_to(REPO_ROOT)), str(REPORT_PATH.relative_to(REPO_ROOT)))
    staged = git("diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        print(f"CHECKPOINT: no changes to commit for {path.relative_to(REPO_ROOT)}", flush=True)
        return
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("commit", "-m", f"Checkpoint Manila PBF enrichment: {path.stem}")
    pushed = git("push", "origin", "HEAD:main", check=False)
    if pushed.returncode:
        # A remote update should be rare because this workflow is serialized.
        print(pushed.stdout, file=sys.stderr, flush=True)
        raise RuntimeError("Checkpoint push failed; stopping rather than losing processed work.")
    print(f"CHECKPOINT PUSHED: {path.relative_to(REPO_ROOT)}", flush=True)


def labelled_osm_identity(props: dict[str, Any]) -> tuple[str, int] | None:
    for key in ("osm_id", "osm_way_id", "osm_wayid", "way_id"):
        value = props.get(key)
        if value in (None, ""):
            continue
        try:
            ident = int(str(value).strip())
        except (TypeError, ValueError):
            continue
        if ident > 0:
            return ("way", ident)
    return None


def tile_feature_center(path: Path, feature: dict[str, Any], extent: int) -> tuple[float, float] | None:
    """Approximate feature center from tile-local vertices; never changes geometry."""
    try:
        z, x, y = map(int, path.relative_to(TILES_ROOT).with_suffix("").parts[-3:])
        points: list[tuple[float, float]] = []

        def walk(value: Any) -> None:
            if isinstance(value, (list, tuple)):
                if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                    points.append((float(value[0]), float(value[1])))
                else:
                    for child in value:
                        walk(child)
        walk((feature.get("geometry") or {}).get("coordinates"))
        points = list(dict.fromkeys(points))
        if not points:
            return None
        px = sum(p[0] for p in points) / len(points)
        py = sum(p[1] for p in points) / len(points)
        n = 2 ** z
        lon = ((x + px / extent) / n) * 360.0 - 180.0
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
        return lat, lon
    except (ValueError, IndexError, TypeError):
        return None


def request_overpass(query: str) -> dict[str, Any] | None:
    for attempt in range(4):
        try:
            response = session.post(OVERPASS_URL, data={"data": query}, timeout=REQUEST_TIMEOUT)
            if response.status_code in (429, 502, 503, 504):
                raise requests.HTTPError(f"temporary Overpass HTTP {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else None
        except (requests.RequestException, ValueError) as exc:
            if attempt == 3:
                print(f"WARNING: Overpass request skipped after retries: {exc}", file=sys.stderr, flush=True)
            else:
                time.sleep(2 ** attempt)
    return None


def get_tags_by_id(identities: set[tuple[str, int]]) -> dict[tuple[str, int], dict[str, str]]:
    result: dict[tuple[str, int], dict[str, str]] = {}
    ids = sorted(ident for kind, ident in identities if kind == "way")
    for offset in range(0, len(ids), 40):
        batch = ids[offset:offset + 40]
        payload = request_overpass("[out:json][timeout:60];way(id:" + ",".join(map(str, batch)) + ");out tags;")
        if payload:
            for el in payload.get("elements", []):
                if el.get("type") == "way" and isinstance(el.get("tags"), dict):
                    result[("way", int(el["id"]))] = {str(k): str(v) for k, v in el["tags"].items()}
        time.sleep(0.5)
    return result


def coordinate_matches(points: list[tuple[str, float, float]]) -> dict[str, tuple[int, dict[str, str]]]:
    matched: dict[str, tuple[int, dict[str, str]]] = {}
    for offset in range(0, len(points), 8):
        batch = points[offset:offset + 8]
        clauses = [f'way(around:25,{lat:.7f},{lon:.7f})["building"];' for _, lat, lon in batch]
        payload = request_overpass("[out:json][timeout:60];(" + "".join(clauses) + ");out tags center;")
        candidates = []
        if payload:
            for el in payload.get("elements", []):
                center, tags = el.get("center") or {}, el.get("tags") or {}
                if el.get("type") == "way" and "lat" in center and "lon" in center and tags.get("building"):
                    candidates.append((int(el["id"]), float(center["lat"]), float(center["lon"]),
                                       {str(k): str(v) for k, v in tags.items()}))
        for key, lat, lon in batch:
            nearest = None
            for ident, olat, olon, tags in candidates:
                dy = (olat - lat) * 111320.0
                dx = (olon - lon) * 111320.0 * math.cos(math.radians(lat))
                distance = math.hypot(dx, dy)
                if nearest is None or distance < nearest[0]:
                    nearest = (distance, ident, tags)
            if nearest and nearest[0] <= 12.0:
                matched[key] = (nearest[1], nearest[2])
        time.sleep(0.5)
    return matched


def internal_number(path: Path, layer: str, idx: int) -> str:
    raw = f"{path.relative_to(TILES_ROOT)}|{layer}|{idx}"
    return "MAN-" + hashlib.sha1(raw.encode()).hexdigest()[:12].upper()


def process_tile(path: Path, report: dict[str, Any]) -> bool:
    try:
        decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
    except Exception as exc:
        report["decode_errors"] += 1
        report["last_error"] = f"{path.relative_to(REPO_ROOT)}: {exc}"
        print(f"WARNING: cannot decode {path.relative_to(REPO_ROOT)}: {exc}", flush=True)
        return False

    identities: set[tuple[str, int]] = set()
    points: list[tuple[str, float, float]] = []
    centers: dict[tuple[str, int], tuple[float, float]] = {}
    feature_count = 0
    for lname, layer in decoded.items():
        if str(lname).lower() not in ("building", "buildings"):
            continue
        for idx, feature in enumerate(layer.get("features", [])):
            feature_count += 1
            props = feature.get("properties") or {}
            identity = labelled_osm_identity(props)
            if identity:
                identities.add(identity)
            center = tile_feature_center(path, feature, int(layer.get("extent", 4096)))
            if center:
                key = (str(lname), idx)
                centers[key] = center
                if not identity:
                    points.append((f"{lname}|{idx}", center[0], center[1]))

    tags_by_id = get_tags_by_id(identities)
    tags_by_coordinate = coordinate_matches(points)
    tile_changed = False
    added = matched_count = unmatched_count = 0

    for lname, layer in decoded.items():
        if str(lname).lower() not in ("building", "buildings"):
            continue
        for idx, feature in enumerate(layer.get("features", [])):
            props = feature.get("properties")
            if not isinstance(props, dict):
                props = {}
                feature["properties"] = props
            identity = labelled_osm_identity(props)
            tags = tags_by_id.get(identity) if identity else None
            matched_id = identity[1] if tags and identity else None
            if not tags:
                coord = tags_by_coordinate.get(f"{lname}|{idx}")
                if coord:
                    matched_id, tags = coord

            def set_if_empty(key: str, value: Any) -> None:
                nonlocal added, tile_changed
                if value not in (None, "") and props.get(key) in (None, ""):
                    props[key] = value
                    added += 1
                    tile_changed = True

            set_if_empty("building_number", internal_number(path, str(lname), idx))
            if tags:
                matched_count += 1
                set_if_empty("osm_type", "way")
                set_if_empty("osm_id", str(matched_id))
                for tag in OSM_TAGS:
                    set_if_empty(tag, tags.get(tag))
                set_if_empty("building_name", tags.get("name") or tags.get("name:en") or tags.get("name:tl"))
                set_if_empty("building_uid", f"osm-way-{matched_id}")
            else:
                unmatched_count += 1
                uid = "tile-" + hashlib.sha1(f"{path.relative_to(TILES_ROOT)}|{lname}|{idx}".encode()).hexdigest()[:16]
                set_if_empty("building_uid", uid)
            set_if_empty("building_name", props.get("name"))

    report["tiles_processed"] += 1
    report["building_features_seen"] += feature_count
    report["coordinate_candidates"] += len(points)
    report["coordinate_osm_matches"] += len(tags_by_coordinate)
    report["verified_osm_id_matches"] += len(tags_by_id)
    report["features_with_osm_match"] += matched_count
    report["features_without_safe_osm_match"] += unmatched_count
    report["properties_added"] += added
    report["last_processed_tile"] = str(path.relative_to(REPO_ROOT))
    report["last_error"] = None

    if tile_changed:
        layer_list = [{"name": name, "features": layer.get("features", []),
                       "extent": layer.get("extent", 4096), "version": layer.get("version", 2)}
                      for name, layer in decoded.items()]
        encoded = mapbox_vector_tile.encode(layer_list, default_options={"y_coord_down": True})
        mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
        path.write_bytes(encoded)
        report["tiles_changed"] += 1
        print(f"UPDATED {path.relative_to(REPO_ROOT)}: +{added} properties; geometry unchanged", flush=True)
    else:
        print(f"CHECKED {path.relative_to(REPO_ROOT)}: no missing properties", flush=True)
    return tile_changed


def main() -> int:
    paths = sorted(p for p in TILES_ROOT.rglob("*.pbf") if p.is_file())
    if not paths:
        print(f"ERROR: no PBF tiles under {TILES_ROOT}", file=sys.stderr)
        return 2

    report: dict[str, Any] = {
        "status": "running", "tile_files_found": len(paths), "tiles_processed": 0,
        "tiles_changed": 0, "decode_errors": 0, "building_features_seen": 0,
        "coordinate_candidates": 0, "coordinate_osm_matches": 0,
        "verified_osm_id_matches": 0, "features_with_osm_match": 0,
        "features_without_safe_osm_match": 0, "properties_added": 0,
        "geometry_generated": False, "geometry_coordinates_intentionally_changed": False,
        "building_number_is_internal_id_not_address": True,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Starting incremental run: {len(paths)} PBF files; each changed tile is pushed immediately.", flush=True)

    for path in paths:
        process_tile(path, report)
        # Always checkpoint progress, even if a tile had no new attributes.
        save_checkpoint(path, report)

    report["status"] = "completed"
    report["completed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git("add", "--", str(REPORT_PATH.relative_to(REPO_ROOT)))
    staged = git("diff", "--cached", "--quiet", check=False)
    if staged.returncode:
        git("commit", "-m", "Finalize Manila PBF enrichment report")
        pushed = git("push", "origin", "HEAD:main", check=False)
        if pushed.returncode:
            print(pushed.stdout, file=sys.stderr, flush=True)
            return 3
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
