#!/usr/bin/env python3
"""Prepare Unity-friendly JSON from the compressed GeoJSON already in middle east/Jordan and middle east/Palestine.

Standard library only. Never reads outside this middle east folder. Never overwrites source data.
"""
from __future__ import annotations
import gzip, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGIONS = {
    "Jordan": ("Jordan", ("buildings", "building_details", "streets", "streetnames", "places", "water", "landcover", "addresses", "boundaries")),
    "Palestine": ("Palestine", ("buildings", "building_details", "streets", "streetnames", "places", "water", "landcover", "addresses", "boundaries")),
}

def read_features(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        return data.get("features", [])
    if isinstance(data, dict) and data.get("type") == "Feature":
        return [data]
    raise ValueError(f"Unsupported GeoJSON root in {path}")

def main():
    for out_name, (source_name, layers) in REGIONS.items():
        source = ROOT / source_name / "layers"
        output = ROOT / "UnityGame" / "BuildData" / out_name
        output.mkdir(parents=True, exist_ok=True)
        manifest = {"region": out_name, "coordinate_system": "WGS84 lon/lat", "layers": {}, "source_root": f"{source_name}/layers"}
        for layer in layers:
            path = source / f"{layer}.geojson.gz"
            if not path.exists():
                continue
            features = read_features(path)
            target = output / f"{layer}.json"
            # Keep source properties and geometry intact; compact encoding reduces disk footprint.
            target.write_text(json.dumps({"type":"FeatureCollection","features":features}, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
            manifest["layers"][layer] = {"file": target.name, "feature_count": len(features), "source_bytes": path.stat().st_size, "output_bytes": target.stat().st_size}
            print(f"{out_name}/{layer}: {len(features):,} features -> {target.stat().st_size:,} bytes")
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Prepared region data. Original .geojson.gz files were not modified.")

if __name__ == "__main__":
    main()
