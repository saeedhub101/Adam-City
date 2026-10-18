#!/usr/bin/env python3
"""Discover openly licensed OpenAerialMap imagery intersecting Ermita, Manila.

The importer deliberately downloads only an explicitly CC-BY-4.0 item and only
when the chosen visual asset is <= 80 MiB. It never scrapes Esri display tiles.
"""
from __future__ import annotations
import hashlib, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ermita" / "maps" / "external" / "openaerialmap"
REPORT = OUT / "ermita-openaerialmap-import-report.json"
SEARCH_URL = "https://api.imagery.hotosm.org/stac/search"
BBOX = [120.972, 14.572, 120.994, 14.593]
MAX_BYTES = 80 * 1024 * 1024
OUT.mkdir(parents=True, exist_ok=True)

def request_json(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Accept":"application/geo+json, application/json",
                 "Content-Type":"application/json", "User-Agent":"Adam-City-open-imagery-import/1.0"})
    with urlopen(req, timeout=45) as r:
        return json.load(r)

def main():
    report = {
        "source": "OpenAerialMap / Humanitarian OpenStreetMap Team imagery API",
        "catalog_api": SEARCH_URL,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "area_of_interest": {"name":"Rizal Park / Ermita, Manila, Philippines",
                             "bbox_wgs84": BBOX},
        "retention_policy": "Only explicitly CC-BY-4.0 assets; <= 80 MiB; no Esri display tiles.",
        "license_reference": "https://openaerialmap.org/about/",
        "downloaded": [], "candidates": [], "warnings": []
    }
    try:
        data = request_json(SEARCH_URL, {"bbox": BBOX, "limit": 100})
        items = data.get("features", []) if isinstance(data, dict) else []
        report["catalog_item_count"] = len(items)
    except Exception as e:
        report["warnings"].append("Catalog search failed: " + repr(e))
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    eligible = []
    for item in items:
        p = item.get("properties") or {}
        license_value = str(p.get("license") or item.get("license") or "").strip()
        assets = item.get("assets") or {}
        asset = next((assets[k] for k in ("visual", "image", "data", "analytic")
                      if isinstance(assets.get(k), dict) and assets[k].get("href")), None)
        candidate = {
            "id": item.get("id"), "title": p.get("title") or p.get("constellation") or item.get("id"),
            "datetime": p.get("datetime"), "gsd_m": p.get("gsd"),
            "license": license_value, "asset_key": None if asset is None else next(
                (k for k in ("visual","image","data","analytic") if assets.get(k) is asset), None),
            "asset_href": None if asset is None else asset.get("href"),
            "asset_type": None if asset is None else asset.get("type"),
            "asset_size": None if asset is None else asset.get("file:size"),
        }
        report["candidates"].append({k:v for k,v in candidate.items() if k != "asset_href"})
        normalized = license_value.lower().replace("_","-").replace(" ","")
        if asset and ("cc-by-4.0" in normalized or "ccby4.0" in normalized):
            eligible.append((candidate, asset))
    eligible.sort(key=lambda pair: (pair[0].get("gsd_m") or 999999, pair[0].get("datetime") or ""), reverse=False)

    for candidate, asset in eligible:
        href = asset.get("href", "")
        # Prefer direct downloadable imagery formats, not thumbnail or tile endpoints.
        path = href.split("?", 1)[0].lower()
        ext = ".tif" if path.endswith((".tif", ".tiff")) else ".jp2" if path.endswith(".jp2") else ".jpg" if path.endswith((".jpg", ".jpeg")) else ".png" if path.endswith(".png") else None
        if not ext:
            report["warnings"].append(f"Skipped {candidate['id']}: no recognized direct raster file extension.")
            continue
        if isinstance(candidate.get("asset_size"), (int, float)) and candidate["asset_size"] > MAX_BYTES:
            report["warnings"].append(f"Skipped {candidate['id']}: catalog asset size exceeds 80 MiB.")
            continue
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(candidate.get("id") or "image"))[:80]
        target = OUT / f"ermita-{safe_id}{ext}"
        try:
            req = Request(href, headers={"User-Agent":"Adam-City-open-imagery-import/1.0"})
            digest = hashlib.sha256()
            total = 0
            with urlopen(req, timeout=60) as response, target.open("wb") as f:
                final_url = response.geturl()
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_BYTES:
                    raise ValueError("Remote asset exceeds 80 MiB limit.")
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("Downloaded asset exceeded 80 MiB limit.")
                    digest.update(chunk); f.write(chunk)
            if total == 0:
                target.unlink(missing_ok=True)
                raise ValueError("Downloaded asset was empty.")
            candidate.update({"repository_path":str(target.relative_to(ROOT)).replace("\\","/"),
                              "downloaded_bytes":total,"sha256":digest.hexdigest(),"final_url":final_url})
            report["downloaded"].append(candidate)
            break
        except Exception as e:
            target.unlink(missing_ok=True)
            report["warnings"].append(f"Download failed for {candidate['id']}: {repr(e)}")

    if not report["downloaded"]:
        report["warnings"].append("No qualifying, directly downloadable CC-BY-4.0 raster <= 80 MiB was found in the Ermita search area. No image was fabricated or sourced from Esri tiles.")
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
