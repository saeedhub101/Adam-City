#!/usr/bin/env python3
"""Fetch Mapillary street-level image thumbnails for Tabarbour with attribution.
Requires MAPILLARY_ACCESS_TOKEN. Images are kept under CC BY-SA 4.0 attribution.
"""
import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOKEN = os.environ.get("MAPILLARY_ACCESS_TOKEN", "").strip()
if not TOKEN:
    raise SystemExit("MAPILLARY_ACCESS_TOKEN is missing; add it as a GitHub Actions secret.")
# Tabarbour coverage: west, south, east, north
BBOX = (35.9360, 31.9940, 35.9600, 32.0120)
API = "https://graph.mapillary.com/images"
OUT = Path("game/public/images/mapillary")
MANIFEST = Path("game/public/data/mapillary-photo-catalog.json")
MAX_IMAGES = 40
UA = "SaeedTabarbourOpenWorld/1.0 (Mapillary imagery attribution)"

def get_json(url):
    req = urllib.request.Request(url, headers={"Authorization": "OAuth " + TOKEN, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    query = {
        "bbox": ",".join(map(str, BBOX)),
        "limit": 200,
        "fields": "id,thumb_1024_url,computed_geometry,creator,captured_at,compass_angle,is_pano,sequence",
    }
    url = API + "?" + urllib.parse.urlencode(query)
    data = get_json(url)
    rows = data.get("data", [])
    # Keep stable, uniquely identified images with coordinates and downloadable thumbnails.
    selected = []
    seen = set()
    for item in rows:
        image_id = str(item.get("id", ""))
        geom = item.get("computed_geometry") or {}
        coords = geom.get("coordinates") or []
        thumb = item.get("thumb_1024_url")
        if not image_id or image_id in seen or len(coords) < 2 or not thumb:
            continue
        lon, lat = coords[0], coords[1]
        if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
            continue
        seen.add(image_id)
        selected.append((item, lon, lat))
    # Sort spatially and cap the initial repository footprint.
    selected = selected[:MAX_IMAGES]
    photos = []
    for item, lon, lat in selected:
        image_id = str(item["id"])
        filename = image_id + ".jpg"
        target = OUT / filename
        if not target.exists():
            req = urllib.request.Request(item["thumb_1024_url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
            if not content.startswith(b"\xff\xd8\xff"):
                print("Skipping non-JPEG thumbnail", image_id)
                continue
            target.write_bytes(content)
            time.sleep(0.15)
        creator = item.get("creator") or {}
        username = creator.get("username") or "Unknown Mapillary contributor"
        photos.append({
            "id": image_id,
            "file": "/images/mapillary/" + filename,
            "lat": lat, "lon": lon,
            "capturedAt": item.get("captured_at"),
            "compassAngle": item.get("compass_angle"),
            "isPanorama": bool(item.get("is_pano")),
            "sequence": item.get("sequence"),
            "creator": username,
            "creatorId": creator.get("id"),
            "source": "Mapillary",
            "sourceUrl": "https://www.mapillary.com/app/?pKey=" + image_id,
            "license": "CC BY-SA 4.0",
            "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "Photo by " + username + " on Mapillary, CC BY-SA 4.0; thumbnail resized to 1024px.",
            "buildingMatch": None
        })
    manifest = {
        "area": "Tabarbour, Amman, Jordan",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Mapillary Graph API",
        "license": "CC BY-SA 4.0",
        "matchingPolicy": "Photos are stored with GPS and compass metadata. They are not assigned to a specific building automatically; image location alone does not prove which facade is shown.",
        "count": len(photos),
        "photos": photos
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Stored {len(photos)} Mapillary thumbnails and attribution records.")

if __name__ == "__main__":
    main()
