#!/usr/bin/env python3
"""Import the official DPWH national-road network intersecting the Ermita project AOI.

Source service: DPWH Road & Bridge Information Application (RBIA), processed by
GIAS-SD, Planning Service. Published through ArcGIS FeatureServer.
Only national roads are included; local streets remain covered by the project's
OpenStreetMap import. Output is clipped to a documented rectangular AOI.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from shapely.geometry import box, shape, mapping
from shapely.ops import transform as transform_geometry
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "ermita" / "maps" / "external"
OUT_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = (
    "https://services1.arcgis.com/IwZZTMxZCmAmFYvF/ArcGIS/rest/services/"
    "Road_Classification/FeatureServer/1/query"
)
# Broad Ermita / Rizal Park coverage in WGS84. This is a project clip window,
# not an official administrative boundary.
AOI = box(120.955, 14.555, 121.005, 14.610)
FIELDS = [
    "OBJECTID", "ROAD_NAME", "SECTION_ID", "DIRECTION", "SEC_LENGTH",
    "ROAD_SEC_CLASS", "ROUTE_NO", "ROAD_ID", "ROUTE_ID", "DEO", "REGION",
    "PROVINCE", "SOURCE", "REMARKS",
]
HEADERS = {"User-Agent": "Adam-City-Open-Geodata-Importer/1.0 (GitHub Actions)"}


def main() -> None:
    features = []
    offset = 0
    page_size = 1000
    session = requests.Session()
    session.headers.update(HEADERS)
    while True:
        params = {
            "where": "1=1",
            "geometry": f"{AOI.bounds[0]},{AOI.bounds[1]},{AOI.bounds[2]},{AOI.bounds[3]}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": ",".join(FIELDS),
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "OBJECTID",
        }
        response = session.get(BASE_URL, params=params, timeout=90)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"ArcGIS query error: {data['error']}")
        batch = data.get("features", [])
        for feature in batch:
            geom_data = feature.get("geometry")
            if not geom_data:
                continue
            geom = shape(geom_data).intersection(AOI)
            if geom.is_empty:
                continue
            props = feature.get("properties") or feature.get("attributes") or {}
            props["data_source"] = "DPWH RBIA / GIAS-SD via ArcGIS Road_Classification FeatureServer layer 1"
            props["source_vintage"] = "Service metadata reports data as of August 2026"
            features.append({
                "type": "Feature",
                "id": props.get("OBJECTID"),
                "geometry": mapping(geom),
                "properties": props,
            })
        if len(batch) < page_size or not data.get("exceededTransferLimit", False):
            break
        offset += len(batch)
        time.sleep(0.2)

    # Deduplicate features defensively if the service's paging changes.
    unique = {}
    for feature in features:
        key = str(feature.get("id") or (
            feature["properties"].get("ROAD_ID"),
            feature["properties"].get("SECTION_ID"),
            feature["properties"].get("ROAD_NAME"),
        ))
        unique[key] = feature
    features = list(unique.values())
    features.sort(key=lambda f: str(f.get("id", "")))

    collection = {
        "type": "FeatureCollection",
        "name": "dpwh_national_roads_ermita_aoi",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    output_path = OUT_DIR / "dpwh-national-roads-ermita.geojson"
    output_path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    classes = {}
    road_names = set()
    for f in features:
        p = f["properties"]
        cls = str(p.get("ROAD_SEC_CLASS") or "unknown")
        classes[cls] = classes.get(cls, 0) + 1
        if p.get("ROAD_NAME"):
            road_names.add(str(p["ROAD_NAME"]))
    report = {
        "status": "success",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_agency": "Department of Public Works and Highways (DPWH), Philippines",
        "source_database": "Road & Bridge Information Application (RBIA), Statistics Division, Planning Service; processed by GIAS-SD",
        "source_url": "https://services1.arcgis.com/IwZZTMxZCmAmFYvF/ArcGIS/rest/services/Road_Classification/FeatureServer/1",
        "source_layer": "National Road Network (layer 1)",
        "source_vintage_note": "ArcGIS layer metadata states the road data are as of August 2026; verify metadata on future refreshes.",
        "geometry": "Polyline, clipped to project AOI",
        "output_crs": "WGS84 longitude/latitude (GeoJSON CRS84)",
        "aoi_wgs84_bbox": list(AOI.bounds),
        "feature_count": len(features),
        "distinct_named_roads": len(road_names),
        "road_section_class_counts": classes,
        "output_file": str(output_path.relative_to(ROOT)),
        "scope_limitations": [
            "This is the national-road network only, not a complete local-street inventory.",
            "No road width, sidewalk, lane marking, curb, or intersection-surface geometry is supplied by this layer.",
            "Use the project's OpenStreetMap layer for local streets and finer mapped road detail.",
            "The AOI is a rectangular project clip window, not an official Ermita boundary.",
        ],
        "attribution": "Source: DPWH RBIA database; processed into geospatial data by GIAS-SD, Planning Service. Retain this attribution when reusing the data.",
        "service_metadata_checked": "https://services1.arcgis.com/IwZZTMxZCmAmFYvF/ArcGIS/rest/services/Road_Classification/FeatureServer/1",
    }
    report_path = OUT_DIR / "dpwh-national-roads-import-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "feature_count": len(features),
        "distinct_named_roads": len(road_names),
        "classes": classes,
        "geojson_bytes": output_path.stat().st_size,
        "report": str(report_path.relative_to(ROOT)),
    }, indent=2))
    if not features:
        raise RuntimeError("DPWH service returned zero roads in the project AOI; refusing to treat an empty file as a successful import.")


if __name__ == "__main__":
    main()
