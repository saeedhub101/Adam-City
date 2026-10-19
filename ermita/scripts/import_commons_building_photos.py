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
    ("Robinsons Place Manila exterior", "building_candidate"),
    ("Manila Residences Bocobo facade", "building_candidate"),
    ("7-Eleven Manila Philippines store exterior", "building_candidate"),
    ("Rizal Park Manila grass lawn aerial", "area_reference"),
    ("Ermita Manila hotel building exterior", "area_reference"),
]

def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return value[:90] or "commons-image"

def api(params):
    last_error = None
    for attempt in range(4):
        response = SESSION.get(API, params={"format": "json", **params}, timeout=45)
        if response.status_code == 429 and attempt < 3:
            try:
                wait = float(response.headers.get("Retry-After", 2 ** (attempt + 1)))
            except Exception:
                wait = 2 ** (attempt + 1)
            time.sleep(min(max(wait, 2), 20))
            last_error = RuntimeError("Wikimedia Commons rate limit (429); retrying")
            continue
        response.raise_for_status()
        return response.json()
    raise last_error or RuntimeError("Wikimedia Commons query failed after retries")

def title_matches(query: str, title: str) -> bool:
    """Reject Commons search spillover whose file title does not name the target."""
    t = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    q = query.lower()
    if "philippine general hospital" in q:
        return "pgh" in t or "philippine general hospital" in t or "cancer institute building" in t
    if "manila doctors hospital" in q:
        return "manila doctors hospital" in t
    if "national museum of fine arts" in q:
        return "national museum" in t and ("fine arts" in t or "philippines" in t or "ermita" in t)
    if "manila city hall" in q:
        return "manila city hall" in t or "city hall of manila" in t
    if "rizal memorial medical center" in q:
        return "rizal memorial medical center" in t
    if "ermita manila buildings street" in q:
        return "ermita" in t and any(word in t for word in ("building", "street", "facade", "exterior"))
    if "malate manila buildings street" in q:
        return "malate" in t and any(word in t for word in ("building", "street", "facade", "exterior"))
    if "university of the philippines manila" in q:
        return ("university of the philippines" in t and "manila" in t) or "up manila" in t
    if "st paul university manila" in q:
        return "st paul university manila" in t or "saint paul university manila" in t
    if "robinsons place manila" in q:
        return "robinsons" in t and "manila" in t and ("place" in t or "mall" in t)
    if "manila residences bocobo" in q:
        return "bocobo" in t and ("residence" in t or "residences" in t)
    if "7-eleven manila" in q:
        return ("7-eleven" in t or "7 eleven" in t or "711" in t) and "manila" in t
    if "rizal park manila grass lawn aerial" in q:
        return ("rizal park" in t or "luneta" in t) and any(word in t for word in ("aerial", "lawn", "park", "grass"))
    if "ermita manila hotel building exterior" in q:
        return "ermita" in t and any(word in t for word in ("hotel", "building", "exterior"))
    return False


def main():
    existing = {}
    if CATALOG.exists():
        try:
            old = json.loads(CATALOG.read_text(encoding="utf-8"))
            for item in old.get("images", []):
                existing[item.get("commons_page")] = item
        except Exception:
            pass

    # Skip queries that already have saved images; only search new/unresolved targets.
    completed_queries = {
        item.get("query") for item in existing.values()
        if item.get("query") and item.get("local_path") and (ROOT / item["local_path"]).is_file()
    }
    found = {}
    errors = []
    for query, match_type in QUERIES:
        if query in completed_queries:
            continue
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
                # Wikimedia search can return gallery pages or unrelated images whose
                # long descriptions mention the query. Require the filename/title to
                # identify the target before retaining it as a building candidate.
                if not title_matches(query, title):
                    continue
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
            time.sleep(1.2)
        except Exception as exc:
            errors.append({"query": query, "error": str(exc)[:300]})

    # Keep up to 24 distinct Commons images per run. Prefer exact building candidates.
    ordered = sorted(found.values(), key=lambda x: (x["match_type"] != "building_candidate", x["query"], x["title"]))
    images = []
    for item in ordered[:24]:
        old = existing.get(item["commons_page"])
        if old and old.get("local_path") and (ROOT / old["local_path"]).is_file():
            new_query = item.get("query")
            new_match_type = item.get("match_type")
            item.update(old)
            item["query"] = new_query
            item["match_type"] = new_match_type
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

    # Correctly label older catalog entries whose previous broad search query
    # accidentally associated them with an unrelated place. Keep every file.
    for item in images:
        title = str(item.get("title", "")).lower()
        original_type = item.get("match_type", "unverified")
        item.setdefault("original_search_match_type", original_type)
        if any(term in title for term in ("bayambang", "basista", "san carlos city", "cebu waterfront", "compania maritima")):
            item["match_type"] = "nonlocal_reference"
            item["location_status"] = "outside_target_area"
            item["use_as_target_facade_reference"] = False
            item["location_note"] = "Image is from another Philippine city/area; retained in the library but must not be assigned to an Ermita/Malate building."
        elif "intramuros" in title or "metropolitan theater" in title or "manila city hall" in title:
            item["match_type"] = "manila_context_reference"
            item["location_status"] = "outside_or_unverified_target_area"
            item["use_as_target_facade_reference"] = False
            item["location_note"] = "Manila-context architecture reference, not a verified facade match inside the current project AOI."
        elif any(term in title for term in ("ermita", "malate", "philippine general hospital", "pgh cancer institute", "national museum of the philippines", "university of the philippines manila", "up manila")):
            item["location_status"] = "likely_target_area_candidate"
            item["use_as_target_facade_reference"] = True
            item["exact_building_identity_verified"] = False
            item["location_note"] = "Likely relevant local building candidate; verify visual identity and coordinates before projecting onto a facade."
        else:
            item["location_status"] = "unverified"
            item["use_as_target_facade_reference"] = False
            item["location_note"] = "Location/building identity has not been verified for the project AOI."

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
        "matching_note": "Every image is retained with license metadata. location_status and use_as_target_facade_reference separate likely local candidates from nearby-city or nonlocal reference images. No image is automatically projected onto a facade.",
        "images": images,
    }
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Catalog contains {len(images)} images; downloaded this run: {catalog['downloaded_this_run']}; query errors: {len(errors)}")
    # A run with zero photos should still preserve diagnostics and be considered completed.
if __name__ == "__main__":
    main()
