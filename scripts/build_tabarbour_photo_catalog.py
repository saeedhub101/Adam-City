#!/usr/bin/env python3
"""Build a license-aware catalogue of public photos geolocated near Tabarbour.
Images are references only: the game must not map a nearby photo onto an unrelated building.
"""
import json, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAT, LON, RADIUS = 32.00306, 35.94722, 2500
API = "https://commons.wikimedia.org/w/api.php"
UA = "SaeedTabarbourOpenWorld/1.0 (photo catalogue; contact via GitHub repository)"

def api(params):
    params = {"format":"json", "origin":"*", **params}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)

def license_ok(meta):
    name = (meta.get("LicenseShortName", {}).get("value") or "").strip().lower()
    return any(x in name for x in ("cc0", "public domain", "cc by", "cc-by", "cc by-sa", "cc-by-sa"))

def gather(params, seen):
    found = []
    data = api(params)
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        original = info.get("url")
        thumb = info.get("thumburl") or original
        pageurl = info.get("descriptionurl") or ("https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page.get("title", "").replace(" ", "_")))
        title = page.get("title", "").removeprefix("File:")
        license_name = meta.get("LicenseShortName", {}).get("value", "")
        if not original or not thumb or pageurl in seen or not license_ok(meta):
            continue
        seen.add(pageurl)
        coords = page.get("coordinates") or [{}]
        coord = coords[0] if coords else {}
        found.append({
            "title": title,
            "thumbnail": thumb,
            "original": original,
            "page": pageurl,
            "author": meta.get("Artist", {}).get("value", "Unknown author"),
            "license": license_name,
            "licenseUrl": meta.get("LicenseUrl", {}).get("value", ""),
            "description": meta.get("ImageDescription", {}).get("value", ""),
            "lat": coord.get("lat"),
            "lon": coord.get("lon"),
            "source": "Wikimedia Commons"
        })
    return found

def main():
    seen, photos = set(), []
    base = {"prop":"imageinfo", "iiprop":"url|extmetadata", "iiurlwidth":900, "ggsnamespace":6, "ggslimit":100}
    try:
        photos += gather({"generator":"geosearch", **base, "ggscoord":f"{LAT}|{LON}", "ggsradius":RADIUS, "ggsnamespace":6}, seen)
    except Exception as exc:
        print("Commons geosearch warning:", exc)
    time.sleep(0.3)
    # Text search catches locally described photos whose EXIF/geolocation is absent.
    try:
        photos += gather({"generator":"search", **base, "gsrsearch":'Tabarbour OR طبربور', "gsrnamespace":6, "gsrlimit":50}, seen)
    except Exception as exc:
        print("Commons text search warning:", exc)
    # Prioritize genuinely geolocated photos, then cap the catalogue for quick loading.
    photos.sort(key=lambda p: (p["lat"] is None or p["lon"] is None, p["title"].lower()))
    output = {
        "area": "Tabarbour, Amman, Jordan",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "Wikimedia Commons geosearch + text search",
        "radiusMeters": RADIUS,
        "count": min(len(photos), 100),
        "photos": photos[:100]
    }
    target = Path("game/public/data/tabarbour-photo-catalog.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Saved {target}: {output['count']} openly licensed photo references")
    if not photos:
        print("No matching openly licensed Commons photos were found; empty catalogue is valid and does not invent coverage.")

if __name__ == "__main__":
    main()
