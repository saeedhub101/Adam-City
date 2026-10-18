#!/usr/bin/env python3
"""Fetch a public Copernicus DEM tile, crop it to Ermita and build a terrain mesh.

The Copernicus DEM is a digital surface model (surface elevations can include
vegetation and structures), not a surveyed bare-earth DTM. Output is approximate.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from pyproj import Transformer
import trimesh

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ermita" / "3d" / "terrain"
OUT.mkdir(parents=True, exist_ok=True)
# Central Ermita/Rizal Park bounding box; expanded enough to show nearby context.
BOUNDS = (120.965, 14.560, 121.005, 14.605)  # west, south, east, north
SOURCES = [
    ("Copernicus DEM GLO-30 Public", "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N14_00_E120_00_DEM/Copernicus_DSM_COG_10_N14_00_E120_00_DEM.tif", 30),
    ("Copernicus DEM GLO-90", "https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_N14_00_E120_00_DEM/Copernicus_DSM_COG_30_N14_00_E120_00_DEM.tif", 90),
]
ATTRIBUTION = "Produced using Copernicus WorldDEM-30/90 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved."

def main():
    errors = []
    for label, url, nominal_resolution in SOURCES:
        try:
            # GDAL's /vsicurl/ enables HTTP range reads from the public cloud-optimized GeoTIFF.
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
                with rasterio.open("/vsicurl/" + url) as src:
                    if src.crs is None:
                        raise ValueError("DEM source has no CRS")
                    if src.crs.to_epsg() != 4326:
                        raise ValueError(f"Expected geographic DEM, got {src.crs}")
                    win = from_bounds(*BOUNDS, transform=src.transform).round_offsets().round_lengths()
                    win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
                    if win.width <= 1 or win.height <= 1:
                        raise ValueError("DEM tile does not overlap the Ermita bounding box")
                    data = src.read(1, window=win, masked=True, out_shape=(min(180, int(win.height)), min(180, int(win.width))), resampling=Resampling.bilinear)
                    transform = src.window_transform(win)
                    # Correct affine transform for the resampled crop.
                    from affine import Affine
                    transform = transform * Affine.scale(win.width / data.shape[1], win.height / data.shape[0])
                    profile = src.profile.copy()
                    profile.update(driver="GTiff", height=data.shape[0], width=data.shape[1], transform=transform,
                                   count=1, compress="deflate", tiled=True, nodata=-9999)
                    values = np.asarray(data.filled(-9999), dtype=np.float32)
                    values[~np.isfinite(values)] = -9999
                    tif_path = OUT / "ermita-copernicus-dem-cropped.tif"
                    with rasterio.open(tif_path, "w", **profile) as dst:
                        dst.write(values, 1)
                    rows, cols = values.shape
                    rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
                    lon, lat = rasterio.transform.xy(transform, rr, cc, offset="center")
                    lon, lat = np.asarray(lon), np.asarray(lat)
                    x, y = Transformer.from_crs("EPSG:4326", "EPSG:32651", always_xy=True).transform(lon, lat)
                    x, y = np.asarray(x), np.asarray(y)
                    z = values.copy()
                    valid = z != -9999
                    if valid.sum() < 4:
                        raise ValueError("DEM crop contains too few valid elevation cells")
                    z[~valid] = float(np.median(z[valid]))
                    vertices = np.column_stack((x.ravel(), y.ravel(), z.ravel()))
                    faces = []
                    for r in range(rows - 1):
                        base = r * cols
                        for c in range(cols - 1):
                            a, b, d, e = base+c, base+c+1, base+cols+c, base+cols+c+1
                            faces.extend(((a, d, b), (b, d, e)))
                    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces, dtype=np.int64), process=False)
                    center = mesh.bounds.mean(axis=0)
                    mesh.apply_translation((-center[0], -center[1], -center[2]))
                    glb_path = OUT / "ermita-terrain-surface.glb"
                    mesh.export(glb_path)
                    report = {
                        "status": "success", "source_dataset": label, "source_url": url,
                        "nominal_resolution_m": nominal_resolution, "bbox_wgs84": BOUNDS,
                        "crop_shape_rows_cols": [int(rows), int(cols)],
                        "valid_elevation_cells": int(valid.sum()),
                        "elevation_min_m": float(np.min(values[valid])),
                        "elevation_max_m": float(np.max(values[valid])),
                        "source_model_type": "Digital Surface Model (DSM), not bare-earth DTM",
                        "terrain_mesh": glb_path.name, "cropped_geotiff": tif_path.name,
                        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "attribution": ATTRIBUTION,
                        "limitations": ["Coarse regional elevation; not suitable for engineering or flood-safety decisions.",
                                        "DSM elevations may include buildings and vegetation.",
                                        "No high-resolution orthophoto was imported by this script."]
                    }
                    (OUT / "terrain-import-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                    (OUT / "README.md").write_text("# Ermita terrain data\n\nThis folder contains a cropped Copernicus elevation surface and a simple terrain mesh for visualization. It is a regional-resolution DSM, not a survey-grade bare-earth terrain model.\n\n- [3D terrain surface](ermita-terrain-surface.glb)\n- [Cropped GeoTIFF](ermita-copernicus-dem-cropped.tif)\n- [Import report and source attribution](terrain-import-report.json)\n\n" + ATTRIBUTION + "\n", encoding="utf-8")
                    print(json.dumps({"status":"success","source":label,"rows":rows,"cols":cols,"valid_cells":int(valid.sum())}))
                    return
        except Exception as exc:
            errors.append({"source": label, "error": str(exc)})
            print(f"DEM source failed: {label}: {exc}", file=sys.stderr)
    report = {"status": "unavailable", "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "attempts": errors, "note": "No terrain files generated. Check public tile availability and source access before retrying."}
    (OUT / "terrain-import-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Do not break the working OSM/building import if a third-party DEM tile is unavailable.
    print(json.dumps(report))
    return

if __name__ == "__main__":
    main()
