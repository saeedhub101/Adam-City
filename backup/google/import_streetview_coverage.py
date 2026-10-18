#!/usr/bin/env python3
"""Check Google Street View coverage along OSM streets without downloading Google imagery.

Only Google panorama IDs are persisted (the documented caching exception). Sample
coordinates come from OpenStreetMap street geometry. No Google imagery, tiles,
dates, or Google-returned coordinates are saved to the repository.
Requires GOOGLE_MAPS_API_KEY with Street View Static API enabled.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
import requests
from pyproj import Transformer
from shapely.geometry import shape, Point, mapping
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "ermita/maps/generated/ermita-features.geojson"
OUT_DIR = ROOT / "ermita/maps/external"
OUT_FILE = OUT_DIR / "google-streetview-panorama-index.geojson"
REPORT = OUT_DIR / "google-streetview-coverage-report.json"
STEP_METERS = 120
MAX_SAMPLES = 500

def main():
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        print("GOOGLE_MAPS_API_KEY is not set; coverage check skipped.")
        return 0
    if not FEATURES.exists():
        print(f"Missing OSM street source: {FEATURES}", file=sys.stderr)
        return 2
    collection = json.loads(FEATURES.read_text(encoding="utf-8"))
    to_metric = Transformer.from_crs("EPSG:4326", "EPSG:32651", always_xy=True).transform
    to_wgs84 = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True).transform
    samples = []
    seen = set()
    for feature in collection.get("features", []):
        tags = feature.get("properties") or feature.get("tags") or {}
        if not tags.get("highway"):
            continue
        try:
            geom = transform(to_metric, shape(feature["geometry"]))
        except Exception:
            continue
        lines = [geom] if geom.geom_type == "LineString" else list(geom.geoms) if geom.geom_type == "MultiLineString" else []
        for line in lines:
            n = max(1, int(line.length // STEP_METERS))
            for i in range(n + 1):
                p = line.interpolate(min(i * STEP_METERS, line.length))
                w = transform(to_wgs84, p)
                coord = (round(w.x, 6), round(w.y, 6))
                if coord not in seen:
                    seen.add(coord)
                    samples.append(coord)
                    if len(samples) >= MAX_SAMPLES:
                        break
            if len(samples) >= MAX_SAMPLES:
                break
        if len(samples) >= MAX_SAMPLES:
            break

    session = requests.Session()
    features, counts = [], {"OK": 0, "ZERO_RESULTS": 0, "OTHER": 0}
    for idx, (lon, lat) in enumerate(samples, 1):
        try:
            response = session.get(
                "https://maps.googleapis.com/maps/api/streetview/metadata",
                params={"location": f"{lat},{lon}", "key": key}, timeout=20)
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "OTHER")
            if status == "OK" and data.get("pano_id"):
                counts["OK"] += 1
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "google_pano_id": data["pano_id"],
                        "sample_source": "OpenStreetMap street geometry",
                        "google_source": "Google Street View Static API",
                        "note": "Panorama ID only; request fresh metadata before display."
                    }
                })
            elif status == "ZERO_RESULTS":
                counts["ZERO_RESULTS"] += 1
            else:
                counts["OTHER"] += 1
                print(f"Google metadata status at sample {idx}: {status}", file=sys.stderr)
        except Exception as exc:
            counts["OTHER"] += 1
            print(f"Google metadata request failed at sample {idx}: {exc}", file=sys.stderr)
        if idx % 50 == 0:
            print(f"Checked {idx}/{len(samples)} street samples")
        time.sleep(0.05)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {"type": "FeatureCollection", "name": "Google Street View panorama ID index",
           "license_note": "Google panorama IDs only; no imagery or Google-returned coordinates stored.",
           "features": features}
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    report = {
        "source": "Google Street View Static API metadata; sampled locations derived from OpenStreetMap streets",
        "checked_sample_count": len(samples),
        "samples_with_panorama": counts["OK"],
        "samples_without_panorama": counts["ZERO_RESULTS"],
        "samples_with_other_status_or_error": counts["OTHER"],
        "sample_spacing_meters": STEP_METERS,
        "maximum_samples": MAX_SAMPLES,
        "stored_google_fields": ["panorama ID only"],
        "imagery_downloaded": False,
        "google_maps_attribution_required_when_displaying": True,
        "outputs": [str(OUT_FILE.relative_to(ROOT)), str(REPORT.relative_to(ROOT))]
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
