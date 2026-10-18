#!/usr/bin/env python3
"""Convert the persisted Microsoft Ermita GeoJSONL gzip archive to browser-ready GeoJSON."""
import gzip, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / "ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz"
target = ROOT / "ermita/maps/external/ermita-microsoft-building-footprints.geojson"
count = 0
target.parent.mkdir(parents=True, exist_ok=True)
tmp = target.with_suffix(".geojson.tmp")
with gzip.open(source, "rt", encoding="utf-8") as src, tmp.open("w", encoding="utf-8") as out:
    out.write('{"type":"FeatureCollection","features":[\n')
    first = True
    for line in src:
        line = line.strip()
        if not line:
            continue
        feature = json.loads(line)
        if feature.get("type") != "Feature" or not feature.get("geometry"):
            continue
        if not first:
            out.write(",\n")
        json.dump(feature, out, separators=(",", ":"), ensure_ascii=False)
        first = False
        count += 1
    out.write("\n]}\n")
tmp.replace(target)
print(f"Wrote {count} Microsoft building footprints to {target}")
if count == 0:
    raise SystemExit("No Microsoft footprints were converted")
