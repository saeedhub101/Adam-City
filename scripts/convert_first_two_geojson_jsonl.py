#!/usr/bin/env python3
"""Convert the first two JSONL GeoJSON chunks into standard GeoJSON FeatureCollections."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "Philippine" / "GeoJSON"
OUTPUT_DIR = ROOT / "Philippine" / "GeoJSON_Map"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for number in (1, 2):
    name = f"Philippine{number:02d}.geojson"
    source = SOURCE_DIR / name
    features = []
    with source.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                feature = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{source}:{line_number}: invalid JSON: {exc}")
            if feature.get("type") != "Feature" or "geometry" not in feature:
                raise SystemExit(f"{source}:{line_number}: expected a GeoJSON Feature")
            features.append(feature)
    output = OUTPUT_DIR / name
    document = {"type": "FeatureCollection", "features": features}
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
    # Validate the generated standard GeoJSON document and feature count.
    with output.open("r", encoding="utf-8") as stream:
        check = json.load(stream)
    assert check.get("type") == "FeatureCollection"
    assert len(check.get("features", [])) == len(features)
    print(f"{name}: {len(features)} features -> {output.relative_to(ROOT)} ({output.stat().st_size} bytes)")
