#!/usr/bin/env python3
"""Enrich existing Manila vector-tile building attributes from authoritative OSM tags.

This script deliberately does NOT create geometry, move features, invent facade details,
or modify manila.html. It only fills missing building properties when a tile feature has
an explicit OSM way ID and the live OSM API returns tags for that exact way.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import mapbox_vector_tile
import requests

ROOT = Path(__file__).resolve().parents[1]
TILES_ROOT = ROOT / "vector-tiles"
OVERPASS_URL = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
USER_AGENT = "Adam-City-Manila-PBF-Enrichment/1.1 (open-source map data enrichment with coordinate matching)"
BATCH_SIZE = 60
REQUEST_TIMEOUT = 90

# Only factual OSM tags; no inferred/random facade geometry or appearance.
OSM_TAGS = (
    "name",
    "building",
    "building:levels",
    "building:levels:underground",
    "height",
    "min_height",
    "building:colour",
    "building:material",
    "roof:colour",
    "roof:material",
    "roof:shape",
    "roof:levels",
    "roof:height",
    "addr:housenumber",
    "addr:street",
    "addr:city",
    "shop",
    "amenity",
    "office",
    "tourism",
    "historic",
    "wikidata",
    "wikipedia",
)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


def explicit_osm_way_id(properties: dict[str, Any], feature_id: Any = None) -> int | None:
    """Get a labelled OSM way ID, or test the vector feature ID against live OSM.

    Feature IDs are treated only as candidates: they are enriched only if Overpass
    confirms that the exact numeric ID is an existing OSM way.
    """
    for key in ("osm_id", "osm_way_id", "osm_wayid", "way_id"):
        value = properties.get(key)
        if value is None:
            continue
        try:
            value = int(str(value).strip())
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    try:
        candidate = int(str(feature_id).strip())
    except (TypeError, ValueError):
        return None
    return candidate if candidate > 0 else None


def get_osm_tags(ids: list[int]) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    unique_ids = sorted(set(ids))
    for offset in range(0, len(unique_ids), BATCH_SIZE):
        batch = unique_ids[offset:offset + BATCH_SIZE]
        query = "[out:json][timeout:75];way(id:" + ",".join(map(str, batch)) + ");out tags;"
        for attempt in range(4):
            try:
                response = session.post(
                    OVERPASS_URL,
                    data={"data": query},
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code in (429, 502, 503, 504):
                    raise requests.HTTPError(f"temporary Overpass HTTP {response.status_code}")
                response.raise_for_status()
                payload = response.json()
                for element in payload.get("elements", []):
                    if element.get("type") == "way" and isinstance(element.get("tags"), dict):
                        result[int(element["id"])] = {
                            str(k): str(v) for k, v in element["tags"].items()
                        }
                break
            except (requests.RequestException, ValueError) as exc:
                if attempt == 3:
                    print(f"WARNING: Overpass batch skipped after retries: {exc}", file=sys.stderr)
                else:
                    time.sleep(2 ** attempt)
        # Be polite to the public Overpass instance.
        time.sleep(1.2)
    return result


def tile_feature_center(path: Path, feature: dict[str, Any], extent: int) -> tuple[float, float] | None:
    """Convert a vector-tile polygon center to WGS84 using its z/x/y path."""
    try:
        z, x, y = map(int, path.relative_to(TILES_ROOT).with_suffix("").parts[-3:])
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates")
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
        # Average unique vertices so repeated ring closure doesn't bias the center.
        points = list(dict.fromkeys(points))
        px = sum(p[0] for p in points) / len(points)
        py = sum(p[1] for p in points) / len(points)
        n = 2 ** z
        lon = ((x + px / extent) / n) * 360.0 - 180.0
        import math
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
        return lat, lon
    except (ValueError, IndexError, TypeError):
        return None


def get_nearby_osm_tags(points: list[tuple[str, float, float]]) -> dict[str, dict[str, str]]:
    """Match unmatched tile features to nearby real OSM building ways by geographic position."""
    matched: dict[str, dict[str, str]] = {}
    # A small radius and a nearest-center threshold prevent broad, speculative matches.
    batch_size = 12
    for offset in range(0, len(points), batch_size):
        batch = points[offset:offset + batch_size]
        clauses = []
        for _, lat, lon in batch:
            clauses.append(f'way(around:18,{lat:.7f},{lon:.7f})["building"];')
        query = "[out:json][timeout:75];(" + "".join(clauses) + ");out tags center;"
        payload = None
        for attempt in range(4):
            try:
                response = session.post(OVERPASS_URL, data={"data": query}, timeout=REQUEST_TIMEOUT)
                if response.status_code in (429, 502, 503, 504):
                    raise requests.HTTPError(f"temporary Overpass HTTP {response.status_code}")
                response.raise_for_status()
                payload = response.json()
                break
            except (requests.RequestException, ValueError) as exc:
                if attempt == 3:
                    print(f"WARNING: coordinate batch skipped after retries: {exc}", file=sys.stderr)
                else:
                    time.sleep(2 ** attempt)
        if payload is None:
            continue
        candidates = []
        for element in payload.get("elements", []):
            center = element.get("center") or {}
            tags = element.get("tags") or {}
            if element.get("type") == "way" and "lat" in center and "lon" in center and tags.get("building"):
                candidates.append((float(center["lat"]), float(center["lon"]), {str(k): str(v) for k, v in tags.items()}))
        for key, lat, lon in batch:
            nearest = None
            for olat, olon, tags in candidates:
                # Equirectangular distance is sufficiently accurate at Manila's latitude.
                import math
                dy = (olat - lat) * 111320.0
                dx = (olon - lon) * 111320.0 * math.cos(math.radians(lat))
                distance = math.hypot(dx, dy)
                if nearest is None or distance < nearest[0]:
                    nearest = (distance, tags)
            if nearest and nearest[0] <= 10.0:
                matched[key] = nearest[1]
        time.sleep(1.2)
    return matched


def iter_pbf_files() -> list[Path]:
    return sorted(p for p in TILES_ROOT.rglob("*.pbf") if p.is_file())


def main() -> int:
    if not TILES_ROOT.is_dir():
        print(f"ERROR: tile directory not found: {TILES_ROOT}", file=sys.stderr)
        return 2

    paths = iter_pbf_files()
    if not paths:
        print(f"ERROR: no .pbf tiles found under {TILES_ROOT}", file=sys.stderr)
        return 2

    # Decode once to collect explicitly keyed OSM way IDs, then fetch tags in batches.
    decoded_tiles: dict[Path, dict[str, Any]] = {}
    ids_by_tile: dict[Path, set[int]] = {}
    all_ids: set[int] = set()
    decode_errors = 0

    for path in paths:
        try:
            decoded = mapbox_vector_tile.decode(
                path.read_bytes(),
                default_options={"y_coord_down": True},
            )
            decoded_tiles[path] = decoded
            tile_ids: set[int] = set()
            for layer_name, layer in decoded.items():
                layer_name = str(layer_name).lower()
                if layer_name not in ("building", "buildings"):
                    continue
                for feature in layer.get("features", []):
                    props = feature.get("properties") or {}
                    osm_id = explicit_osm_way_id(props, feature.get("id"))
                    if osm_id is not None:
                        tile_ids.add(osm_id)
            ids_by_tile[path] = tile_ids
            all_ids.update(tile_ids)
        except Exception as exc:
            decode_errors += 1
            print(f"WARNING: cannot decode {path.relative_to(ROOT)}: {exc}", file=sys.stderr)

    print(
        f"Tiles found: {len(paths)}; decoded: {len(decoded_tiles)}; "
        f"decode errors: {decode_errors}; explicit OSM way IDs: {len(all_ids)}"
    )
    if not all_ids:
        print(
            "No numeric OSM candidate IDs were found on building features. "
            "For safety, no tiles will be rewritten."
        )
        return 0

    osm_tags = get_osm_tags(list(all_ids))
    print(f"OSM ways with tags retrieved: {len(osm_tags)}")

    changed_files = 0
    changed_features = 0
    added_properties = 0
    missing_osm = 0

    for path, decoded in decoded_tiles.items():
        tile_changed = False
        for layer_name, layer in decoded.items():
            if str(layer_name).lower() not in ("building", "buildings"):
                continue
            for feature in layer.get("features", []):
                props = feature.get("properties")
                if not isinstance(props, dict):
                    continue
                osm_id = explicit_osm_way_id(props, feature.get("id"))
                if osm_id is None:
                    continue
                tags = osm_tags.get(osm_id)
                if not tags:
                    missing_osm += 1
                    continue
                feature_added = 0
                for key in OSM_TAGS:
                    value = tags.get(key)
                    if value is None or value == "":
                        continue
                    # Never overwrite existing tile data; only fill absent/empty fields.
                    if props.get(key) is None or props.get(key) == "":
                        props[key] = value
                        feature_added += 1
                if feature_added:
                    tile_changed = True
                    changed_features += 1
                    added_properties += feature_added

        if tile_changed:
            # Re-encode all original layers; geometry and tile-local coordinates are preserved.
            layer_list = []
            for layer_name, layer in decoded.items():
                layer_list.append({
                    "name": layer_name,
                    "features": layer.get("features", []),
                    "extent": layer.get("extent", 4096),
                    "version": layer.get("version", 2),
                })
            encoded = mapbox_vector_tile.encode(
                layer_list,
                default_options={"y_coord_down": True},
            )
            # Ensure the new PBF can be decoded before replacing the original.
            mapbox_vector_tile.decode(encoded, default_options={"y_coord_down": True})
            path.write_bytes(encoded)
            changed_files += 1
            print(f"UPDATED {path.relative_to(ROOT)}")

    summary = {
        "tile_files_found": len(paths),
        "tiles_decoded": len(decoded_tiles),
        "decode_errors": decode_errors,
        "explicit_osm_way_ids": len(all_ids),
        "osm_ways_with_tags_by_id": len(osm_tags),\n        "features_checked_by_coordinates": len(coordinate_points),\n        "nearby_osm_matches_by_coordinates": len(nearby_tags),
        "features_enriched": changed_features,
        "properties_added": added_properties,
        "tiles_changed": changed_files,
        "features_without_live_osm_match": missing_osm,
        "geometry_generated": False,
        "geometry_coordinates_intentionally_changed": False,
    }
    report_path = ROOT / "pbf-enrichment-report.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
