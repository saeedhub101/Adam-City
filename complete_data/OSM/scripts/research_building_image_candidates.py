#!/usr/bin/env python3
"""Discover geotagged Wikimedia Commons image candidates near unresolved buildings.

Candidates are evidence leads only. This script never modifies geometry, GLBs, or
building attributes and does not claim that nearby imagery depicts the target.
"""
from __future__ import annotations

import concurrent.futures
import csv
import json
import threading
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
USER_AGENT = "AdamCityBuildingResearch/1.1 (building imagery candidate discovery; GitHub repository saeedhub101/Adam-City)"
FIELDS = [
    "source_feature_id", "part", "status", "latitude", "longitude",
    "area_m2", "source_name_or_brand", "image_title", "image_page",
    "thumbnail_url", "image_url", "distance_m", "license_short_name",
    "license_url", "artist", "description", "review_decision", "review_notes",
]
_rate_lock = threading.Lock()
_last_request_start = 0.0


def request_json(params: dict) -> dict:
    global _last_request_start
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error = None
    for attempt in range(5):
        # Pace request starts globally while allowing network latency to overlap.
        with _rate_lock:
            wait = 0.18 - (time.monotonic() - _last_request_start)
            if wait > 0:
                time.sleep(wait)
            _last_request_start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = min(float(retry_after), 30) if retry_after else min(2 ** attempt, 16)
            except ValueError:
                delay = min(2 ** attempt, 16)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(min(2 ** attempt, 16))
    raise RuntimeError(f"Commons API request failed after retries: {last_error}")


def metadata_value(meta: dict, key: str) -> str:
    value = meta.get(key) or {}
    return str(value.get("value", ""))[:500] if isinstance(value, dict) else ""


def research_one(building: dict) -> tuple[str, list[dict], str | None]:
    feature_id = building.get("source_feature_id", "")
    try:
        data = request_json({
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "geosearch",
            "ggscoord": f'{building["latitude"]}|{building["longitude"]}',
            "ggsradius": "75",
            "ggslimit": "5",
            "ggsnamespace": "6",
            "prop": "coordinates|imageinfo",
            "colimit": "1",
            "iiprop": "url|extmetadata",
            "iiurlwidth": "600",
        })
        pages = (data.get("query") or {}).get("pages") or []
        rows = []
        for page in pages:
            coords = (page.get("coordinates") or [{}])[0]
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            rows.append({
                "source_feature_id": feature_id,
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
                "license_short_name": metadata_value(meta, "LicenseShortName"),
                "license_url": metadata_value(meta, "LicenseUrl"),
                "artist": metadata_value(meta, "Artist"),
                "description": metadata_value(meta, "ImageDescription") or metadata_value(meta, "ObjectName"),
                "review_decision": "",
                "review_notes": "",
            })
        return feature_id, rows, None
    except Exception as exc:
        return feature_id, [], str(exc)[:500]


def save_outputs(queue_count: int, output: list[dict], no_results: int, errors: list[dict], complete: bool) -> None:
    output.sort(key=lambda row: (
        row["source_feature_id"], float(row["distance_m"] or 1e12), row["image_title"]
    ))
    OUT_JSON.write_text(json.dumps({
        "title": "Unverified Wikimedia Commons image candidates near unresolved Adam-City buildings",
        "candidate_policy": "Proximity is not identity. Every image must be visually inspected and verified before use.",
        "complete": complete,
        "queue_buildings": queue_count,
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
        "# Wikimedia Commons image candidates", "",
        "Discovery aid for unresolved-building visual review. Nearby geotagged files are not verified depictions of target buildings.", "",
        "## Results", "",
        f"- Status: **{'complete' if complete else 'partial checkpoint'}**",
        f"- Buildings queried: **{queue_count}**",
        f"- Image candidate records: **{len(output)}**",
        f"- Buildings with at least one candidate: **{unique_buildings}**",
        f"- Buildings with no geotagged result: **{no_results}**",
        f"- Requests with errors so far: **{len(errors)}**", "",
        "## Mandatory verification before use", "",
        "- Open each candidate's image page and inspect the actual image; do not rely on its filename or proximity alone.",
        "- Confirm that the visible building and viewpoint match the target location.",
        "- Check the license and attribution requirements on the source page.",
        "- Record review_decision and review_notes only after inspection.",
        "- This process does not modify GLBs, geometry, positions, heights, IDs, colors, or materials.", "",
    ]
    if errors:
        report += ["## Request errors", ""] + [f"- {e['source_feature_id']}: {e['error']}" for e in errors[:50]] + [""]
    OUT_MD.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    with QUEUE.open(encoding="utf-8-sig", newline="") as handle:
        queue = list(csv.DictReader(handle))

    output: list[dict] = []
    errors: list[dict] = []
    no_results = 0
    completed = 0
    # Four workers hide network latency; a shared limiter still paces API request starts.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(research_one, building) for building in queue]
        for future in concurrent.futures.as_completed(futures):
            feature_id, rows, error = future.result()
            completed += 1
            output.extend(rows)
            if not rows and error is None:
                no_results += 1
            if error:
                errors.append({"source_feature_id": feature_id, "error": error})
            if completed % 25 == 0 or completed == len(queue):
                save_outputs(len(queue), output, no_results, errors, complete=(completed == len(queue)))
                print(json.dumps({
                    "completed": completed, "total": len(queue), "image_candidates": len(output),
                    "buildings_without_geotagged_results": no_results, "request_errors": len(errors),
                }), flush=True)

    save_outputs(len(queue), output, no_results, errors, complete=True)
    print(json.dumps({
        "queue_buildings": len(queue),
        "image_candidates": len(output),
        "buildings_with_candidates": len({row["source_feature_id"] for row in output}),
        "buildings_without_geotagged_results": no_results,
        "request_errors": len(errors),
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
