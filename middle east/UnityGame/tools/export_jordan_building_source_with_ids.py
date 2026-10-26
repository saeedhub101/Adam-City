#!/usr/bin/env python3
"""Build a temporary identity-preserving GeoJSON layer from the repository's saved Jordan PBF.

The generated file is a workflow intermediate under UnityGame/BuildData; it is not a new external
download and is not committed as source data. OSM IDs are exported as @id attributes.
"""
import gzip
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PBF = ROOT / "middle east" / "Jordan" / "osm" / "jordan-latest.osm.pbf"
OUT = ROOT / "middle east" / "UnityGame" / "BuildData" / "jordan-buildings-with-osm-ids.geojson.gz"

def main():
    if not PBF.is_file():
        raise FileNotFoundError(f"Saved local Jordan OSM PBF is missing: {PBF}")
    if shutil.which("osmium") is None:
        raise RuntimeError("osmium-tool is required; install it in the workflow before running this exporter")
    OUT.parent.mkdir(parents=True, exist_ok=True)
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
        # Stream compression so the temporary GeoJSON need not be duplicated in memory.
        with geojson.open("rb") as source, gzip.open(OUT, "wb", compresslevel=6) as target:
            shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
    print(f"Created identity-preserving OSM building source: {OUT} ({OUT.stat().st_size} compressed bytes)")

if __name__ == "__main__":
    main()
