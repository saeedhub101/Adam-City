#!/usr/bin/env python3
"""Fetch Microsoft's open mined-road data for Southeast Asia and clip PHL roads to Ermita AOI."""
import json, subprocess, tempfile, zipfile
from pathlib import Path
from shapely.geometry import shape, box, mapping

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ermita/maps/external/ermita-microsoft-road-detections.geojson"
URL = "https://usaminedroads.z19.web.core.windows.net/drops/2025.04.28/Southeastern_Asia.zip"
AOI = box(120.965, 14.560, 121.005, 14.605)

with tempfile.TemporaryDirectory() as td:
    archive = Path(td) / "Southeastern_Asia.zip"
    subprocess.run(["curl", "-fL", "--retry", "3", "--retry-delay", "3", URL, "-o", str(archive)], check=True)
    count_read = count_aoi = 0
    features = []
    with zipfile.ZipFile(archive) as zf:
        members = [n for n in zf.namelist() if not n.endswith("/")]
        if not members:
            raise RuntimeError("Microsoft Southeast Asia road archive contains no files")
        for member in members:
            with zf.open(member) as stream:
                for raw in stream:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    parts = line.split("\t", 1)
                    if len(parts) != 2 or parts[0].strip().upper() != "PHL":
                        continue
                    count_read += 1
                    try:
                        item = json.loads(parts[1])
                        geom = shape(item.get("geometry") or {})
                        if geom.is_empty or not geom.intersects(AOI):
                            continue
                        clipped = geom.intersection(AOI)
                        if clipped.is_empty:
                            continue
                        props = dict(item.get("properties") or {})
                        props["source"] = "Microsoft ML Road Detections"
                        props["source_vintage"] = "Microsoft-published 2025-04-28 regional release; imagery dates vary"
                        features.append({"type":"Feature","geometry":mapping(clipped),"properties":props})
                        count_aoi += 1
                    except Exception:
                        continue
    if not features:
        raise RuntimeError(f"No PHL Microsoft road detections found in AOI (checked {count_read} PHL rows)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(".geojson.tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump({"type":"FeatureCollection","features":features}, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    temp.replace(OUT)
    print(f"Read {count_read} Philippines road rows; saved {count_aoi} clipped Ermita features to {OUT}")
