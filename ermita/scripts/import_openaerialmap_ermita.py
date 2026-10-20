# Workflow trigger: verify the open aerial importers against the live public catalog.
#!/usr/bin/env python3
"""Incrementally discover and download openly licensed OpenAerialMap imagery for Ermita.

No API key or account is required for the public catalog. The script stores
source imagery and provenance separately from building footprints. It downloads
only direct raster assets explicitly licensed CC-BY-4.0, bounded to this AOI,
with conservative per-file and total-size limits. It never downloads map tiles.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ermita" / "maps" / "external" / "openaerialmap"
REPORT = OUT / "ermita-openaerialmap-import-report.json"
SEARCH_URL = "https://api.imagery.hotosm.org/stac/search"
BBOX = [120.972, 14.572, 120.994, 14.593]  # west, south, east, north
MAX_ASSET_BYTES = 80 * 1024 * 1024
MAX_TOTAL_NEW_BYTES = 300 * 1024 * 1024
LIMIT = 100
USER_AGENT = "Adam-City-open-imagery-import/1.1"
OUT.mkdir(parents=True, exist_ok=True)


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/geo+json, application/json", "User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers)
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def license_is_cc_by_40(value: object) -> bool:
    normalized = re.sub(r"[ _]", "-", str(value or "").strip().lower())
    return "cc-by-4.0" in normalized or "ccby4.0" in normalized


def raster_extension(href: str, media_type: str | None) -> str | None:
    path = href.split("?", 1)[0].lower()
    for suffix in (".tif", ".tiff", ".jp2", ".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(suffix):
            return ".tif" if suffix == ".tiff" else ".jpg" if suffix == ".jpeg" else suffix
    media = (media_type or "").lower()
    return {
        "image/tiff": ".tif",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/jp2": ".jp2",
        "image/webp": ".webp",
    }.get(media)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    report = {
        "source": "OpenAerialMap / Humanitarian OpenStreetMap Team imagery catalog",
        "catalog_url": SEARCH_URL,
        "license_reference": "https://openaerialmap.org/about/",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "area_of_interest": {"name": "Ermita / Rizal Park, Manila, Philippines", "bbox_wgs84": BBOX},
        "retention_policy": (
            "Only direct raster assets explicitly marked CC-BY-4.0; max 80 MiB per asset "
            "and 300 MiB newly downloaded per run. Existing files are reused, never overwritten."
        ),
        "catalog_items_seen": 0,
        "eligible_assets": [],
        "downloaded": [],
        "reused_existing": [],
        "skipped": [],
        "warnings": [],
    }

    try:
        catalog = request_json(SEARCH_URL, {"bbox": BBOX, "limit": LIMIT})
    except Exception as exc:
        report["status"] = "catalog_request_failed"
        report["warnings"].append(repr(exc))
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    items = catalog.get("features", []) if isinstance(catalog, dict) else []
    report["catalog_items_seen"] = len(items)
    candidates = []
    for item in items:
        props = item.get("properties") or {}
        license_value = props.get("license") or item.get("license")
        assets = item.get("assets") or {}
        for asset_key, asset in assets.items():
            if not isinstance(asset, dict) or not asset.get("href"):
                continue
            href = asset["href"]
            ext = raster_extension(href, asset.get("type"))
            if not ext:
                continue
            size = asset.get("file:size") or asset.get("size")
            record = {
                "item_id": item.get("id"),
                "title": props.get("title") or item.get("id"),
                "datetime": props.get("datetime"),
                "gsd_m": props.get("gsd"),
                "item_bbox_wgs84": item.get("bbox"),
                "producer": props.get("oam:producer_name"),
                "license": license_value,
                "asset_key": asset_key,
                "asset_href": href,
                "asset_type": asset.get("type"),
                "asset_size": size,
                "extension": ext,
            }
            if not license_is_cc_by_40(license_value):
                report["skipped"].append({"item_id": record["item_id"], "asset_key": asset_key,
                                          "reason": "License not explicitly CC-BY-4.0; no download."})
                continue
            if isinstance(size, (int, float)) and size > MAX_ASSET_BYTES:
                report["skipped"].append({"item_id": record["item_id"], "asset_key": asset_key,
                                          "reason": "Catalog size exceeds 80 MiB."})
                continue
            candidates.append(record)

    # Prefer better spatial resolution and then newer acquisition dates.
    candidates.sort(key=lambda x: (x.get("gsd_m") if isinstance(x.get("gsd_m"), (int, float)) else 999999,
                                   x.get("datetime") or ""))
    report["eligible_assets"] = [
        {k: v for k, v in item.items() if k != "asset_href"} for item in candidates
    ]

    new_bytes = 0
    seen_targets: set[str] = set()
    for item in candidates:
        if len(report["downloaded"]) + len(report["reused_existing"]) >= LIMIT:
            report["warnings"].append("Reached the per-run cap of 100 assets.")
            break
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(item.get("item_id") or "image"))[:70]
        safe_key = re.sub(r"[^A-Za-z0-9_-]+", "_", str(item.get("asset_key") or "asset"))[:30]
        target = OUT / f"ermita-{safe_id}-{safe_key}{item['extension']}"
        if str(target) in seen_targets:
            continue
        seen_targets.add(str(target))
        if target.exists() and target.stat().st_size > 0:
            report["reused_existing"].append({
                "item_id": item["item_id"], "asset_key": item["asset_key"],
                "repository_path": str(target.relative_to(ROOT)).replace("\\", "/"),
                "bytes": target.stat().st_size, "sha256": sha256_file(target),
            })
            continue
        if new_bytes >= MAX_TOTAL_NEW_BYTES:
            report["skipped"].append({"item_id": item["item_id"], "asset_key": item["asset_key"],
                                      "reason": "Reached 300 MiB total new-download cap."})
            continue
        try:
            req = Request(item["asset_href"], headers={"User-Agent": USER_AGENT})
            digest = hashlib.sha256()
            downloaded = 0
            with urlopen(req, timeout=90) as response, target.open("wb") as stream:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_ASSET_BYTES:
                    raise ValueError("Remote Content-Length exceeds 80 MiB.")
                final_url = response.geturl()
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > MAX_ASSET_BYTES:
                        raise ValueError("Downloaded asset exceeded 80 MiB.")
                    if new_bytes + downloaded > MAX_TOTAL_NEW_BYTES:
                        raise ValueError("Run would exceed 300 MiB total new downloads.")
                    digest.update(chunk)
                    stream.write(chunk)
            if downloaded == 0:
                raise ValueError("Empty response body.")
            new_bytes += downloaded
            report["downloaded"].append({
                "item_id": item["item_id"], "title": item["title"], "datetime": item["datetime"],
                "gsd_m": item["gsd_m"], "item_bbox_wgs84": item["item_bbox_wgs84"],
                "producer": item["producer"], "license": item["license"],
                "asset_key": item["asset_key"], "asset_type": item["asset_type"],
                "repository_path": str(target.relative_to(ROOT)).replace("\\", "/"),
                "bytes": downloaded, "sha256": digest.hexdigest(), "final_url": final_url,
                "attribution": "OpenAerialMap contributor and original provider; see item metadata",
            })
        except Exception as exc:
            target.unlink(missing_ok=True)
            report["warnings"].append(f"{item.get('item_id')} / {item.get('asset_key')}: {exc!r}")

    report["new_bytes_downloaded"] = new_bytes
    report["status"] = "success" if (report["downloaded"] or report["reused_existing"]) else "no_eligible_assets"
    if not candidates:
        report["warnings"].append(
            "No direct raster asset explicitly licensed CC-BY-4.0 was found in the AOI. "
            "No imagery tiles or proprietary satellite services were copied."
        )
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
