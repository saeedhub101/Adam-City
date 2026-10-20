#!/usr/bin/env python3
"""Create a web-friendly JPEG preview from the already stored OpenAerialMap GeoTIFF."""
import json
from pathlib import Path
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / "ermita/maps/external/openaerialmap/ermita-5b90f92da0d7280005fab355.tif"
output = source.with_suffix(".jpg")
report_path = source.parent / "local-aerial-preview-report.json"
if not source.exists():
    raise SystemExit(f"Required existing imagery is missing: {source}")
with rasterio.open(source) as ds:
    if ds.count < 3:
        raise SystemExit(f"Expected RGB imagery, found {ds.count} band(s)")
    scale = min(1.0, 4500 / max(ds.width, ds.height))
    width, height = max(1, round(ds.width * scale)), max(1, round(ds.height * scale))
    rgb = ds.read([1, 2, 3], out_shape=(3, height, width), resampling=Resampling.bilinear)
    bounds = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds, densify_pts=21)
    # Convert band-first raster to RGB and save an optimized browser image.
    image = Image.fromarray(rgb.transpose(1, 2, 0), mode="RGB")
    image.save(output, "JPEG", quality=88, optimize=True, progressive=True)
report = {
    "source": "Existing OpenAerialMap GeoTIFF already stored in this repository",
    "source_file": str(source.relative_to(ROOT)),
    "web_preview": str(output.relative_to(ROOT)),
    "width": width,
    "height": height,
    "bounds_wgs84_west_south_east_north": list(bounds),
    "display_note": "This image covers the Arroceros Forest Park area north of central Ermita; it only overlays where its footprint exists.",
    "sha256": __import__("hashlib").sha256(output.read_bytes()).hexdigest(),
    "bytes": output.stat().st_size,
}
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
