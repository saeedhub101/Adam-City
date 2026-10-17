#!/usr/bin/env python3
"""Fetch geolocated, building-specific Manila facade photographs from Wikimedia Commons."""
from __future__ import annotations
import json
from pathlib import Path
import requests

OUT = Path("StandaloneBattleRoyale/Content/Maps/Real-Facade-Photos")
OUT.mkdir(parents=True, exist_ok=True)
API = "https://commons.wikimedia.org/w/api.php"
# These Commons categories identify real, named buildings in Binondo/Escolta.
CATEGORIES = {
    "First United Building": "Category:First United Building",
    "Regina Building": "Category:Regina Building",
    "Afable Building": "Category:Afable Building",
}
session = requests.Session()
session.headers.update({"User-Agent": "AdamRoyal-ResearchGame/1.0 (educational research; contact via GitHub repo)"})
manifest = []
for building, category in CATEGORIES.items():
    try:
        data = session.get(API, params={
            "action":"query","format":"json","generator":"categorymembers",
            "gcmtitle":category,"gcmtype":"file","gcmlimit":30,
            "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":2048
        }, timeout=45).json()
        pages = (data.get("query") or {}).get("pages") or {}
        candidates = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url")
            if not url or not str(url).lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue
            title = page.get("title", "")
            # Prefer exterior/façade views and avoid interiors, maps, logos and plans.
            low = title.lower()
            if any(w in low for w in ("interior", "floor plan", "map", "logo", "plaque")):
                continue
            score = sum(w in low for w in ("facade", "façade", "exterior", "building", "south façade", "street"))
            candidates.append((score, title, url, info.get("extmetadata", {})))
        candidates.sort(reverse=True, key=lambda x: x[0])
        saved = 0
        for score, title, url, meta in candidates:
            if saved >= 3:
                break
            try:
                response = session.get(url, timeout=60)
                response.raise_for_status()
                ext = ".png" if "png" in response.headers.get("content-type", "").lower() else ".jpg"
                slug = "".join(c if c.isalnum() else "_" for c in building).strip("_")
                name = f"{slug}_{saved+1}{ext}"
                (OUT / name).write_bytes(response.content)
                def field(key):
                    return (meta.get(key) or {}).get("value", "")
                manifest.append({
                    "building": building, "file": name, "commons_title": title,
                    "source_page": "https://commons.wikimedia.org/wiki/" + requests.utils.quote(title.replace(" ", "_")),
                    "image_url": url, "license": field("LicenseShortName"),
                    "artist": field("Artist"), "attribution_required": True,
                    "status": "reference_photo_not_yet_projected_onto_3d_mesh"
                })
                saved += 1
            except Exception as exc:
                print(f"Photo download skipped for {title}: {exc}")
        print(f"{building}: downloaded {saved} real facade/reference photos")
    except Exception as exc:
        print(f"Commons category failed for {building}: {exc}")
if not manifest:
    raise SystemExit("No real building photographs downloaded; refusing to pass photo asset stage.")
(OUT / "manifest.json").write_text(json.dumps({
    "source": "Wikimedia Commons API",
    "purpose": "Building-specific real facade reference photographs",
    "important_limit": "Photos are downloaded and identified by named building; this stage does not claim they have been photogrammetrically reconstructed or correctly UV-projected onto every 3D wall.",
    "images": manifest
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Downloaded {len(manifest)} photographs; manifest written.")
