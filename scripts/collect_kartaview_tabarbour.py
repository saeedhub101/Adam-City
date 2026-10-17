#!/usr/bin/env python3
"""Collect public KartaView street photos near Tabarbour without an API token.

KartaView imagery is CC BY-SA 4.0. Preserve the contributor attribution,
source URL, GPS coordinates and camera heading in the catalogue.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Tabarbour, Amman — same working area used by the game map.
WEST, SOUTH, EAST, NORTH = 35.9360, 31.9940, 35.9600, 32.0120
API = "https://api.openstreetcam.org/2.0/photo/"
OUT = Path("game/public/images/kartaview")
MANIFEST = Path("game/public/data/kartaview-photo-catalog.json")
UA = "SaeedOpenWorld/1.0 (public KartaView imagery collector)"
MAX_PHOTOS = 500
# Sample the area on a grid. Public endpoint is used without a token; keep
# requests modest to respect the documented unauthenticated rate limits.
GRID_LATS = [31.996, 32.000, 32.004, 32.008, 32.011]
GRID_LONS = [35.938, 35.943, 35.948, 35.953, 35.958]


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    found = {}
    errors = []
    for lat in GRID_LATS:
        for lon in GRID_LONS:
            if len(found) >= MAX_PHOTOS:
                break
            params = {
                "lat": lat,
                "lng": lon,
                "zoomLevel": 18,
                "radius": 400,
                "join": "sequence",
                "orderBy": "id",
                "orderDirection": "desc",
            }
            url = API + "?" + urllib.parse.urlencode(params)
            try:
                payload = get_json(url)
                result = payload.get("result") or {}
                status = payload.get("status") or {}
                if status and status.get("apiCode") not in (None, 600):
                    errors.append(f"{lat},{lon}: API {status.get('apiCode')} {status.get('apiMessage','')}")
                    continue
                items = result.get("data") or []
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    photo_id = str(item.get("id") or item.get("photoId") or "")
                    photo_lat = as_float(item.get("lat"))
                    photo_lon = as_float(item.get("lng") or item.get("lon"))
                    if not photo_id or photo_lat is None or photo_lon is None:
                        continue
                    if not (WEST <= photo_lon <= EAST and SOUTH <= photo_lat <= NORTH):
                        continue
                    image_url = (item.get("fileurlTh") or item.get("fileurlLTh")
                                 or item.get("fileurlProc") or item.get("fileurl"))
                    if not image_url:
                        continue
                    found[photo_id] = {
                        "id": photo_id,
                        "lat": photo_lat,
                        "lon": photo_lon,
                        "compassAngle": as_float(item.get("heading")),
                        "capturedAt": item.get("shotDate") or item.get("dateAdded"),
                        "sequenceId": item.get("sequenceId") or (item.get("sequence") or {}).get("id"),
                        "imageUrl": image_url.replace("[[sizeprefix]]", "th"),
                        "sourceUrl": "https://kartaview.org/map/@{:.6f},{:.6f},18z".format(photo_lat, photo_lon),
                        "source": "KartaView",
                        "license": "CC BY-SA 4.0",
                        "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
                        "attribution": "© Grab and KartaView Contributors",
                    }
            except Exception as exc:
                errors.append(f"{lat},{lon}: {str(exc)[:180]}")
            time.sleep(0.2)
        if len(found) >= MAX_PHOTOS:
            break

    photos = []
    for index, photo in enumerate(found.values(), start=1):
        photo = dict(photo)
        filename = photo["id"] + ".jpg"
        target = OUT / filename
        try:
            if not target.exists() or target.stat().st_size == 0:
                req = urllib.request.Request(photo["imageUrl"], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45) as response:
                    content = response.read(8 * 1024 * 1024 + 1)
                if len(content) > 8 * 1024 * 1024:
                    raise ValueError("thumbnail exceeds 8 MiB")
                if not (content.startswith(bytes([255, 216, 255])) or content.startswith(b"\\x89PNG\\r\\n\\x1a\\n")):
                    raise ValueError("image response is not JPEG/PNG")
                target.write_bytes(content)
            photo["file"] = "/images/kartaview/" + filename
            photo["bundled"] = True
            photos.append(photo)
        except Exception as exc:
            print(f"WARNING: could not download KartaView photo {photo['id']}: {exc}")
        if index % 50 == 0:
            print(f"Downloaded {len(photos)} of {len(found)} KartaView photos")

    manifest = {
        "area": "Tabarbour, Amman, Jordan",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "KartaView public API (no access token)",
        "license": "CC BY-SA 4.0",
        "attribution": "© Grab and KartaView Contributors",
        "count": len(photos),
        "matchingPolicy": "Photos retain GPS and heading. GPS alone is not used to claim a specific building facade match.",
        "errors": errors[:25],
        "photos": photos,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"KartaView: downloaded {len(photos)} photos with GPS metadata; queried {len(GRID_LATS) * len(GRID_LONS)} sample points.")
    if errors:
        print(f"Non-fatal query/download issues: {len(errors)}")
    # A zero-photo result is reported clearly; do not fake successful coverage.
    if not photos:
        print("No public KartaView photos were found/downloaded in this area. This is a coverage/API result, not a successful photo collection.")


if __name__ == "__main__":
    main()
