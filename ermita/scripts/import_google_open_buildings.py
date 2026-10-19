#!/usr/bin/env python3
"""Fetch Google Research Open Buildings v3 for Ermita only; no OSM endpoints."""
from __future__ import annotations
import csv, gzip, json, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from shapely import wkt
from shapely.geometry import box, mapping
from shapely.prepared import prep
import s2geometry as s2

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "ermita" / "maps" / "sources" / "google-open-buildings"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "google-open-buildings-v3-ermita.geojson"
REPORT = OUT_DIR / "google-open-buildings-v3-ermita-report.json"
BBOX = (120.972, 14.572, 120.994, 14.593)
AOI = box(*BBOX)
BASE = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_6_gzip_no_header"
MAX_CELL_BYTES = 250 * 1024 * 1024
MIN_CONFIDENCE = 0.65

def cell_tokens():
    rect = s2.S2LatLngRect.FromPointPair(
        s2.S2LatLng.FromDegrees(BBOX[1], BBOX[0]),
        s2.S2LatLng.FromDegrees(BBOX[3], BBOX[2]))
    coverer = s2.S2RegionCoverer()
    coverer.set_fixed_level(6)
    coverer.set_max_cells(1000)
    return sorted({cell.ToToken() for cell in coverer.GetCovering(rect)})

def main():
    if OUT.exists() and OUT.stat().st_size and REPORT.exists():
        previous = json.loads(REPORT.read_text(encoding="utf-8"))
        previous["run_status"] = "reused_existing_no_download"
        print(json.dumps(previous, ensure_ascii=False, indent=2))
        return

    report = {
        "status": "running",
        "source": "Google Research Open Buildings v3 polygon detections",
        "source_url": "https://sites.research.google/gr/open-buildings/",
        "download_root": BASE,
        "area": "Ermita / Rizal Park, Manila, Philippines",
        "bbox_wgs84": list(BBOX),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_inference_vintage": "May 2023 (Open Buildings v3)",
        "license": "CC BY 4.0 (selected license option)",
        "attribution": "Google Research Open Buildings v3; see https://sites.research.google/gr/open-buildings/",
        "minimum_confidence_retained": MIN_CONFIDENCE,
        "identity_policy": "Stored as a separate source; no OSM matching or overwriting.",
        "cells": [], "warnings": []
    }
    region = prep(AOI)
    features = []
    tokens = cell_tokens()
    report["s2_level"] = 6
    report["s2_cells_considered"] = tokens

    with tempfile.TemporaryDirectory(prefix="adam-city-google-buildings-") as td:
        for token in tokens:
            url = f"{BASE}/{token}_buildings.csv.gz"
            path = Path(td) / f"{token}_buildings.csv.gz"
            try:
                req = Request(url, headers={"User-Agent": "Adam-City-Open-Buildings-Importer/1.0"})
                with urlopen(req, timeout=120) as response, path.open("wb") as out:
                    length = response.headers.get("Content-Length")
                    if length and int(length) > MAX_CELL_BYTES:
                        raise ValueError(f"S2 cell compressed size exceeds {MAX_CELL_BYTES} bytes")
                    total = 0
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_CELL_BYTES:
                            raise ValueError(f"S2 cell exceeded {MAX_CELL_BYTES} bytes")
                        out.write(chunk)
                kept = 0
                checked = 0
                with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
                    reader = csv.reader(stream)
                    for row in reader:
                        if len(row) < 5:
                            continue
                        checked += 1
                        try:
                            lat, lon = float(row[0]), float(row[1])
                            area = float(row[2])
                            confidence = float(row[3])
                            geom = wkt.loads(row[4])
                        except (ValueError, TypeError, IndexError):
                            continue
                        if confidence < MIN_CONFIDENCE or geom.is_empty or not region.intersects(geom):
                            continue
                        plus_code = row[5] if len(row) > 5 else ""
                        features.append({
                            "type": "Feature",
                            "id": f"google-open-buildings-v3-{token}-{len(features)+1}",
                            "geometry": mapping(geom),
                            "properties": {
                                "source": "Google Research Open Buildings v3",
                                "source_cell_s2_l6": token,
                                "confidence": confidence,
                                "area_in_meters": area,
                                "centroid_latitude": lat,
                                "centroid_longitude": lon,
                                "full_plus_code": plus_code,
                                "confidence_ge_080": confidence >= 0.8,
                                "inference_vintage": "2023-05",
                                "osm_id": None
                            }
                        })
                        kept += 1
                report["cells"].append({"token": token, "status": "downloaded_and_filtered",
                                        "compressed_bytes": path.stat().st_size,
                                        "rows_examined": checked, "features_retained": kept})
            except Exception as exc:
                report["cells"].append({"token": token, "status": "failed", "url": url,
                                        "error": repr(exc)})
                report["warnings"].append(f"S2 cell {token}: {repr(exc)}")

    collection = {"type": "FeatureCollection", "name": "google-open-buildings-v3-ermita",
                  "features": features}
    if features:
        tmp = OUT.with_suffix(".geojson.part")
        tmp.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n",
                       encoding="utf-8")
        tmp.replace(OUT)
        report["output_file"] = str(OUT.relative_to(ROOT))
        report["feature_count"] = len(features)
        report["high_confidence_count_ge_080"] = sum(1 for f in features if f["properties"]["confidence_ge_080"])
        report["status"] = "partial" if report["warnings"] else "success"
    else:
        report["feature_count"] = 0
        report["status"] = "failed"
        report["warnings"].append("No building polygons were retained. Check whether the area is covered and whether S2 downloads succeeded.")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not features:
        raise RuntimeError("Google Open Buildings import produced no building polygons.")

if __name__ == "__main__":
    main()
