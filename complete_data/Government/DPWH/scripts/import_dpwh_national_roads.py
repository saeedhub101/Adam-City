#!/usr/bin/env python3
"""Batch-import public DPWH road and bridge GIS layers for Ermita/Rizal Park.

Downloads official national-road geometry, road pavement surface attributes,
lane-count records and bridge inventory where the public ArcGIS services return
features within the project AOI. Local streets and traffic signs remain covered
by the existing OSM importer; building footprints and street-level imagery are
handled by existing project importers.
"""
from __future__ import annotations
import json, time
from datetime import datetime, timezone
from pathlib import Path
import requests
from shapely.geometry import box, shape, mapping

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "ermita" / "maps" / "external"
OUT_DIR.mkdir(parents=True, exist_ok=True)
AOI = box(120.955, 14.555, 121.005, 14.610)  # project clip window, not an official boundary
BASE = "https://services1.arcgis.com/IwZZTMxZCmAmFYvF/ArcGIS/rest/services"
SOURCES = [
    {
        "key": "dpwh-national-roads",
        "title": "DPWH National Road Network",
        "url": f"{BASE}/Road_Classification/FeatureServer/1/query",
        "vintage": "August 2026 per layer metadata",
        "agency": "DPWH RBIA / Statistics Division, Planning Service; geospatial processing by GIAS-SD",
    },
    {
        "key": "dpwh-road-surface-type",
        "title": "DPWH Road Surface Type",
        "url": f"{BASE}/Surface_Type/FeatureServer/0/query",
        "vintage": "January 2026 per layer metadata",
        "agency": "DPWH RBIA / Statistics Division, Planning Service; geospatial processing by GIAS-SD",
    },
    {
        "key": "dpwh-number-of-lanes",
        "title": "DPWH Number of Lanes",
        "url": f"{BASE}/Number_of_Lanes/FeatureServer/0/query",
        "vintage": "June 2020 per service metadata",
        "agency": "DPWH RBIA / Statistics Division, Planning Service; geospatial processing by GIAS-SD",
    },
    {
        "key": "dpwh-bridge-inventory",
        "title": "DPWH Detailed Bridge Inventory (Bridge Needs Ratio layer)",
        "url": f"{BASE}/Detailed_Bridge_Inventory_Final/FeatureServer/2/query",
        "vintage": "October 2025 per layer metadata",
        "agency": "DPWH RBIA and Bridge Management System; geospatial data by GIAS-SD",
    },
]
HEADERS = {"User-Agent": "Adam-City-Open-Geodata-Importer/1.1 (GitHub Actions)"}

def fetch_layer(session, source):
    all_features = []
    offset = 0
    page_size = 1000
    while True:
        params = {
            "where": "1=1",
            "geometry": f"{AOI.bounds[0]},{AOI.bounds[1]},{AOI.bounds[2]},{AOI.bounds[3]}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "OBJECTID",
        }
        response = session.get(source["url"], params=params, timeout=90)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"{source['key']} ArcGIS error: {data['error']}")
        batch = data.get("features", [])
        for feature in batch:
            raw_geometry = feature.get("geometry")
            if not raw_geometry:
                continue
            geom = shape(raw_geometry).intersection(AOI)
            if geom.is_empty:
                continue
            props = dict(feature.get("properties") or feature.get("attributes") or {})
            all_features.append({
                "type": "Feature",
                "id": props.get("OBJECTID", props.get("objectid")),
                "geometry": mapping(geom),
                "properties": props,
            })
        if len(batch) < page_size or not data.get("exceededTransferLimit", False):
            break
        offset += len(batch)
        time.sleep(0.2)
    unique = {}
    for f in all_features:
        k = str(f.get("id") if f.get("id") is not None else json.dumps(f["geometry"], sort_keys=True))
        unique[k] = f
    return list(unique.values())

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    reports = []
    failures = []
    for source in SOURCES:
        try:
            features = fetch_layer(session, source)
            if not features:
                raise RuntimeError("Service returned no features inside the AOI")
            collection = {
                "type": "FeatureCollection",
                "name": source["key"],
                "features": features,
            }
            out_path = OUT_DIR / f"{source['key']}-ermita.geojson"
            out_path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            reports.append({
                "source_id": source["key"],
                "title": source["title"],
                "source_url": source["url"].removesuffix("/query"),
                "agency": source["agency"],
                "source_vintage": source["vintage"],
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "clip_bbox_wgs84": list(AOI.bounds),
                "geometry": "source geometry clipped to project AOI",
                "output_crs": "WGS84 longitude/latitude",
                "feature_count": len(features),
                "output_file": str(out_path.relative_to(ROOT)),
                "attribution": source["agency"],
            })
        except Exception as exc:
            failures.append({"source_id": source["key"], "source_url": source["url"].removesuffix("/query"), "error": str(exc)})
    report = {
        "status": "success" if reports else "failed",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_area": "Ermita and Rizal Park, Manila; rectangular clip window",
        "sources_attempted": len(SOURCES),
        "sources_imported": len(reports),
        "imports": reports,
        "failures": failures,
        "limitations": [
            "DPWH national-road geometry is not a complete local-street dataset; use the existing OSM layer for local streets.",
            "Surface and lane-count layers may be older than the national road network and may not cover every local road.",
            "Bridge inventory only describes bridges represented by the national-road inventory.",
            "This import does not claim to provide building footprints, facades, signs, or orthophotos; those are handled by other project data pipelines or require separate source access.",
            "The clip window is a project area-of-interest rectangle, not an official Ermita administrative boundary.",
        ],
    }
    report_path = OUT_DIR / "dpwh-road-bridge-batch-import-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"sources_imported": len(reports), "imports": [{"id": x["source_id"], "count": x["feature_count"], "file": x["output_file"]} for x in reports], "failures": failures, "report": str(report_path.relative_to(ROOT))}, indent=2))
    if not reports:
        raise RuntimeError("No DPWH layers imported successfully; see report for service errors.")

if __name__ == "__main__":
    main()
