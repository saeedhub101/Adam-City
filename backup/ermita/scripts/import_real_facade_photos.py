#!/usr/bin/env python3
"""Download public KartaView street-level photos near Ermita buildings.

Images are real street photographs, not automatically reconstructed wall textures.
Each match includes distance and heading checks so nearby photos are not presented
as verified facade views without supporting geometry.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
BUILDINGS_FILE = ROOT / "ermita/maps/generated/ermita-building-footprints.geojson"
OUT_DIR = ROOT / "ermita/facades/generated"
IMAGE_DIR = ROOT / "ermita/facades/images"
CSV_FILE = OUT_DIR / "ermita-real-facade-images.csv"
REPORT_FILE = OUT_DIR / "ermita-real-facade-report.json"
API = "https://api.openstreetcam.org/2.0/photo/"
USER_AGENT = "Adam-City-Ermita-Facade-Importer/1.0 (open mapping research)"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_LONLAT = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
MAX_API_CELLS = 120
MAX_IMAGES = 250
MAX_DISTANCE_M = 45.0
MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
TIMEOUT = (15, 45)


def first(record, *keys):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return ""


def photo_rows(payload):
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    if isinstance(result, dict):
        rows = result.get("data") or result.get("photos") or []
        if isinstance(rows, list):
            return rows
    rows = payload.get("data") or payload.get("photos") or []
    return rows if isinstance(rows, list) else []


def photo_id(row):
    return str(first(row, "id", "photoId", "photo_id", "photoID"))


def image_url(row):
    value = first(row, "photoUrl", "photo_url", "imageUrl", "image_url",
                  "thumbUrl", "thumb_url", "url")
    if isinstance(value, dict):
        value = first(value, "url", "href", "src")
    if isinstance(value, str) and value.startswith("https://"):
        return value
    return ""


def parse_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def bearing_deg(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angle_delta(a, b):
    return abs((a - b + 180) % 360 - 180)


def fetch_cell(session, lat, lon):
    params = {
        "lat": lat, "lng": lon, "radius": 220, "zoomLevel": 18,
        "join": "sequence", "orderBy": "id", "orderDirection": "desc",
        "itemsPerPage": 100,
    }
    response = session.get(API, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return photo_rows(response.json())


def download_image(session, url, destination):
    if not url or urlparse(url).scheme != "https":
        return False, "no_public_image_url"
    try:
        with session.get(url, stream=True, timeout=TIMEOUT) as response:
            response.raise_for_status()
            ctype = response.headers.get("Content-Type", "").lower()
            if not ctype.startswith("image/"):
                return False, "response_not_image"
            length = parse_float(response.headers.get("Content-Length"))
            if length and length > MAX_DOWNLOAD_BYTES:
                return False, "image_too_large"
            data = bytearray()
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                data.extend(chunk)
                if len(data) > MAX_DOWNLOAD_BYTES:
                    return False, "image_too_large"
        # Preserve original bytes. Source images are CC BY-SA 4.0; attribution is
        # recorded in the CSV and report. No fabricated facade textures are created.
        suffix = ".jpg"
        if "png" in ctype:
            suffix = ".png"
        elif "webp" in ctype:
            suffix = ".webp"
        destination = destination.with_suffix(suffix)
        destination.write_bytes(data)
        return True, str(destination.relative_to(ROOT))
    except Exception as exc:
        return False, "download_error:" + str(exc)[:180]


def main():
    if not BUILDINGS_FILE.exists():
        raise FileNotFoundError(f"Missing {BUILDINGS_FILE}; run the OSM import first")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    collection = json.loads(BUILDINGS_FILE.read_text(encoding="utf-8"))
    buildings = []
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for feature in collection.get("features", []):
        try:
            geom = geom_transform(TO_METERS, shape(feature["geometry"]))
            polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms) if geom.geom_type == "MultiPolygon" else []
            props = feature.get("properties") or {}
            tags = props.get("tags") if isinstance(props.get("tags"), dict) else props
            for poly in polys:
                if poly.is_empty or not poly.is_valid or poly.area < 12:
                    continue
                minx, miny, maxx, maxy = min(minx, poly.bounds[0]), min(miny, poly.bounds[1]), max(maxx, poly.bounds[2]), max(maxy, poly.bounds[3])
                buildings.append({
                    "poly": poly,
                    "id": str(props.get("osm_feature_id") or f"{props.get('type','way')}/{props.get('id','unknown')}"),
                    "name": first(tags, "name", "brand", "addr:housenumber"),
                })
        except Exception as exc:
            print(f"Skipping invalid footprint: {exc}")
    if not buildings:
        raise RuntimeError("No valid building polygons found")

    # Query a bounded 300 m grid instead of issuing thousands of per-building calls.
    step = 300.0
    xs = []
    x = minx + step / 2
    while x <= maxx and len(xs) < MAX_API_CELLS:
        xs.append(x)
        x += step
    ys = []
    y = miny + step / 2
    while y <= maxy and len(ys) < MAX_API_CELLS:
        ys.append(y)
        y += step
    cells = [(x, y) for x in xs for y in ys]
    if len(cells) > MAX_API_CELLS:
        stride = math.ceil(len(cells) / MAX_API_CELLS)
        cells = cells[::stride][:MAX_API_CELLS]

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    candidates = {}
    errors = []
    for index, (x, y) in enumerate(cells, 1):
        lon, lat = TO_LONLAT(x, y)
        try:
            for row in fetch_cell(session, lat, lon):
                pid = photo_id(row)
                if pid and pid not in candidates:
                    candidates[pid] = row
        except Exception as exc:
            errors.append({"cell": index, "error": str(exc)[:200]})
        time.sleep(0.15)

    matches = []
    for pid, row in candidates.items():
        lat = parse_float(first(row, "lat", "latitude", "gpsLatitude"))
        lon = parse_float(first(row, "lng", "lon", "longitude", "gpsLongitude"))
        if lat is None or lon is None:
            continue
        point = Point(*TO_METERS(lon, lat))
        heading = parse_float(first(row, "heading", "gpsHeading", "bearing", "cameraHeading"))
        best = None
        for building in buildings:
            poly = building["poly"]
            distance = point.distance(poly.boundary)
            if distance > MAX_DISTANCE_M:
                continue
            wall_point = poly.boundary.interpolate(poly.boundary.project(point))
            wall_lon, wall_lat = TO_LONLAT(wall_point.x, wall_point.y)
            wanted = bearing_deg(lat, lon, wall_lat, wall_lon)
            delta = angle_delta(heading, wanted) if heading is not None else None
            # When a heading exists, require the camera to face roughly toward the wall.
            if delta is not None and delta > 60:
                continue
            score = distance + (delta * 0.2 if delta is not None else 8.0)
            if best is None or score < best["score"]:
                best = {
                    "building": building, "distance": distance,
                    "heading_delta": delta, "score": score,
                }
        if best is None:
            continue
        url = image_url(row)
        matches.append({
            "photo_id": pid, "row": row, "lat": lat, "lon": lon,
            "heading": heading, "url": url, **best,
        })

    matches.sort(key=lambda item: item["score"])
    matches = matches[:MAX_IMAGES]
    output_rows = []
    downloaded = 0
    for item in matches:
        row = item["row"]
        pid = item["photo_id"]
        saved_path = ""
        status = "metadata_only"
        if item["url"]:
            safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", pid)[:80] or "photo"
            ok, result = download_image(session, item["url"], IMAGE_DIR / f"{safe_id}.jpg")
            if ok:
                downloaded += 1
                saved_path = result
                status = "downloaded"
            else:
                status = result
        seq = first(row, "sequenceId", "sequence_id", "sequenceID")
        timestamp = first(row, "shotDate", "dateAdded", "date_added", "capturedAt", "timestamp")
        delta = item["heading_delta"]
        output_rows.append({
            "photo_id": pid,
            "building_osm_id": item["building"]["id"],
            "building_name": item["building"]["name"],
            "distance_to_building_wall_m": round(item["distance"], 2),
            "camera_heading_deg": item["heading"] if item["heading"] is not None else "",
            "heading_difference_deg": round(delta, 1) if delta is not None else "",
            "match_status": "direction_checked" if delta is not None else "nearby_not_direction_verified",
            "latitude": item["lat"], "longitude": item["lon"],
            "capture_date": timestamp, "sequence_id": seq,
            "image_url": item["url"],
            "local_image": saved_path, "download_status": status,
            "source": "KartaView / © Grab and KartaView Contributors",
            "license": "CC BY-SA 4.0",
            "source_page": f"https://kartaview.org/map/@{item['lat']},{item['lon']},18z",
        })

    fields = [
        "photo_id", "building_osm_id", "building_name", "distance_to_building_wall_m",
        "camera_heading_deg", "heading_difference_deg", "match_status", "latitude",
        "longitude", "capture_date", "sequence_id", "image_url", "local_image",
        "download_status", "source", "license", "source_page",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    report = {
        "status": "success",
        "area": "Ermita, Manila, Philippines",
        "source": "KartaView public street-level imagery API",
        "source_terms": "https://kartaview.org/terms",
        "image_license": "CC BY-SA 4.0",
        "attribution_required": "© Grab and KartaView Contributors",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "buildings_checked": len(buildings),
        "grid_cells_queried": len(cells),
        "unique_api_photos_found": len(candidates),
        "photos_matched_to_buildings": len(output_rows),
        "photos_downloaded": downloaded,
        "api_errors": errors,
        "csv": str(CSV_FILE.relative_to(ROOT)),
        "image_directory": str(IMAGE_DIR.relative_to(ROOT)),
        "limitations": [
            "Coverage depends on publicly available KartaView imagery; an empty result means no matching public images were found by this search.",
            "A nearby photo is not proof of an exact facade match; the CSV records distance and heading-check status.",
            "Street photographs are not automatically UV-mapped onto 3D building walls. Accurate facade texturing requires camera calibration and multi-view reconstruction.",
            "Images retain their KartaView CC BY-SA 4.0 license and required attribution."
        ],
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
