#!/usr/bin/env python3
"""Audit LiDAR suitability for building geometry; do not import satellite laser samples.

This pipeline is deliberately gated: only verified airborne/terrestrial point clouds
(LAS/LAZ/COPC or an explicitly identified equivalent) covering Jordan can be considered
useful input for building roofs, heights and infrastructure. GEDI/ICESat-2 satellite
footprints are not dense city LiDAR and must not be downloaded as a substitute.
"""
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path("middle east/LiDAR")
RAW=ROOT/"downloads"
REPORT=ROOT/"LIDAR_IMPORT_REPORT.md"
for path in (ROOT, RAW):
    path.mkdir(parents=True, exist_ok=True)

def inspect_pointclouds():
    found=[]
    for p in RAW.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".las",".laz",".copc"}:
            continue
        try:
            with p.open("rb") as f: header=f.read(4)
            valid=header==b"LASF"
            found.append({"path":str(p),"bytes":p.stat().st_size,"las_signature_valid":valid})
        except OSError as exc:
            found.append({"path":str(p),"bytes":0,"las_signature_valid":False,"error":str(exc)})
    return found

pointclouds=inspect_pointclouds()
valid=[x for x in pointclouds if x.get("las_signature_valid") and x.get("bytes",0)>227]
stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
lines=[
"# Jordan — building-useful LiDAR import audit","",
f"Last checked: {stamp}","",
"## Decision",
"",
"Satellite laser observations (GEDI and ICESat-2 ATL03/ATL06/ATL08) are not being imported by this workflow. Their sparse orbital footprints are not dense airborne/terrestrial point clouds and do not provide reliable building facades or complete roof surfaces. They are not a suitable substitute for the requested building-focused LiDAR.",
"",
"This workflow is now audit-only until a source is verified to contain actual airborne or terrestrial LiDAR point clouds covering Jordan. It will not crawl global catalogs, download satellite observations, or count catalog JSON as imported data.",
"",
"## Existing point-cloud files checked",
"",
f"- LAS/LAZ/COPC files found: {len(pointclouds)}",
f"- Files with valid LASF signature and plausible size: {len(valid)}",
]
for item in pointclouds:
    lines.append(f"- {item['path']} — {item['bytes']} bytes; LAS signature valid: {item.get('las_signature_valid',False)}")
lines += [
"",
"## What would be useful for building reconstruction",
"",
"- Airborne/vehicle-mounted LiDAR point clouds (LAS/LAZ/COPC) with roof and building returns, preferably classified building points.",
"- Point density, coordinate reference system, acquisition date, vertical datum, and license must be recorded per dataset.",
"- A bare-earth DEM alone helps terrain placement but cannot reconstruct facades. GEDI/ICESat-2 samples may help broad vegetation/terrain research, but not the requested city building detail.",
"",
"## Current result",
"",
"No new LiDAR payloads were downloaded by this audit. Existing files were not deleted. A future import must first prove geographic overlap with Jordan and that the source is an airborne/terrestrial point cloud before downloading payloads."
]
REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(f"LiDAR suitability audit complete: pointcloud_files={len(pointclouds)} valid={len(valid)}; no satellite downloads attempted.",flush=True)
