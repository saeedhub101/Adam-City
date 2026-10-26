#!/usr/bin/env python3
"""Temporarily replace the checked-out building GeoJSON with an ID-preserving export from saved OSM PBF.

The workflow restores the tracked GeoJSON after indexing, so the generated intermediate is never
committed. The input PBF is already stored in this repository; no external runtime data is used.
"""
import gzip
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PBF = ROOT / "middle east" / "Jordan" / "osm" / "jordan-latest.osm.pbf"
OUT = ROOT / "middle east" / "Jordan" / "layers" / "buildings.geojson.gz"

def main():
    if not PBF.is_file():
        raise FileNotFoundError(f"Saved local Jordan OSM PBF is missing: {PBF}")
    if shutil.which("osmium") is None:
        raise RuntimeError("osmium-tool is required; install it in the workflow before running this exporter")
    with tempfile.TemporaryDirectory(prefix="adam-city-osm-id-export-") as tmp:
        filtered = Path(tmp) / "jordan-buildings.osm.pbf"
        geojson = Path(tmp) / "jordan-buildings.geojson"
        subprocess.run([
            "osmium", "tags-filter", str(PBF),
            "w/building", "w/building:part", "r/building",
            "-o", str(filtered), "--overwrite"
        ], check=True)
        subprocess.run([
            "osmium", "export", str(filtered),
            "--attributes=type,id", "--output-format=geojson",
            "-o", str(geojson), "--overwrite"
        ], check=True)
        # Replace only the workflow checkout copy; the workflow restores this tracked file afterward.
        with geojson.open("rb") as source, gzip.open(OUT, "wb", compresslevel=6) as target:
            shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
    print(f"Created ID-preserving building export at {OUT} ({OUT.stat().st_size} bytes compressed)")

if __name__ == "__main__":
    main()
