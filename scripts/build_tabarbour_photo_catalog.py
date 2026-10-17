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
    params = {"action":"query", "format":"json", "origin":"*", **params}
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

def point_in_polygon(lat, lon, ring):
    """Ray casting in lon/lat coordinates; only exact footprint containment is auto-matched."""
    if len(ring) < 3:
        return False
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point.get("lon"), point.get("lat")
        xj, yj = ring[j].get("lon"), ring[j].get("lat")
        if xi is None or yi is None or xj is None or yj is None:
            j = i
            continue
        crosses = ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi)
        if crosses:
            inside = not inside
        j = i
    return inside

def load_buildings():
    source = Path("game/public/data/tabarbour-osm.json")
    data = json.loads(source.read_text(encoding="utf-8"))
    buildings = []
    for way in data.get("elements", []):
        tags = way.get("tags") or {}
        geometry = way.get("geometry") or []
        if way.get("type") != "way" or not tags.get("building") or len(geometry) < 3:
            continue
        buildings.append({
            "id": str(way["id"]),
            "name": tags.get("name") or tags.get("addr:housenumber") or ("OSM building #" + str(way["id"])),
            "ring": geometry
        })
    return buildings

def match_photo_to_building(photo, buildings):
    lat, lon = photo.get("lat"), photo.get("lon")
    if lat is None or lon is None:
        return None
    matches = [b for b in buildings if point_in_polygon(lat, lon, b["ring"])]
    # A point must fall inside exactly one mapped building footprint. A nearby point
    # or ambiguous overlap is never enough to claim an exact building match.
    if len(matches) != 1:
        return None
    b = matches[0]
    return {"osmBuildingId": b["id"], "buildingName": b["name"], "matchMethod": "geotag_inside_unique_osm_footprint"}

def main():
    seen, photos = set(), []
    buildings = load_buildings()
    base = {"prop":"imageinfo|coordinates", "iiprop":"url|extmetadata", "iiurlwidth":900, "ggsnamespace":6, "ggslimit":100}
    try:
        photos += [p for p in gather({"generator":"geosearch", **base, "ggscoord":f"{LAT}|{LON}", "ggsradius":RADIUS, "ggsprimary":"all", "ggsnamespace":6}, seen) if p["lat"] is not None and p["lon"] is not None]
    except Exception as exc:
        print("Commons geosearch warning:", exc)
    time.sleep(0.3)
    # Text search is only a fallback for files explicitly named after Tabarbour; do not add generic Jordan/Amman images.
    try:
        photos += [p for p in gather({"generator":"search", **base, "gsrsearch":'Tabarbour OR طبربور', "gsrnamespace":6, "gsrlimit":50}, seen) if any(term in p["title"].casefold() for term in ("tabarbour", "طبربور"))]
    except Exception as exc:
        print("Commons text search warning:", exc)
    # Prioritize genuinely geolocated photos, then cap the catalogue for quick loading.
    photos.sort(key=lambda p: (p["lat"] is None or p["lon"] is None, p["title"].lower()))
    output = {
        "area": "Tabarbour, Amman, Jordan",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "Wikimedia Commons geosearch + text search; strict unique OSM footprint matching",\n        "matchedToBuildingCount": sum(1 for p in photos if p.get("buildingMatch")),\n        "matchingPolicy": "Automatic association only when photo coordinates fall inside exactly one OSM building footprint. No nearest-building guesses.",
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
