#!/usr/bin/env python3
"""Import non-OSM elevation and land-cover data for Ermita; keep downloads idempotent.

Sources:
- SRTM 1 arc-second terrain tile from the public AWS Terrain Tiles archive.
- ESA WorldCover 2021 v200 10 m land-cover map (CC BY 4.0).

No OpenStreetMap endpoint or OSM-derived dataset is queried by this script.
Existing repository files are never overwritten.
"""
from __future__ import annotations
import gzip, json, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.features import shapes
from shapely.geometry import box, mapping, shape

ROOT = Path(__file__).resolve().parents[2]
MAPS = ROOT / "ermita" / "maps"
TERRAIN = MAPS / "sources" / "terrain"
LANDCOVER = MAPS / "sources" / "landcover"
QA = MAPS / "qa"
for d in (TERRAIN, LANDCOVER, QA):
    d.mkdir(parents=True, exist_ok=True)

# Detailed Rizal Park / Ermita work area; WGS84 longitude/latitude.
BBOX = (120.972, 14.572, 120.994, 14.593)
AOI = box(*BBOX)
SRTM_URL = "https://elevation-tiles-prod.s3.amazonaws.com/skadi/N14/N14E120.hgt.gz"
WORLDCOVER_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N12E120_Map.tif"

DEM_OUT = TERRAIN / "srtm-1arcsec-ermita.tif"
COVER_OUT = LANDCOVER / "esa-worldcover-2021-10m-ermita.tif"
VEG_OUT = LANDCOVER / "vegetation-grass-classes-ermita.geojson"
REPORT_OUT = QA / "non-osm-terrain-landcover-report.json"
HILLSHADE_OUT = TERRAIN / "srtm-1arcsec-ermita-hillshade.png"

CLASS_NAMES = {
    10: "tree_cover", 20: "shrubland", 30: "grassland", 40: "cropland",
    50: "built_up", 60: "bare_sparse_vegetation", 70: "snow_ice",
    80: "permanent_water", 90: "herbaceous_wetland", 95: "mangroves",
    100: "moss_lichen",
}
VEGETATION_CLASSES = {10, 20, 30, 40, 60, 90, 95, 100}

def download(url: str, path: Path) -> dict:
    if path.exists() and path.stat().st_size:
        return {"status": "reused_existing", "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size}
    tmp = path.with_suffix(path.suffix + ".part")
    req = Request(url, headers={"User-Agent": "Adam-City-NonOSM-Terrain-Landcover/1.0"})
    try:
        with urlopen(req, timeout=120) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out)
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError("downloaded file is empty")
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return {"status": "downloaded", "url": url, "bytes": path.stat().st_size}

def clip_raster(source: Path, destination: Path) -> dict:
    if destination.exists() and destination.stat().st_size:
        with rasterio.open(destination) as ds:
            return {"status": "reused_existing", "path": str(destination.relative_to(ROOT)),
                    "width": ds.width, "height": ds.height, "crs": str(ds.crs)}
    with rasterio.open(source) as ds:
        geom = box(*BBOX)
        if ds.crs and ds.crs.to_string() != "EPSG:4326":
            from rasterio.warp import transform_geom
            geom_json = transform_geom("EPSG:4326", ds.crs, mapping(geom))
        else:
            geom_json = mapping(geom)
        arr, transform = mask(ds, [geom_json], crop=True, filled=True, nodata=ds.nodata)
        meta = ds.meta.copy()
        meta.update(driver="GTiff", height=arr.shape[1], width=arr.shape[2],
                    transform=transform, compress="deflate", tiled=True)
        if ds.nodata is not None:
            meta["nodata"] = ds.nodata
        tmp = destination.with_suffix(".tif.part")
        with rasterio.open(tmp, "w", **meta) as out:
            out.write(arr)
            out.update_tags(source=str(source.name), aoi_wgs84=",".join(map(str, BBOX)))
        tmp.replace(destination)
    with rasterio.open(destination) as ds:
        return {"status": "created", "path": str(destination.relative_to(ROOT)),
                "width": ds.width, "height": ds.height, "crs": str(ds.crs),
                "bands": ds.count, "dtype": ds.dtypes[0]}

def vectorize_vegetation(raster_path: Path) -> dict:
    if VEG_OUT.exists() and VEG_OUT.stat().st_size:
        data = json.loads(VEG_OUT.read_text(encoding="utf-8"))
        return {"status": "reused_existing", "path": str(VEG_OUT.relative_to(ROOT)),
                "features": len(data.get("features", []))}
    features_out = []
    with rasterio.open(raster_path) as ds:
        band = ds.read(1)
        valid = np.isin(band, list(VEGETATION_CLASSES))
        for geom_json, val in shapes(band, mask=valid, transform=ds.transform, connectivity=8):
            code = int(val)
            if code not in VEGETATION_CLASSES:
                continue
            geom = shape(geom_json)
            if geom.is_empty or geom.area == 0:
                continue
            # Simplify only this derived display layer; the source raster remains exact.
            geom = geom.simplify(0.000008, preserve_topology=True)
            features_out.append({
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "class_code": code,
                    "class_name": CLASS_NAMES.get(code, "unknown"),
                    "source": "ESA WorldCover 2021 v200",
                    "resolution_m": 10,
                    "note": "Land-cover classification, not individual grass blades or tree objects."
                }
            })
    collection = {"type": "FeatureCollection", "name": "ermita-vegetation-grass-classes",
                  "features": features_out}
    tmp = VEG_OUT.with_suffix(".geojson.part")
    tmp.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(VEG_OUT)
    return {"status": "created", "path": str(VEG_OUT.relative_to(ROOT)), "features": len(features_out),
            "class_counts": {name: sum(1 for f in features_out if f["properties"]["class_name"] == name)
                             for name in sorted({f["properties"]["class_name"] for f in features_out})}}

def create_hillshade() -> dict:
    if HILLSHADE_OUT.exists() and HILLSHADE_OUT.stat().st_size:
        return {"status": "reused_existing", "path": str(HILLSHADE_OUT.relative_to(ROOT)),
                "bytes": HILLSHADE_OUT.stat().st_size}
    from PIL import Image
    with rasterio.open(DEM_OUT) as ds:
        elev = ds.read(1).astype("float32")
        nodata = ds.nodata
        valid = elev != nodata if nodata is not None else np.ones(elev.shape, dtype=bool)
        xres = abs(ds.transform.a) * 111320 * np.cos(np.deg2rad((BBOX[1] + BBOX[3]) / 2))
        yres = abs(ds.transform.e) * 111132
        gy, gx = np.gradient(elev, max(yres, 1), max(xres, 1))
        slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
        aspect = np.arctan2(-gx, gy)
        azimuth, altitude = np.deg2rad(315), np.deg2rad(45)
        shade = np.sin(altitude) * np.sin(slope) + np.cos(altitude) * np.cos(slope) * np.cos(azimuth - aspect)
        gray = np.clip(255 * (0.35 + 0.65 * np.maximum(shade, 0)), 0, 255).astype("uint8")
        rgba = np.zeros((elev.shape[0], elev.shape[1], 4), dtype="uint8")
        rgba[:, :, :3] = gray[:, :, None]
        rgba[:, :, 3] = np.where(valid, 95, 0).astype("uint8")
        Image.fromarray(rgba, mode="RGBA").save(HILLSHADE_OUT, optimize=True)
    return {"status": "created", "path": str(HILLSHADE_OUT.relative_to(ROOT)),
            "bytes": HILLSHADE_OUT.stat().st_size, "width": int(elev.shape[1]),
            "height": int(elev.shape[0]), "derived_from": str(DEM_OUT.relative_to(ROOT))}

def main():
    report = {
        "status": "running",
        "area": "Ermita / Rizal Park, Manila, Philippines",
        "aoi_bbox_wgs84": list(BBOX),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "Non-OSM sources only; existing outputs are reused and never overwritten.",
        "sources": {
            "terrain": {"name": "SRTM 1 arc-second terrain via AWS Terrain Tiles", "url": SRTM_URL,
                        "license_reference": "https://registry.opendata.aws/terrain-tiles/"},
            "landcover": {"name": "ESA WorldCover 2021 v200, 10 m", "url": WORLDCOVER_URL,
                          "license": "CC BY 4.0",
                          "attribution": "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium",
                          "license_reference": "https://esa-worldcover.org/en/data-access"}
        },
        "outputs": {}, "warnings": []
    }
    with tempfile.TemporaryDirectory(prefix="adam-city-terrain-") as td:
        tmp = Path(td)
        # Terrain: download only to temporary storage, keep the clipped output in Git.
        try:
            gz = tmp / "N14E120.hgt.gz"
            download(SRTM_URL, gz)
            hgt = tmp / "N14E120.hgt"
            with gzip.open(gz, "rb") as src, hgt.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            report["outputs"]["terrain"] = clip_raster(hgt, DEM_OUT)
            report["outputs"]["terrain"]["source_resolution"] = "approximately 1 arc-second"
        except Exception as exc:
            report["warnings"].append("Terrain import failed: " + repr(exc))
        # Derive a transparent hillshade preview from the locally stored SRTM DEM.
        try:
            if DEM_OUT.exists():
                report["outputs"]["terrain_hillshade"] = create_hillshade()
        except Exception as exc:
            report["warnings"].append("Terrain hillshade generation failed: " + repr(exc))
        # Land cover: skip the network request when the clipped raster is already saved.
        try:
            if COVER_OUT.exists() and COVER_OUT.stat().st_size:
                report["outputs"]["landcover"] = {"status": "reused_existing",
                    "path": str(COVER_OUT.relative_to(ROOT)), "bytes": COVER_OUT.stat().st_size}
            else:
                source = tmp / "esa-worldcover.tif"
                download(WORLDCOVER_URL, source)
                report["outputs"]["landcover"] = clip_raster(source, COVER_OUT)
            if COVER_OUT.exists():
                report["outputs"]["vegetation_polygons"] = vectorize_vegetation(COVER_OUT)
        except Exception as exc:
            report["warnings"].append("Land-cover import failed: " + repr(exc))
    report["status"] = "success" if report["outputs"] and not report["warnings"] else (
        "partial" if report["outputs"] else "failed")
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["outputs"]:
        raise RuntimeError("Neither terrain nor land-cover output was produced.")

if __name__ == "__main__":
    main()
