#!/usr/bin/env python3
"""Collect diverse public Manila street-view/reference photos from Wikimedia Commons."""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path("StandaloneBattleRoyale/Content/Maps/Street-Imagery")
ROOT.mkdir(parents=True, exist_ok=True)
API = "https://commons.wikimedia.org/w/api.php"
MAX_PHOTOS = 80
TERMS = [
    "Escolta Manila street",
    "Binondo Manila street",
    "Manila downtown street",
    "Manila street traffic",
    "Manila old buildings street",
    "Intramuros Manila street",
]
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "AdamRoyalResearch/1.0 (public educational mapping; repository issue tracker)"})
EXTS = (".jpg", ".jpeg", ".png", ".webp")


def request_api(params):
    response = SESSION.get(API, params={**params, "format": "json"}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload


def main():
    candidates = {}
    errors = []
    for term in TERMS:
        try:
            payload = request_api({
                "action": "query", "list": "search", "srsearch": term,
                "srnamespace": 6, "srlimit": 50,
            })
            for item in payload.get("query", {}).get("search", []):
                title = item.get("title", "")
                low = title.lower()
                if not low.endswith(EXTS) or any(k in low for k in ("map", "logo", "flag", "coat of arms", "diagram", "floor plan")):
                    continue
                # Rank titles with street/traffic/building context above generic city imagery.
                score = sum(k in low for k in ("street", "road", "traffic", "building", "escolta", "binondo", "intramuros", "manila"))
                candidates[title] = max(score, candidates.get(title, 0))
            time.sleep(0.2)
        except Exception as exc:
            errors.append(f"{term}: {exc}")
    ordered = sorted(candidates, key=lambda title: candidates[title], reverse=True)
    images = []
    for offset in range(0, len(ordered), 20):
        if len(images) >= MAX_PHOTOS:
            break
        batch = ordered[offset:offset+20]
        try:
            payload = request_api({
                "action": "query", "titles": "|".join(batch),
                "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1800,
            })
        except Exception as exc:
            errors.append(f"metadata batch: {exc}")
            continue
        pages = payload.get("query", {}).get("pages", {})
        for page in sorted(pages.values(), key=lambda p: candidates.get(p.get("title", ""), 0), reverse=True):
            if len(images) >= MAX_PHOTOS:
                break
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url")
            title = page.get("title", "")
            if not url or not url.lower().split("?")[0].endswith(EXTS):
                continue
            try:
                response = SESSION.get(url, timeout=60)
                response.raise_for_status()
                ctype = response.headers.get("content-type", "").lower()
                if not ctype.startswith("image/") or len(response.content) < 12000:
                    continue
                ext = ".png" if "png" in ctype else ".webp" if "webp" in ctype else ".jpg"
                slug = re.sub(r"[^A-Za-z0-9_-]+", "_", title.rsplit(":", 1)[-1]).strip("_")[:70]
                name = f"commons_manila_{len(images)+1:03d}_{slug}{ext}"
                (ROOT / name).write_bytes(response.content)
                meta = info.get("extmetadata") or {}
                field = lambda key: (meta.get(key) or {}).get("value", "")
                images.append({
                    "file": name, "source": "Wikimedia Commons",
                    "source_page": "https://commons.wikimedia.org/wiki/" + quote(title.replace(" ", "_")),
                    "image_url": url, "commons_title": title,
                    "license": field("LicenseShortName"), "artist": field("Artist"),
                    "attribution_required": True,
                    "status": "street_reference_photo_not_yet_projected_onto_3d_mesh",
                })
                print(f"Saved {name} ({len(images)}/{MAX_PHOTOS})")
            except Exception as exc:
                errors.append(f"download {title}: {exc}")
        time.sleep(0.2)
    (ROOT / "manifest.json").write_text(json.dumps({
        "source": "Wikimedia Commons API",
        "search_terms": TERMS,
        "downloaded_photos": len(images),
        "important_limit": "Reference photos are not automatically projected onto 3D buildings as textures.",
        "images": images, "errors": errors,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manila street reference collection: {len(images)} image(s) saved.")
    if not images:
        print("WARNING: No usable street photos were available from Wikimedia Commons.")


if __name__ == "__main__":
    main()
