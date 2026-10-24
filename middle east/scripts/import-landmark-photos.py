#!/usr/bin/env python3
"""Import a small, attributed offline set of geotagged Wikimedia Commons landmark photos."""
import json, os, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path("middle east")
OUT = ROOT / "media" / "commons"
INDEX = ROOT / "landmark-photos.json"
MAX_PER_CENTER = 8
MAX_DOWNLOAD_BYTES = 700_000
CENTERS = [
    ("Amman", 31.9539, 35.9106), ("Petra", 30.3285, 35.4444),
    ("Jerash", 32.2808, 35.8993), ("Aqaba", 29.5321, 35.0063),
    ("Dead Sea", 31.5, 35.5), ("Jerusalem", 31.778, 35.235),
    ("Bethlehem", 31.7054, 35.2024), ("Hebron", 31.5326, 35.0998),
    ("Nablus", 32.2211, 35.2544), ("Ramallah", 31.9038, 35.2034),
    ("Gaza", 31.5017, 34.4668), ("Jericho", 31.8611, 35.4619),
]

def request_json(url):
    req = urllib.request.Request(url, headers={"User-Agent":"AdamCityMapDataImporter/1.0 (open data map; contact via repository issues)"})
    with urllib.request.urlopen(req, timeout=35) as r:
        return json.loads(r.read().decode("utf-8"))

def safe_name(title):
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", title).strip("-")[:100] or "commons-image"
    return stem + ".jpg"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    previous = {}
    if INDEX.exists():
        try:
            previous = {x.get("commons_page"): x for x in json.loads(INDEX.read_text(encoding="utf-8")).get("features", [])}
        except Exception:
            previous = {}
    features, seen = [], set()
    for label, lat, lon in CENTERS:
        params = {
            "action":"query", "format":"json", "generator":"geosearch",
            "ggscoord":f"{lat}|{lon}", "ggsradius":"10000", "ggslimit":"50",
            "ggsnamespace":"6", "prop":"imageinfo", "iiprop":"url|extmetadata",
            "iiurlwidth":"720"
        }
        try:
            data = request_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
        except Exception as exc:
            print(f"WARN Commons search {label}: {exc}")
            continue
        pages = sorted((data.get("query", {}).get("pages", {}) or {}).values(), key=lambda p: p.get("title",""))
        added = 0
        for page in pages:
            title = page.get("title", "")
            info = (page.get("imageinfo") or [{}])[0]
            thumb = info.get("thumburl") or info.get("url")
            if not thumb or title in seen:
                continue
            meta = info.get("extmetadata") or {}
            license_name = (meta.get("LicenseShortName") or {}).get("value", "")
            artist = (meta.get("Artist") or {}).get("value", "")
            description = (meta.get("ImageDescription") or {}).get("value", "")
            commons_page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            # Prefer a reusable license; exclude files whose licensing metadata is absent.
            if not license_name:
                continue
            old = previous.get(commons_page)
            filename = old.get("local_path", "") if old else ""
            valid_existing = filename and (ROOT / filename).is_file()
            if not valid_existing:
                filename = (Path("media/commons") / safe_name(title)).as_posix()
                dest = ROOT / filename
                try:
                    req = urllib.request.Request(thumb, headers={"User-Agent":"AdamCityMapDataImporter/1.0"})
                    with urllib.request.urlopen(req, timeout=35) as resp:
                        raw = resp.read(MAX_DOWNLOAD_BYTES + 1)
                    if len(raw) > MAX_DOWNLOAD_BYTES or not raw.startswith(b"\xff\xd8"):
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(raw)
                except Exception as exc:
                    print(f"WARN photo download {title}: {exc}")
                    continue
            seen.add(title)
            features.append({
                "type":"Feature", "geometry":{"type":"Point","coordinates":[lon,lat]},
                "properties":{
                    "name": re.sub(r"<[^>]+>", "", title.removeprefix("File:")),
                    "area":label, "image":"./" + urllib.parse.quote(filename, safe="/"),
                    "commons_page":commons_page, "license":re.sub(r"<[^>]+>", "", license_name),
                    "artist":re.sub(r"<[^>]+>", "", artist)[:400],
                    "description":re.sub(r"<[^>]+>", "", description)[:500],
                    "source":"Wikimedia Commons geotagged file"
                }
            })
            added += 1
            if added >= MAX_PER_CENTER:
                break
        print(f"{label}: indexed {added} images")
        time.sleep(0.15)
    payload = {
        "type":"FeatureCollection", "name":"Geotagged Wikimedia Commons photos near selected Jordan and Palestine landmarks",
        "license_note":"Images retain their individual Wikimedia Commons licenses and attribution in feature properties; check the linked file page before reuse.",
        "features":features
    }
    INDEX.write_text(json.dumps(payload, ensure_ascii=False, separators=(",",":")) + "\n", encoding="utf-8")
    print(f"Saved {len(features)} photo points to {INDEX}; local image directory: {OUT}")

if __name__ == "__main__":
    main()
