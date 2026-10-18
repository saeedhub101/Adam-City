# Trigger footprint import using the latest conflict-safe workflow.
#!/usr/bin/env python3
"""Fetch Microsoft's public Philippines building footprints and clip to Ermita AOI."""
import gzip
import json
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from shapely.geometry import box, shape, mapping

URL = "https://minedbuildings.z5.web.core.windows.net/legacy/southeast-asia/philippines.geojsonl.zip"
# Project AOI from Copernicus terrain import. This is a rectangular crop, not a parcel boundary.
AOI = box(120.965, 14.560, 121.005, 14.605)
OUT = Path("ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz")
REPORT = Path("ermita/maps/external/microsoft-building-footprints-import-report.json")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "running",
        "source": "Microsoft/Bing Maps Open Building Footprints — Philippines",
        "source_url": URL,
        "source_imagery_vintage": "2016–2020",
        "license": "Open Data Commons Open Database License (ODbL); retain attribution and comply with share-alike terms",
        "source_crs": "EPSG:4326",
        "aoi_bbox_wgs84": [120.965, 14.560, 121.005, 14.605],
        "output": str(OUT),
        "method": "Stream each line-delimited GeoJSON feature from the official Philippines archive; intersect with the project AOI rectangle; write clipped features as gzip-compressed GeoJSONL.",
        "features_read": 0,
        "features_intersecting_aoi": 0,
        "features_written": 0,
        "duplicate_features_skipped": 0,
        "limitations": [
            "This is a supplemental non-government dataset, not a Philippine government dataset.",
            "Contains detected building footprints only; no façades, windows, signs, logos, or guaranteed building names.",
            "Source imagery is dated 2016–2020; completeness and positional accuracy vary by location.",
            "The AOI is the project's rectangular crop and may include adjacent areas."
        ]
    }
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "philippines.geojsonl.zip"
        request = urllib.request.Request(URL, headers={"User-Agent": "Adam-City-data-import/1.0"})
        print(f"Downloading {URL}", flush=True)
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as dst:
            total = 0
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
                total += len(chunk)
                print(f"Downloaded {total / (1024**3):.2f} GiB", flush=True)
        report["downloaded_archive_bytes"] = archive.stat().st_size
        with zipfile.ZipFile(archive) as zf:
            members = [n for n in zf.namelist() if n.lower().endswith((".geojsonl", ".jsonl", ".geojson", ".json"))]
            if not members:
                raise RuntimeError("No GeoJSON/GeoJSONL member found in source archive: " + repr(zf.namelist()[:10]))
            member = max(members, key=lambda n: zf.getinfo(n).file_size)
            report["archive_member"] = member
            tmp_out = OUT.with_suffix(OUT.suffix + ".tmp")
            seen_keys = set()
            try:
                with zf.open(member, "r") as src, gzip.open(tmp_out, "wt", encoding="utf-8", compresslevel=6) as dst:
                    for raw in src:
                        if not raw.strip():
                            continue
                        feature = json.loads(raw)
                        report["features_read"] += 1
                        geom_data = feature.get("geometry")
                        if not geom_data:
                            continue
                        geom = shape(geom_data)
                        if geom.is_empty or not geom.intersects(AOI):
                            continue
                        report["features_intersecting_aoi"] += 1
                        clipped = geom.intersection(AOI)
                        if clipped.is_empty:
                            continue
                        feature["geometry"] = mapping(clipped)
                        props = feature.get("properties")
                        if not isinstance(props, dict):
                            props = {}
                            feature["properties"] = props
                        # Deduplicate within the downloaded source snapshot by stable source ID;
                        # fall back to clipped geometry when no source ID is available.
                        source_id = feature.get("id") or props.get("id") or props.get("building_id") or props.get("osm_id")
                        dedupe_key = f"id:{source_id}" if source_id is not None else f"geom:{clipped.wkb_hex}"
                        if dedupe_key in seen_keys:
                            report["duplicate_features_skipped"] += 1
                            continue
                        seen_keys.add(dedupe_key)
                        feature["properties"]["source_dataset"] = "Microsoft Open Building Footprints Philippines"
                        feature["properties"]["source_imagery_vintage"] = "2016-2020"
                        dst.write(json.dumps(feature, separators=(",", ":")) + "\n")
                        report["features_written"] += 1
                        if report["features_read"] % 500000 == 0:
                            print(f"Processed {report['features_read']:,}; clipped {report['features_written']:,}", flush=True)
                tmp_out.replace(OUT)
            finally:
                if tmp_out.exists():
                    tmp_out.unlink()
    report["output_bytes"] = OUT.stat().st_size
    report["status"] = "success"
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
