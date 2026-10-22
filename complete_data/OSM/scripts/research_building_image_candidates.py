#!/usr/bin/env python3
"""Discover geotagged Wikimedia Commons image candidates near unresolved buildings.

Candidates are evidence leads only. This script never modifies geometry, GLBs, or
building attributes and does not claim that nearby imagery depicts the target.
"""
from __future__ import annotations

import concurrent.futures
import csv
import json
import subprocess
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
PROGRESS = PARTS / "building-image-candidates-progress.jsonl"
BATCH_SIZE = 300
CHECKPOINT_EVERY = 10
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


def load_progress() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    if PROGRESS.exists():
        with PROGRESS.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                    if record.get("source_feature_id"):
                        latest[record["source_feature_id"]] = record
                except json.JSONDecodeError:
                    # Ignore a truncated line; the last committed checkpoint remains valid.
                    continue
    return latest


def write_progress(records: dict[str, dict]) -> None:
    tmp = PROGRESS.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for record in records.values():
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        import os
        os.fsync(handle.fileno())
    tmp.replace(PROGRESS)


def push_checkpoint() -> None:
    # Persist the durable progress ledger to main during the run.
    subprocess.run(["git", "add", str(PROGRESS.relative_to(ROOT))], cwd=ROOT, check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if staged.returncode == 0:
        return
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", "Checkpoint building image research progress"], cwd=ROOT, check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)


def main() -> None:
    with QUEUE.open(encoding="utf-8-sig", newline="") as handle:
        queue = list(csv.DictReader(handle))

    records = load_progress()
    completed_ids = {fid for fid, record in records.items() if not record.get("error")}
    pending = [b for b in queue if b.get("source_feature_id", "") not in completed_ids]
    batch = pending[:BATCH_SIZE]
    if not batch:
        output = [row for rec in records.values() if not rec.get("error") for row in rec.get("rows", [])]
        errors = [{"source_feature_id": fid, "error": rec["error"]} for fid, rec in records.items() if rec.get("error")]
        no_results = sum(1 for rec in records.values() if not rec.get("error") and not rec.get("rows"))
        save_outputs(len(queue), output, no_results, errors, complete=(len(completed_ids) >= len(queue)))
        print(json.dumps({"message":"No pending buildings in this batch", "completed_total":len(completed_ids), "queue_total":len(queue)}), flush=True)
        return

    print(json.dumps({"batch_size":len(batch), "pending_before_batch":len(pending), "completed_before_batch":len(completed_ids)}), flush=True)
    processed_this_batch = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(research_one, building) for building in batch]
        for future in concurrent.futures.as_completed(futures):
            feature_id, rows, error = future.result()
            records[feature_id] = {
                "source_feature_id": feature_id,
                "rows": rows,
                "error": error,
                "result": "error" if error else ("candidates" if rows else "no_geotagged_results"),
            }
            processed_this_batch += 1
            write_progress(records)
            if processed_this_batch % CHECKPOINT_EVERY == 0:
                push_checkpoint()
                done = sum(1 for rec in records.values() if not rec.get("error"))
                print(json.dumps({"batch_completed":processed_this_batch, "batch_size":len(batch), "completed_total":done, "queue_total":len(queue), "checkpoint_pushed":True}), flush=True)

    # Persist any remaining results before generating reports.
    push_checkpoint()
    output = [row for rec in records.values() if not rec.get("error") for row in rec.get("rows", [])]
    errors = [{"source_feature_id": fid, "error": rec["error"]} for fid, rec in records.items() if rec.get("error")]
    no_results = sum(1 for rec in records.values() if not rec.get("error") and not rec.get("rows"))
    completed_total = sum(1 for rec in records.values() if not rec.get("error"))
    save_outputs(len(queue), output, no_results, errors, complete=(completed_total >= len(queue)))
    for path in (OUT_JSON, OUT_CSV, OUT_MD):
        subprocess.run(["git", "add", str(path.relative_to(ROOT))], cwd=ROOT, check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if staged.returncode != 0:
        subprocess.run(["git", "commit", "-m", "Update building image candidate results"], cwd=ROOT, check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print(json.dumps({
        "batch_processed": processed_this_batch,
        "completed_total": completed_total,
        "queue_buildings": len(queue),
        "image_candidates": len(output),
        "buildings_with_candidates": len({row["source_feature_id"] for row in output}),
        "buildings_without_geotagged_results": no_results,
        "request_errors_retryable": len(errors),
        "next_run_will_resume_from_progress_ledger": True
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
