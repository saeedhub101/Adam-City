#!/usr/bin/env python3
"""Audit repository-local geotagged photos against local OSM building records.

This script never edits GLBs, generates facade textures, or downloads anything.
Its output is a candidate report only. A photo's GPS point is the camera position,
not proof of which facade it sees; camera heading and a visual identity check are
required before a photograph may be applied to a building.
"""
import gzip
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repository/middle east
PHOTOS = ROOT / "landmark-photos.json"
BUILDING_SOURCES = [
    ("Jordan", ROOT / "Jordan" / "layers" / "building_details.geojson.gz"),
    ("Palestine", ROOT / "Palestine" / "layers" / "building_details.geojson.gz"),
]
OUT = ROOT / "UnityGame" / "BuildData" / "photo-building-match-candidates.json"
START = (35.940358, 31.997579)  # Tabarbour, lon/lat
PHOTO_SEARCH_RADIUS_M = 150.0
MAX_CANDIDATES = 5


def haversine_m(lon1, lat1, lon2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def points_from_geometry(geometry):
    """Yield coordinate pairs from any common GeoJSON geometry."""
    if not geometry:
        return
    kind, coords = geometry.get("type"), geometry.get("coordinates") or []
    if kind == "Point":
        if len(coords) >= 2:
            yield coords[0], coords[1]
    elif kind in ("LineString", "MultiPoint"):
        for p in coords:
            if len(p) >= 2:
                yield p[0], p[1]
    elif kind in ("Polygon", "MultiLineString"):
        for ring in coords:
            for p in ring:
                if len(p) >= 2:
                    yield p[0], p[1]
    elif kind == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                for p in ring:
                    if len(p) >= 2:
                        yield p[0], p[1]
    elif kind == "GeometryCollection":
        for child in geometry.get("geometries") or []:
            yield from points_from_geometry(child)


def representative_point(geometry):
    pts = list(points_from_geometry(geometry))
    if not pts:
        return None
    # This is a fast representative point for candidate ranking only, not a surveyed centroid.
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def tile_path(area, lon, lat):
    if str(area).casefold() != "amman":
        return None
    x, y = math.floor(lon * 100), math.floor(lat * 100)
    return f"BuildGLB/amman/amman_{x}_{y}.glb"


def main():
    missing = [str(path) for _, path in BUILDING_SOURCES if not path.exists()]
    if not PHOTOS.exists() or missing:
        raise FileNotFoundError(
            f"Required repository-local inputs missing: {PHOTOS}; building layers missing: {missing}"
        )

    with PHOTOS.open(encoding="utf-8") as f:
        photo_data = json.load(f)
    photos = []
    for feature in photo_data.get("features", []):
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coords) < 2:
            continue
        props = feature.get("properties") or {}
        lon, lat = float(coords[0]), float(coords[1])
        photos.append({
            "name": props.get("name", ""),
            "description": props.get("description", ""),
            "area": props.get("area", ""),
            "image": props.get("image", ""),
            "license": props.get("license", ""),
            "artist": props.get("artist", ""),
            "lon": lon,
            "lat": lat,
            "distance_from_tabarbour_m": round(haversine_m(START[0], START[1], lon, lat), 1),
            "nearby_glb_tile": tile_path(props.get("area", ""), lon, lat),
            "candidates": [],
            "status": "candidate_only_no_camera_heading_or_visual_identity_check",
        })

    # Grid-index buildings so only nearby candidates need distance checks.
    cell_deg = 0.002
    grid = {}
    building_count = 0
    for region, source_path in BUILDING_SOURCES:
        with gzip.open(source_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        for feature in data.get("features", []):
            geometry = feature.get("geometry")
            point = representative_point(geometry)
            if not point:
                continue
            lon, lat = point
            props = feature.get("properties") or {}
            item = {
                "region": region,
                "id": str(feature.get("id", props.get("@id", props.get("osm_id", "")))),
                "name": str(props.get("name") or props.get("name:en") or ""),
                "building": str(props.get("building", "")),
                "lon": lon,
                "lat": lat,
            }
            key = (math.floor(lon / cell_deg), math.floor(lat / cell_deg))
            grid.setdefault(key, []).append(item)
            building_count += 1

    for photo in photos:
        gx, gy = math.floor(photo["lon"] / cell_deg), math.floor(photo["lat"] / cell_deg)
        candidates = []
        # Search roughly 150 m around each photo, with a small safety margin.
        for dx in range(-8, 9):
            for dy in range(-8, 9):
                for b in grid.get((gx + dx, gy + dy), []):
                    distance = haversine_m(photo["lon"], photo["lat"], b["lon"], b["lat"])
                    if distance <= PHOTO_SEARCH_RADIUS_M:
                        candidates.append({
                            **b,
                            "camera_to_building_distance_m": round(distance, 1),
                            "same_name_hint": bool(
                                photo["name"] and b["name"]
                                and photo["name"].casefold() in b["name"].casefold()
                            ),
                        })
        candidates.sort(key=lambda x: (not x["same_name_hint"], x["camera_to_building_distance_m"]))
        photo["candidates"] = candidates[:MAX_CANDIDATES]

    result = {
        "policy": "offline_repository_assets_only",
        "purpose": "candidate audit; not automatic photo-to-facade assignment",
        "photo_count": len(photos),
        "building_records_indexed": building_count,
        "tabarbour_origin": {"lon": START[0], "lat": START[1]},
        "photo_search_radius_m": PHOTO_SEARCH_RADIUS_M,
        "important_limit": (
            "GPS identifies the photo camera position, not the facade direction. "
            "Do not texture a building unless the facade is visually identified and "
            "camera heading/perspective is understood. This report never changes a GLB."
        ),
        "photos": sorted(photos, key=lambda p: p["distance_from_tabarbour_m"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}: {len(photos)} photos, {building_count} building records indexed.")


if __name__ == "__main__":
    main()
