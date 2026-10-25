#!/usr/bin/env python3
"""Download Microsoft's free Philippines building-footprint release and clip a Malate-focused AOI.

The full country archive is temporary CI input. Only the clipped GeoJSON and its
provenance report are committed. Existing output is never silently overwritten.
"""
from __future__ import annotations
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from shapely.geometry import box, shape, mapping

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "ermita" / "maps" / "sources" / "microsoft-satellite-buildings"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "microsoft-philippines-satellite-footprints-malate.geojson"
REPORT = OUT_DIR / "microsoft-philippines-satellite-footprints-malate-report.json"
SOURCE_URL = "https://minedbuildings.z5.web.core.windows.net/legacy/southeast-asia/philippines.geojsonl.zip"
# Malate-focused rectangle with a small surrounding buffer to catch complete buildings.
BBOX = (120.972, 14.550, 121.005, 14.580)
AOI = box(*BBOX)
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_OUTPUT_FEATURES = 200_000

def coords_bounds(coords):
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    stack = [coords]
    while stack:
        item = stack.pop()
        if not item:
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)):
            x, y = float(item[0]), float(item[1])
            minx, miny, maxx, maxy = min(minx, x), min(miny, y), max(maxx, x), max(maxy, y)
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
    return minx, miny, maxx, maxy

def download_archive(dest: Path):
    req = Request(SOURCE_URL, headers={"User-Agent": "Adam-City-Microsoft-Malate-Footprints/1.0"})
    total = 0
    with urlopen(req, timeout=240) as response, dest.open("wb") as out:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_ARCHIVE_BYTES:
            raise RuntimeError(f"Source archive exceeds {MAX_ARCHIVE_BYTES} byte safety limit")
        while True:
            chunk = response.read(2 * 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ARCHIVE_BYTES:
                raise RuntimeError("Source archive exceeded safety limit")
            out.write(chunk)
    if not total:
        raise RuntimeError("Downloaded Microsoft source archive is empty")
    return total

def main():
    if OUT.exists() and OUT.stat().st_size and REPORT.exists():
        previous = json.loads(REPORT.read_text(encoding="utf-8"))
        print(json.dumps({"status": "reused_existing_not_overwritten", "output": str(OUT.relative_to(ROOT)),
                          "bytes": OUT.stat().st_size, "feature_count": previous.get("feature_count")}, indent=2))
        return 0

    report = {
        "status": "running",
        "source": "Microsoft Bing Maps satellite-derived building footprints for the Philippines",
        "project_url": "https://github.com/microsoft/IdMyPhBuildingFootprints",
        "source_url": SOURCE_URL,
        "license": "Open Data Commons Open Database License (ODbL)",
        "license_reference": "https://opendatacommons.org/licenses/odbl/1-0/",
        "imagery_vintage": "2016-2020 Maxar imagery (project documentation)",
        "area": "Malate-focused AOI, Manila, Philippines (includes a surrounding buffer)",
        "bbox_wgs84": list(BBOX),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "Full Philippines archive is temporary CI input; only the clipped Malate-area subset and provenance report are committed. Original GLB geometry and coordinates are not modified.",
        "archive_bytes": None, "zip_member": None, "rows_examined": 0, "feature_count": 0, "warnings": []
    }
    with tempfile.TemporaryDirectory(prefix="adam-city-microsoft-malate-") as td:
        archive = Path(td) / "philippines.geojsonl.zip"
        try:
            report["archive_bytes"] = download_archive(archive)
            with zipfile.ZipFile(archive) as zf:
                members = [n for n in zf.namelist() if n.lower().endswith((".geojsonl", ".jsonl", ".geojson"))]
                if not members:
                    raise RuntimeError("No GeoJSONL/GeoJSON data member found in Microsoft archive")
                member = max(members, key=lambda n: zf.getinfo(n).file_size)
                report["zip_member"] = member
                features = []
                with zf.open(member, "r") as stream:
                    for raw in stream:
                        if not raw.strip():
                            continue
                        report["rows_examined"] += 1
                        try:
                            obj = json.loads(raw)
                            if obj.get("type") == "Feature":
                                geom_obj = obj.get("geometry")
                                props = obj.get("properties") or {}
                                original_id = obj.get("id")
                            else:
                                geom_obj = obj.get("geometry") or obj
                                props = obj.get("properties") or {}
                                original_id = obj.get("id") or props.get("id")
                            if not geom_obj or not geom_obj.get("coordinates"):
                                continue
                            bounds = coords_bounds(geom_obj["coordinates"])
                            if bounds[2] < BBOX[0] or bounds[0] > BBOX[2] or bounds[3] < BBOX[1] or bounds[1] > BBOX[3]:
                                continue
                            geom = shape(geom_obj)
                            if geom.is_empty or not geom.intersects(AOI):
                                continue
                            if not geom.is_valid:
                                geom = geom.buffer(0)
                            clipped = geom.intersection(AOI)
                            if clipped.is_empty or clipped.area <= 0:
                                continue
                            new_props = dict(props)
                            new_props.update({
                                "source": "Microsoft IdMyPhBuildingFootprints",
                                "source_imagery_vintage": "2016-2020",
                                "source_license": "ODbL",
                                "source_feature_id": str(original_id) if original_id is not None else None,
                            })
                            features.append({
                                "type": "Feature",
                                "id": f"microsoft-satellite-malate-{len(features)+1}",
                                "geometry": mapping(clipped),
                                "properties": new_props
                            })
                            if len(features) > MAX_OUTPUT_FEATURES:
                                raise RuntimeError("AOI feature count exceeded safety cap; no incomplete output written")
                        except RuntimeError:
                            raise
                        except Exception:
                            continue
            if not features:
                raise RuntimeError("No Microsoft footprints intersected the Malate-focused area")
            collection = {"type": "FeatureCollection", "name": "microsoft-philippines-satellite-footprints-malate", "features": features}
            tmp = OUT.with_suffix(".geojson.part")
            tmp.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            tmp.replace(OUT)
            report.update({"status": "success", "feature_count": len(features),
                           "output_file": str(OUT.relative_to(ROOT)), "output_bytes": OUT.stat().st_size})
        except Exception as exc:
            report["status"] = "failed"
            report["warnings"].append(repr(exc))
            REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            raise
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
