#!/usr/bin/env python3
"""Incrementally import KartaView street-imagery metadata for Ermita, without downloading images."""
from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
BUILDINGS_FILE = ROOT / "ermita/maps/generated/ermita-building-footprints.geojson"
OUT_DIR = ROOT / "kartaview"
PHOTOS_CSV = OUT_DIR / "ermita-street-imagery-metadata.csv"
PHOTOS_GEOJSON = OUT_DIR / "ermita-street-imagery-metadata.geojson"
SEQUENCES_CSV = OUT_DIR / "ermita-street-imagery-sequences.csv"
REPORT_FILE = OUT_DIR / "ermita-street-imagery-metadata-report.json"
API = "https://api.openstreetcam.org/2.0/photo/"
USER_AGENT = "Adam-City-Ermita-KartaView-Metadata/1.0 (open mapping research)"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_LONLAT = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
MAX_API_CELLS = 120
CELL_STEP_M = 300.0
TIMEOUT = (15, 45)

PHOTO_FIELDS = [
    "photo_id", "sequence_id", "sequence_index", "latitude", "longitude",
    "camera_heading_deg", "capture_date", "date_added", "date_processed",
    "field_of_view_deg", "projection", "gps_accuracy_m", "osm_way_id",
    "image_processing_status", "image_processing_result", "sequence_device",
    "sequence_date_added", "sequence_distance_km", "sequence_field_of_view_deg",
    "sequence_nw_lat", "sequence_nw_lon", "sequence_se_lat", "sequence_se_lon",
    "source_page", "metadata_source",
]


def first(record, *keys):
    for key in keys:
        value = record.get(key) if isinstance(record, dict) else None
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


def read_existing():
    rows = {}
    if PHOTOS_CSV.exists():
        with PHOTOS_CSV.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                pid = str(row.get("photo_id", "")).strip()
                if pid:
                    rows[pid] = row
    return rows


def query_metadata(session, lat, lon):
    params = {
        "lat": lat, "lng": lon, "radius": 220, "zoomLevel": 18,
        "join": "sequence", "orderBy": "id", "orderDirection": "desc",
        "itemsPerPage": 100,
    }
    response = session.get(API, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return photo_rows(response.json())


def main():
    if not BUILDINGS_FILE.exists():
        raise FileNotFoundError(f"Missing {BUILDINGS_FILE}; run the OSM import first")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    buildings = json.loads(BUILDINGS_FILE.read_text(encoding="utf-8")).get("features", [])
    bounds = []
    for feature in buildings:
        try:
            geom = shape(feature["geometry"])
            if not geom.is_empty:
                bounds.append(geom.bounds)
        except Exception:
            continue
    if not bounds:
        raise RuntimeError("No valid building footprints found to define the Ermita search area")

    min_lon = min(b[0] for b in bounds)
    min_lat = min(b[1] for b in bounds)
    max_lon = max(b[2] for b in bounds)
    max_lat = max(b[3] for b in bounds)
    minx, miny = TO_METERS(min_lon, min_lat)
    maxx, maxy = TO_METERS(max_lon, max_lat)
    xs, ys = [], []
    x = minx + CELL_STEP_M / 2
    while x <= maxx and len(xs) < MAX_API_CELLS:
        xs.append(x)
        x += CELL_STEP_M
    y = miny + CELL_STEP_M / 2
    while y <= maxy and len(ys) < MAX_API_CELLS:
        ys.append(y)
        y += CELL_STEP_M
    cells = [(x, y) for x in xs for y in ys]
    if len(cells) > MAX_API_CELLS:
        stride = math.ceil(len(cells) / MAX_API_CELLS)
        cells = cells[::stride][:MAX_API_CELLS]

    existing = read_existing()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    discovered = {}
    errors = []
    for index, (x, y) in enumerate(cells, 1):
        lon, lat = TO_LONLAT(x, y)
        try:
            for item in query_metadata(session, lat, lon):
                pid = str(first(item, "id", "photoId", "photo_id", "photoID"))
                if pid and pid not in discovered:
                    discovered[pid] = item
        except Exception as exc:
            errors.append({"cell": index, "error": str(exc)[:200]})
        time.sleep(0.15)

    # Do not re-import existing records. Query the public coverage grid to discover new IDs,
    # then append only IDs that are not already in the local metadata cache.
    new_records = 0
    for pid, item in discovered.items():
        if pid in existing:
            continue
        seq = item.get("sequence") if isinstance(item.get("sequence"), dict) else {}
        row = {
            "photo_id": pid,
            "sequence_id": str(first(item, "sequenceId", "sequence_id", "sequenceID") or first(seq, "id", "sequenceId")),
            "sequence_index": first(item, "sequenceIndex", "sequence_index", "sequenceIndexInSequence"),
            "latitude": first(item, "lat", "latitude", "gpsLatitude"),
            "longitude": first(item, "lng", "lon", "longitude", "gpsLongitude"),
            "camera_heading_deg": first(item, "heading", "gpsHeading", "bearing", "cameraHeading"),
            "capture_date": first(item, "shotDate", "captureDate", "timestamp", "dateCaptured"),
            "date_added": first(item, "dateAdded", "date_added"),
            "date_processed": first(item, "dateProcessed", "date_processed"),
            "field_of_view_deg": first(item, "fieldOfView", "field_of_view"),
            "projection": first(item, "projection"),
            "gps_accuracy_m": first(item, "gpsAccuracy", "gps_accuracy"),
            "osm_way_id": first(item, "wayId", "way_id"),
            "image_processing_status": first(item, "autoImgProcessingStatus", "imageProcessingStatus"),
            "image_processing_result": first(item, "autoImgProcessingResult"),
            "sequence_device": first(seq, "deviceName", "device_name"),
            "sequence_date_added": first(seq, "dateAdded", "date_added"),
            "sequence_distance_km": first(seq, "distance"),
            "sequence_field_of_view_deg": first(seq, "fieldOfView", "field_of_view"),
            "sequence_nw_lat": first(seq, "nwLat", "nw_lat"),
            "sequence_nw_lon": first(seq, "nwLng", "nw_lng"),
            "sequence_se_lat": first(seq, "seLat", "se_lat"),
            "sequence_se_lon": first(seq, "seLng", "se_lng"),
            "source_page": f"https://kartaview.org/map/@{row_lat(item)},{row_lon(item)},18z",
            "metadata_source": "KartaView public API; metadata only, image bytes not downloaded",
        }
        existing[pid] = row
        new_records += 1

    all_rows = sorted(existing.values(), key=lambda r: (str(r.get("sequence_id", "")), int_or_large(r.get("sequence_index")), str(r.get("photo_id", ""))))
    with PHOTOS_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PHOTO_FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    features = []
    sequence_points = {}
    for row in all_rows:
        try:
            lon, lat = float(row["longitude"]), float(row["latitude"])
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        props = {key: row.get(key, "") for key in PHOTO_FIELDS if key not in ("latitude", "longitude")}
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
        sid = str(row.get("sequence_id", "")).strip()
        if sid:
            sequence_points.setdefault(sid, []).append((int_or_large(row.get("sequence_index")), lon, lat, row))
    geojson = {"type": "FeatureCollection", "name": "KartaView street imagery metadata - Ermita", "features": features}
    PHOTOS_GEOJSON.write_text(json.dumps(geojson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    seq_fields = ["sequence_id", "photo_metadata_points", "first_capture_date", "last_capture_date", "device_name", "distance_km", "field_of_view_deg", "nw_lat", "nw_lon", "se_lat", "se_lon", "track_geojson_available", "source_page"]
    seq_rows = []
    for sid, points in sorted(sequence_points.items()):
        points.sort(key=lambda p: p[0])
        rows = [p[3] for p in points]
        dates = sorted(str(r.get("capture_date") or r.get("date_added") or "") for r in rows if r.get("capture_date") or r.get("date_added"))
        seq_rows.append({
            "sequence_id": sid, "photo_metadata_points": len(points),
            "first_capture_date": dates[0] if dates else "", "last_capture_date": dates[-1] if dates else "",
            "device_name": first(rows[0], "sequence_device"), "distance_km": first(rows[0], "sequence_distance_km"),
            "field_of_view_deg": first(rows[0], "sequence_field_of_view_deg"),
            "nw_lat": first(rows[0], "sequence_nw_lat"), "nw_lon": first(rows[0], "sequence_nw_lon"),
            "se_lat": first(rows[0], "sequence_se_lat"), "se_lon": first(rows[0], "sequence_se_lon"),
            "track_geojson_available": "yes" if len(points) >= 2 else "no",
            "source_page": f"https://kartaview.org/map/@{points[0][2]},{points[0][1]},16z",
        })
    with SEQUENCES_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=seq_fields)
        writer.writeheader()
        writer.writerows(seq_rows)

    report = {
        "status": "success" if not errors else "partial",
        "area": "Ermita, Manila, Philippines",
        "source": "KartaView public API",
        "mode": "metadata-only; no image files requested or downloaded",
        "queried_grid_cells": len(cells),
        "new_photo_metadata_records_added": new_records,
        "existing_photo_metadata_records_reimported": 0,
        "total_preserved_photo_metadata_records": len(all_rows),
        "unique_sequences_with_metadata": len(seq_rows),
        "geojson_point_features": len(features),
        "api_errors": errors,
        "outputs": [str(PHOTOS_CSV.relative_to(ROOT)), str(PHOTOS_GEOJSON.relative_to(ROOT)), str(SEQUENCES_CSV.relative_to(ROOT))],
        "incremental_policy": "Existing metadata records are not rewritten; only previously unseen photo IDs are appended. The API coverage grid is queried to discover new IDs, but existing records are not re-imported. No existing image files are deleted.",
        "limitations": ["The public nearby-photo endpoint is bounded by its response size and grid coverage; this is not a guarantee of complete citywide KartaView coverage.", "GPS points and sequence metadata describe capture coverage, not verified road signs or extracted lane/traffic-sign detections."]
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def row_lat(item):
    return first(item, "lat", "latitude", "gpsLatitude") or 0


def row_lon(item):
    return first(item, "lng", "lon", "longitude", "gpsLongitude") or 0


def int_or_large(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 10**18


if __name__ == "__main__":
    main()
