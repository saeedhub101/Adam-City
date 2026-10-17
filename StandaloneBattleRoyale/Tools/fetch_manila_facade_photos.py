#!/usr/bin/env python3
"""Download real, named-building facade reference photos from Wikimedia Commons."""
from __future__ import annotations
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path("StandaloneBattleRoyale/Content/Maps")
OUT = ROOT / "Real-Facade-Photos"
OUT.mkdir(parents=True, exist_ok=True)
API = "https://commons.wikimedia.org/w/api.php"
BUILDINGS = {
    "First United Building": ("First United Building Manila", "First United Building Escolta Manila"),
    "Regina Building": ("Regina Building Manila", "Regina Building Escolta"),
    "Perez-Samanillo Building": ("Perez Samanillo Building Manila", "Don Roman Santos Building Manila"),
    "Calvo Building": ("Calvo Building Escolta Manila", "Calvo Building Manila facade"),
    "Luneta Hotel": ("Luneta Hotel Manila exterior", "Luneta Hotel Manila facade"),
    "Manila Central Post Office": ("Manila Central Post Office exterior", "Manila Post Office building facade"),
    "Manila City Hall": ("Manila City Hall exterior", "Manila City Hall facade"),
    "Manila Metropolitan Theater": ("Manila Metropolitan Theater exterior", "Metropolitan Theater Manila facade"),
    "Escolta Street Buildings": ("Escolta Street Manila buildings", "Escolta Manila heritage buildings facade"),
    "Binondo Street Buildings": ("Binondo Manila street buildings", "Binondo Manila building facade"),
    "Intramuros Buildings": ("Intramuros Manila historic buildings exterior", "Intramuros Manila street facade"),
    "Jones Bridge Area": ("Jones Bridge Manila surrounding buildings", "Jones Bridge Manila city buildings"),
} 
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "AdamRoyalResearch/1.0 (public educational mapping; repository issue tracker)"})
EXTS = (".jpg", ".jpeg", ".png", ".webp")


def api(params):
    response = SESSION.get(API, params={**params, "format": "json"}, timeout=45)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    return data


def main():
    manifest = []
    errors = []
    for building, terms in BUILDINGS.items():
        candidates = {}
        for term in terms:
            try:
                data = api({
                    "action": "query", "list": "search", "srsearch": term,
                    "srnamespace": 6, "srlimit": 30,
                })
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    low = title.lower()
                    if not low.endswith(EXTS) or any(x in low for x in ("interior", "floor plan", "map", "logo", "plaque", "diagram")):
                        continue
                    candidates[title] = candidates.get(title, 0) + sum(k in low for k in ("facade", "façade", "exterior", "building", "street"))
                time.sleep(0.15)
            except Exception as exc:
                errors.append(f"{term}: {exc}")
        titles = list(candidates)
        # Ask for image metadata in batches; API titles can contain special characters.
        for offset in range(0, len(titles), 20):
            batch = titles[offset:offset+20]
            if not batch:
                continue
            try:
                data = api({
                    "action": "query", "titles": "|".join(batch),
                    "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1800,
                })
                pages = data.get("query", {}).get("pages", {})
            except Exception as exc:
                errors.append(f"metadata for {building}: {exc}")
                continue
            saved = 0
            for page in sorted(pages.values(), key=lambda p: candidates.get(p.get("title", ""), 0), reverse=True):
                if saved >= 4:
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
                    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", building).strip("_")
                    name = f"{slug}_{saved+1}{ext}"
                    (OUT / name).write_bytes(response.content)
                    meta = info.get("extmetadata") or {}
                    field = lambda key: (meta.get(key) or {}).get("value", "")
                    manifest.append({
                        "building": building, "file": name, "commons_title": title,
                        "source_page": "https://commons.wikimedia.org/wiki/" + quote(title.replace(" ", "_")),
                        "image_url": url, "license": field("LicenseShortName"),
                        "artist": field("Artist"), "attribution_required": True,
                        "status": "reference_photo_not_yet_projected_onto_3d_mesh"
                    })
                    saved += 1
                except Exception as exc:
                    errors.append(f"download {title}: {exc}")
            print(f"{building}: saved {saved} photo(s)")
    (OUT / "manifest.json").write_text(json.dumps({
        "source": "Wikimedia Commons API", "purpose": "Named Manila building facade reference photographs",
        "important_limit": "Coverage depends on available licensed photos; downloaded photos must be projected onto building materials and are not a complete photogrammetry reconstruction.",
        "images": manifest, "errors": errors,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wikimedia facade collection: {len(manifest)} image(s) saved.")
    if len(manifest) < 12:
        raise RuntimeError(f"Insufficient real building photos: collected {len(manifest)}, require at least 12. Add sources or fix Wikimedia query failures before building.")


if __name__ == "__main__":
    main()
