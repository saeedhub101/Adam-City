#!/usr/bin/env python3
"""Discover geotagged Wikimedia Commons image candidates near unresolved buildings.

Candidates are evidence leads only. This script never modifies geometry, GLBs, or
building attributes and does not claim that nearby imagery depicts the target.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARTS = ROOT / "complete_data/OSM/data/buildings/parts"
QUEUE = PARTS / "building-visual-research-queue.csv"
OUT_JSON = PARTS / "building-image-candidates.json"
OUT_CSV = PARTS / "building-image-candidates.csv"
OUT_MD = PARTS / "BUILDING-IMAGE-CANDIDATES.md"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "AdamCityBuildingResearch/1.0 (building imagery candidate discovery; GitHub repository saeedhub101/Adam-City)"
FIELDS = [
    "source_feature_id", "part", "status", "latitude", "longitude",
    "area_m2", "source_name_or_brand", "image_title", "image_page",
    "thumbnail_url", "image_url", "distance_m", "license_short_name",
    "license_url", "artist", "description", "review_decision", "review_notes",
]


def request_json(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(min(2 ** attempt, 16))
    raise RuntimeError(f"Wikimedia Commons API request failed after retries: {last_error}")


def main() -> None:
    with QUEUE.open(encoding="utf-8-sig", newline="") as handle:
        queue = list(csv.DictReader(handle))

    output = []
    no_results = 0
    errors = []
    for index, building in enumerate(queue, 1):
        try:
            data = request_json({
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "generator": "geosearch",
                "ggscoord": f'{building["latitude"]}|{building["longitude"]}',
                "ggsradius": "100",
                "ggslimit": "10",
                "ggsnamespace": "6",
                "prop": "coordinates|imageinfo",
                "colimit": "1",
                "iiprop": "url|extmetadata",
                "iiurlwidth": "600",
            })
            pages = (data.get("query") or {}).get("pages") or []
            if not pages:
                no_results += 1
            for page in pages:
                coords = (page.get("coordinates") or [{}])[0]
                info = (page.get("imageinfo") or [{}])[0]
                meta = info.get("extmetadata") or {}
                def meta_value(key: str) -> str:
                    value = meta.get(key) or {}
                    return str(value.get("value", ""))[:1500] if isinstance(value, dict) else ""
                output.append({
                    "source_feature_id": building.get("source_feature_id", ""),
                    "part": building.get("part", ""),
                    "status": building.get("status", ""),
                    "latitude": building.get("latitude", ""),
                    "longitude": building.get("longitude", ""),
                    "area_m2": building.get("area_m2", ""),
                    "source_name_or_brand": building.get("source_name_or_brand", ""),
                    "image_title": page.get("title", ""),
                    "image_page": info.get("descriptionurl", ""),
                    "thumbnail_url": info.get("thumburl", ""),
                    "image_url": info.get("url", ""),
                    "distance_m": coords.get("dist", ""),
                    "license_short_name": meta_value("LicenseShortName"),
                    "license_url": meta_value("LicenseUrl"),
                    "artist": meta_value("Artist"),
                    "description": meta_value("ImageDescription") or meta_value("ObjectName"),
                    "review_decision": "",
                    "review_notes": "",
                })
        except Exception as exc:
            errors.append({"source_feature_id": building.get("source_feature_id", ""), "error": str(exc)[:500]})
        # Stay polite to Commons and avoid hammering the public API.
        if index < len(queue):
            time.sleep(0.12)

    output.sort(key=lambda row: (
        row["source_feature_id"], float(row["distance_m"] or 1e12), row["image_title"]
    ))
    OUT_JSON.write_text(json.dumps({
        "title": "Unverified Wikimedia Commons image candidates near unresolved Adam-City buildings",
        "candidate_policy": "Proximity is not identity. Every image must be visually inspected and verified before use.",
        "queue_buildings": len(queue),
        "image_candidates": len(output),
        "buildings_without_geotagged_results": no_results,
        "request_errors": errors,
        "candidates": output,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)

    unique_buildings = len({row["source_feature_id"] for row in output})
    report = [
        "# Wikimedia Commons image candidates",
        "",
        "This is a discovery aid for the unresolved-building visual review queue. Results are nearby geotagged Commons files, not verified depictions of the target building.",
        "",
        "## Results",
        "",
        f"- Buildings queried: **{len(queue)}**",
        f"- Image candidate records: **{len(output)}**",
        f"- Buildings with at least one candidate: **{unique_buildings}**",
        f"- Buildings with no geotagged result: **{no_results}**",
        f"- Requests with errors: **{len(errors)}**",
        "",
        "## Mandatory verification before use",
        "",
        "- Open each candidate's image page and inspect the actual image; do not rely on its filename or proximity alone.",
        "- Confirm that the visible building and viewpoint match the target location.",
        "- Check the license and attribution requirements on the source page.",
        "- Record review_decision and review_notes only after inspection.",
        "- This process does not modify GLBs, geometry, positions, heights, IDs, colors, or materials.",
        "",
    ]
    if errors:
        report += ["## Request errors", ""] + [f"- {e['source_feature_id']}: {e['error']}" for e in errors[:50]] + [""]
    OUT_MD.write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({
        "queue_buildings": len(queue),
        "image_candidates": len(output),
        "buildings_with_candidates": unique_buildings,
        "buildings_without_geotagged_results": no_results,
        "request_errors": len(errors),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
