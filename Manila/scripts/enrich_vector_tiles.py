#!/usr/bin/env python3
"""Enrich Manila vector-tile building properties from verified OpenStreetMap data.

Keeps all original geometries and coordinates unchanged. Adds stable internal building
numbers, explicit OSM identity fields, and only factual tags returned by OSM.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Any

import mapbox_vector_tile
import requests

ROOT = Path(__file__).resolve().parents[1]
TILES_ROOT = ROOT / "vector-tiles"
OVERPASS_URL = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
USER_AGENT = "Adam-City-Manila-PBF-Enrichment/1.2 (OSM coordinate matching)"
REQUEST_TIMEOUT = 90

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
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


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
    """Convert a tile-local geometry's vertex average into WGS84 using z/x/y."""
    try:
        z, x, y = map(int, path.relative_to(TILES_ROOT).with_suffix("").parts[-3:])
        coords = (feature.get("geometry") or {}).get("coordinates")
        points: list[tuple[float, float]] = []

        def walk(value: Any) -> None:
            if isinstance(value, (list, tuple)):
                if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                    points.append((float(value[0]), float(value[1])))
                else:
                    for child in value:
                        walk(child)
        walk(coords)
        if not points:
            return None
        points = list(dict.fromkeys(points))
        px = sum(p[0] for p in points) / len(points)
        py = sum(p[1] for p in points) / len(points)
        n = 2 ** z
        lon = ((x + px / extent) / n) * 360.0 - 180.0
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
        return lat, lon
    except (ValueError, IndexError, TypeError):
        return None


def get_tags_by_id(identities: set[tuple[str, int]]) -> dict[tuple[str, int], dict[str, str]]:
    result: dict[tuple[str, int], dict[str, str]] = {}
    ids = sorted(ident for kind, ident in identities if kind == "way")
    for offset in range(0, len(ids), 40):
        batch = ids[offset:offset + 40]
        if not batch:
            continue
        query = "[out:json][timeout:60];way(id:" + ",".join(map(str, batch)) + ");out tags;"
        payload = request_overpass(query)
        if payload:
            for el in payload.get("elements", []):
                if el.get("type") == "way" and isinstance(el.get("tags"), dict):
                    result[("way", int(el["id"]))] = {str(k): str(v) for k, v in el["tags"].items()}
        time.sleep(1.0)
    return result


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
                print(f"WARNING: Overpass request skipped after retries: {exc}", file=sys.stderr)
            else:
                time.sleep(2 ** attempt)
    return None


def coordinate_matches(points: list[tuple[str, float, float]]) -> dict[str, tuple[int, dict[str, str]]]:
    """Match a tile feature to a nearby real OSM building way, with a tight distance gate."""
    matched: dict[str, tuple[int, dict[str, str]]] = {}
    # Batch nearby searches to reduce API calls while still checking every feature position.
    for offset in range(0, len(points), 8):
        batch = points[offset:offset + 8]
        clauses = [f'way(around:25,{lat:.7f},{lon:.7f})["building"];' for _, lat, lon in batch]
        payload = request_overpass("[out:json][timeout:60];(" + "".join(clauses) + ");out tags center;")
        candidates: list[tuple[int, float, float, dict[str, str]]] = []
        if payload:
            for el in payload.get("elements", []):
                center = el.get("center") or {}
                tags = el.get("tags") or {}
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
            # Do not attach metadata to a distant or ambiguous building.
            if nearest and nearest[0] <= 12.0:
                matched[key] = (nearest[1], nearest[2])
        time.sleep(1.0)
    return matched


def iter_pbf_files() -> list[Path]:
    return sorted(p for p in TILES_ROOT.rglob("*.pbf") if p.is_file())


def main() -> int:
    paths = iter_pbf_files()
    if not paths:
        print(f"ERROR: no PBF tiles under {TILES_ROOT}", file=sys.stderr)
        return 2

    decoded_tiles: dict[Path, dict[str, Any]] = {}
    feature_points: dict[tuple[Path, str, int], tuple[float, float]] = {}
    labelled_ids: set[tuple[str, int]] = set()
    decode_errors = 0
    total_buildings = 0

    for path in paths:
        try:
            decoded = mapbox_vector_tile.decode(path.read_bytes(), default_options={"y_coord_down": True})
            decoded_tiles[path] = decoded
            for lname, layer in decoded.items():
                if str(lname).lower() not in ("building", "buildings"):
                    continue
                for idx, feature in enumerate(layer.get("features", [])):
                    total_buildings += 1
                    props = feature.get("properties") or {}
                    identity = labelled_osm_identity(props)
                    if identity:
                        labelled_ids.add(identity)
                    center = tile_feature_center(path, feature, int(layer.get("extent", 4096)))
                    if center:
                        feature_points[(path, str(lname), idx)] = center
        except Exception as exc:
            decode_errors += 1
            print(f"WARNING: cannot decode {path.relative_to(ROOT)}: {exc}", file=sys.stderr)

    print(f"Tiles found={len(paths)} decoded={len(decoded_tiles)} decode_errors={decode_errors} building_features={total_buildings}")
    tags_by_id = get_tags_by_id(labelled_ids)
    points_for_lookup = []
    for key, (lat, lon) in feature_points.items():
        path, lname, idx = key
        feature = decoded_tiles[path][lname]["features"][idx]
        props = feature.get("properties") or {}
        if not labelled_osm_identity(props):
            points_for_lookup.append((f"{path.relative_to(ROOT)}|{lname}|{idx}", lat, lon))
    tags_by_coordinate = coordinate_matches(points_for_lookup)
    print(f"Labelled OSM IDs={len(labelled_ids)} verified ID matches={len(tags_by_id)} coordinate candidates={len(points_for_lookup)} coordinate matches={len(tags_by_coordinate)}")

    changed_files = changed_features = properties_added = missing = 0
    for path, decoded in decoded_tiles.items():
        tile_changed = False
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
                matched_id = identity[1] if identity else None
                if not tags:
                    key = f"{path.relative_to(ROOT)}|{lname}|{idx}"
                    coordinate_result = tags_by_coordinate.get(key)
                    if coordinate_result:
                        matched_id, tags = coordinate_result
                if tags:
                    # Add traceable identity fields; never overwrite existing non-empty data.
                    if props.get("osm_type") in (None, ""):
                        props["osm_type"] = "way"
                        properties_added += 1
                        tile_changed = True
                    if props.get("osm_id") in (None, ""):
                        props["osm_id"] = str(matched_id)
                        properties_added += 1
                        tile_changed = True
                    for key in OSM_TAGS:
                        value = tags.get(key)
                        if value not in (None, "") and props.get(key) in (None, ""):
                            props[key] = value
                            properties_added += 1
                            tile_changed = True
                    # Keep a convenient explicit display name when the source actually names it.
                    display_name = tags.get("name") or tags.get("name:en") or tags.get("name:tl")
                    if display_name and props.get("building_name") in (None, ""):
                        props["building_name"] = display_name
                        properties_added += 1
                        tile_changed = True
                    if props.get("building_number") in (None, ""):
                        # This is a stable internal identifier, not a fabricated street address.
                        rel = str(path.relative_to(TILES_ROOT))
                        raw = f"{rel}|{lname}|{idx}"
                        props["building_number"] = "MAN-" + hashlib.sha1(raw.encode()).hexdigest()[:12].upper()
                        properties_added += 1
                        tile_changed = True
                    if props.get("building_uid") in (None, ""):
                        props["building_uid"] = f"osm-way-{matched_id}"
                        properties_added += 1
                        tile_changed = True
                    changed_features += 1
                else:
                    missing += 1
                    # Give every building a stable local number, even when OSM has no safe match.
                    if props.get("building_number") in (None, ""):
                        rel = str(path.relative_to(TILES_ROOT))
                        raw = f"{rel}|{lname}|{idx}"
                        props["building_number"] = "MAN-" + hashlib.sha1(raw.encode()).hexdigest()[:12].upper()
                        properties_added += 1
                        tile_changed = True
                    if props.get("building_uid") in (None, ""):
                        rel = str(path.relative_to(TILES_ROOT))
                        props["building_uid"] = "tile-" + hashlib.sha1(f"{rel}|{lname}|{idx}".encode()).hexdigest()[:16]
                        properties_added += 1
                        tile_changed = True
                # Keep an explicit display name property if an existing name is present.
                if props.get("building_name") in (None, "") and props.get("name") not in (None, ""):
                    props["building_name"] = str(props["name"])
                    properties_added += 1
                    tile_changed = True
                if tile_changed:
                    changed_features += 0

        if tile_changed:
            layer_list = [{"name": name, "features": layer.get("features", []),
                           "extent": layer.get("extent", 4096), "version": layer.get("version", 2)}
                          for name, layer in decoded.items()]
            encoded = mapbox_vector_tile.encode(layer_list, default_options={"y_coord_down": True})
            mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
            path.write_bytes(encoded)
            changed_files += 1
            print(f"UPDATED {path.relative_to(ROOT)}")

    report = {
        "tile_files_found": len(paths), "tiles_decoded": len(decoded_tiles),
        "decode_errors": decode_errors, "building_features_seen": total_buildings,
        "labelled_osm_ids": len(labelled_ids), "verified_osm_id_matches": len(tags_by_id),
        "coordinate_candidates": len(points_for_lookup), "coordinate_osm_matches": len(tags_by_coordinate),
        "features_without_safe_osm_match": missing, "features_processed_with_osm_data": changed_features,
        "properties_added": properties_added, "tiles_changed": changed_files,
        "geometry_generated": False, "geometry_coordinates_intentionally_changed": False,
        "building_number_is_internal_id_not_address": True,
    }
    (ROOT / "pbf-enrichment-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
