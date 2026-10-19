#!/usr/bin/env python3
"""Download licensed Wikimedia Commons reference photos for Ermita/Malate buildings.

Only images with usable file pages and license/author metadata are retained.
Exact building matches are distinguished from neighborhood-level references.
Existing files are not downloaded again.
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ermita" / "buildings" / "reference_photos"
CATALOG = ROOT / "ermita" / "buildings" / "reference_photos_catalog.json"
USER_AGENT = "AdamCityReferencePhotoImporter/1.0 (educational 3D city project)"
API = "https://commons.wikimedia.org/w/api.php"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})
OUT.mkdir(parents=True, exist_ok=True)

# Queries are intentionally specific first. Area-level searches are clearly marked
# as unverified references and must not be treated as a confirmed building match.
QUERIES = [
    ("Philippine General Hospital Manila facade", "building_candidate"),
    ("Manila Doctors Hospital building", "building_candidate"),
    ("National Museum of Fine Arts Manila exterior", "building_candidate"),
    ("Manila City Hall exterior building", "building_candidate"),
    ("Rizal Memorial Medical Center building Manila", "building_candidate"),
    ("Ermita Manila buildings street", "area_reference"),
    ("Malate Manila buildings street", "area_reference"),
    ("University of the Philippines Manila building", "building_candidate"),
    ("St Paul University Manila building", "building_candidate"),
]

def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return value[:90] or "commons-image"

def api(params):
    response = SESSION.get(API, params={"format": "json", **params}, timeout=45)
    response.raise_for_status()
    return response.json()

def main():
    existing = {}
    if CATALOG.exists():
        try:
            old = json.loads(CATALOG.read_text(encoding="utf-8"))
            for item in old.get("images", []):
                existing[item.get("commons_page")] = item
        except Exception:
            pass

    found = {}
    errors = []
    for query, match_type in QUERIES:
        try:
            data = api({
                "action": "query",
                "generator": "search",
                "gsrsearch": "filetype:bitmap " + query,
                "gsrnamespace": 6,
                "gsrlimit": 8,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "iiurlwidth": 1000,
            })
            pages = (data.get("query") or {}).get("pages") or {}
            for page in pages.values():
                infos = page.get("imageinfo") or []
                if not infos:
                    continue
                info = infos[0]
                meta = info.get("extmetadata") or {}
                def plain(key):
                    raw = meta.get(key, {}).get("value", "")
                    return re.sub(r"<[^>]+>", " ", str(raw)).replace("&nbsp;", " ").strip()
                license_name = plain("LicenseShortName")
                license_url = plain("LicenseUrl")
                artist = plain("Artist")
                if not license_name or not license_url:
                    continue
                title = page.get("title", "image")
                page_url = "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_")
                key = page_url
                if key not in found:
                    found[key] = {
                        "commons_page": page_url,
                        "title": title.removeprefix("File:"),
                        "image_url": info.get("thumburl") or info.get("url"),
                        "original_url": info.get("url"),
                        "license": license_name,
                        "license_url": license_url,
                        "artist_attribution": artist,
                        "credit": plain("Credit"),
                        "description": plain("ImageDescription"),
                        "query": query,
                        "match_type": match_type,
                        "download_status": "pending",
                    }
            time.sleep(0.15)
        except Exception as exc:
            errors.append({"query": query, "error": str(exc)[:300]})

    # Keep up to 24 distinct Commons images per run. Prefer exact building candidates.
    ordered = sorted(found.values(), key=lambda x: (x["match_type"] != "building_candidate", x["query"], x["title"]))
    images = []
    for item in ordered[:24]:
        old = existing.get(item["commons_page"])
        if old and old.get("local_path") and (ROOT / old["local_path"]).is_file():
            item.update(old)
            item["download_status"] = "already_saved"
            images.append(item)
            continue
        url = item.get("image_url")
        if not url:
            item["download_status"] = "no_download_url"
            images.append(item)
            continue
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"):
            ext = ".jpg"
        filename = safe_name(Path(item["title"]).stem) + ext
        dest = OUT / filename
        # Avoid clobbering a different file with a same-name title.
        if dest.exists():
            filename = safe_name(Path(item["title"]).stem + "-" + str(abs(hash(item["commons_page"])) % 1000000)) + ext
            dest = OUT / filename
        try:
            response = SESSION.get(url, timeout=60)
            response.raise_for_status()
            if len(response.content) < 5000 or len(response.content) > 12_000_000:
                raise ValueError(f"image size outside safe bounds: {len(response.content)} bytes")
            if not response.headers.get("Content-Type", "").startswith("image/"):
                raise ValueError("download response is not an image")
            dest.write_bytes(response.content)
            item["local_path"] = str(dest.relative_to(ROOT)).replace(os.sep, "/")
            item["bytes"] = len(response.content)
            item["download_status"] = "downloaded"
        except Exception as exc:
            item["download_status"] = "failed"
            item["download_error"] = str(exc)[:300]
        images.append(item)
        time.sleep(0.15)

    # Retain previous catalog entries not selected this run, so assets remain indexed.
    selected = {x["commons_page"] for x in images}
    for page, item in existing.items():
        if page not in selected and item.get("local_path") and (ROOT / item["local_path"]).is_file():
            images.append(item)

    catalog = {
        "project": "Adam-City",
        "area": "Ermita and Malate, Manila, Philippines",
        "purpose": "Licensed photographic references for building facade/material research; not automatically projected onto buildings.",
        "source": "Wikimedia Commons API",
        "source_url": "https://commons.wikimedia.org/",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "image_count": len(images),
        "downloaded_this_run": sum(x.get("download_status") == "downloaded" for x in images),
        "errors": errors,
        "matching_note": "building_candidate means the search query names a candidate building/landmark, not that visual identity has been independently verified. area_reference is neighborhood-level only. Verify each image before using it as a texture.",
        "images": images,
    }
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Catalog contains {len(images)} images; downloaded this run: {catalog['downloaded_this_run']}; query errors: {len(errors)}")
    # A run with zero photos should still preserve diagnostics and be considered completed.
if __name__ == "__main__":
    main()
