#!/usr/bin/env python3
"""Import georeferenced Wikipedia article evidence and Mapillary street imagery metadata for Tabarbour.

Mapillary API access requires MAPILLARY_ACCESS_TOKEN (configure as a GitHub Actions secret).
Images are retained as evidence candidates and are never assigned to a building without verified
building identity / camera bearing / visibility checks.
"""
import hashlib, json, os, pathlib, re, time, urllib.parse, urllib.request

ROOT = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
OUT = ROOT / "middle east/BuildGLB/tabarbour-real/photos"
WIKI_OUT = OUT / "wikipedia"
MAP_OUT = OUT / "mapillary"
BOUNDS = {"west": 35.90, "east": 35.99, "south": 31.96, "north": 32.04}
CENTER = (31.997579, 35.940358)
UA = "Adam-City-Tabarbour-EvidenceImporter/1.0 (open-source project)"

def get_json(url, headers=None, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.load(res)

def request_url(base, params):
    return base + "?" + urllib.parse.urlencode(params)

def inside(coords):
    try:
        lon, lat = float(coords[0]), float(coords[1])
        return BOUNDS["west"] <= lon <= BOUNDS["east"] and BOUNDS["south"] <= lat <= BOUNDS["north"]
    except Exception:
        return False

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def wikipedia():
    WIKI_OUT.mkdir(parents=True, exist_ok=True)
    found = {}
    endpoints = [
        ("en", "https://en.wikipedia.org/w/api.php"),
        ("ar", "https://ar.wikipedia.org/w/api.php"),
    ]
    for lang, api in endpoints:
        params = {
            "action": "query", "format": "json", "formatversion": "2",
            "generator": "geosearch", "ggscoord": f"{CENTER[0]}|{CENTER[1]}",
            "ggsradius": "10000", "ggslimit": "50",
            "prop": "coordinates|pageimages|extracts|info",
            "piprop": "thumbnail", "pithumbsize": "1600",
            "exintro": "1", "explaintext": "1", "inprop": "url"
        }
        try:
            data = get_json(request_url(api, params))
            for page in data.get("query", {}).get("pages", []):
                coords = (page.get("coordinates") or [{}])[0]
                point = [coords.get("lon"), coords.get("lat")]
                if point[0] is not None and not inside(point):
                    continue
                rec = {
                    "source": "Wikipedia", "language": lang, "pageid": page.get("pageid"),
                    "title": page.get("title"), "article_url": page.get("fullurl"),
                    "coordinates_lon_lat": point if point[0] is not None else None,
                    "thumbnail_url": (page.get("thumbnail") or {}).get("source"),
                    "thumbnail_width": (page.get("thumbnail") or {}).get("width"),
                    "thumbnail_height": (page.get("thumbnail") or {}).get("height"),
                    "extract": (page.get("extract") or "")[:5000],
                    "status": "article_evidence_candidate",
                    "note": "Article proximity does not prove the image depicts a specific building; check image license and identity before reuse."
                }
                found[(lang, page.get("pageid"))] = rec
        except Exception as e:
            print("WIKIPEDIA_QUERY_FAILED", lang, repr(e), flush=True)
    records = list(found.values())
    write_json(WIKI_OUT / "wikipedia-article-manifest.json", {
        "area": "Tabarbour, Amman, Jordan", "bounds": BOUNDS,
        "source": "Wikipedia Action API geosearch, English and Arabic",
        "records": len(records), "items": records
    })
    print("WIKIPEDIA_EVIDENCE_RECORDS", len(records), flush=True)
    return {"records": len(records), "languages": ["en", "ar"]}

def mapillary():
    MAP_OUT.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("MAPILLARY_ACCESS_TOKEN", "").strip()
    manifest_path = MAP_OUT / "mapillary-image-manifest.json"
    if not token:
        result = {
            "status": "skipped_missing_secret",
            "reason": "Mapillary Graph API requires an access token. Configure repository secret MAPILLARY_ACCESS_TOKEN.",
            "records": 0, "items": []
        }
        write_json(manifest_path, result)
        print("MAPILLARY_SKIPPED: MAPILLARY_ACCESS_TOKEN secret is not configured", flush=True)
        return result
    bbox = f'{BOUNDS["west"]},{BOUNDS["south"]},{BOUNDS["east"]},{BOUNDS["north"]}'
    params = {
        "access_token": token,
        "fields": "id,geometry,computed_geometry,captured_at,compass_angle,computed_compass_angle,altitude,computed_altitude,thumb_1024_url,thumb_2048_url,sequence,creator,quality_score,width,height,camera_type,make,model,is_pano",
        "bbox": bbox, "limit": "200"
    }
    items = []
    url = request_url("https://graph.mapillary.com/images", params)
    pages = 0
    while url and pages < 10 and len(items) < 1000:
        pages += 1
        try:
            data = get_json(url, timeout=60)
        except Exception as e:
            print("MAPILLARY_QUERY_FAILED", repr(e), flush=True)
            break
        for image in data.get("data", []):
            geom = image.get("computed_geometry") or image.get("geometry") or {}
            coords = geom.get("coordinates") or []
            if coords and not inside(coords):
                continue
            image_id = str(image.get("id", ""))
            items.append({
                "source": "Mapillary", "id": image_id,
                "image_url": "https://www.mapillary.com/app/?pKey=" + image_id,
                "thumbnail_url": image.get("thumb_2048_url") or image.get("thumb_1024_url"),
                "geometry": geom, "captured_at": image.get("captured_at"),
                "compass_angle": image.get("computed_compass_angle", image.get("compass_angle")),
                "altitude_m": image.get("computed_altitude", image.get("altitude")),
                "sequence": image.get("sequence"), "creator": image.get("creator"),
                "quality_score": image.get("quality_score"), "width": image.get("width"),
                "height": image.get("height"), "camera_type": image.get("camera_type"),
                "camera_make": image.get("make"), "camera_model": image.get("model"),
                "is_panorama": image.get("is_pano"),
                "status": "georeferenced_visual_evidence_candidate",
                "note": "Image camera altitude is not building height. No building-specific color/material/address is inferred from image metadata alone."
            })
        next_url = (data.get("paging") or {}).get("next")
        # Only follow API-provided continuation URLs.
        url = next_url if next_url and next_url.startswith("https://graph.mapillary.com/") else None
        print("MAPILLARY_PAGE", pages, "total_candidates", len(items), flush=True)
    write_json(manifest_path, {
        "area": "Tabarbour, Amman, Jordan", "bounds": BOUNDS,
        "source": "Mapillary Graph API", "status": "queried",
        "records": len(items), "pages_read": pages,
        "items": items,
        "policy": "Store metadata and thumbnail links; apply imagery to building materials only after visual identity and facing direction are verified."
    })
    print("MAPILLARY_EVIDENCE_RECORDS", len(items), flush=True)
    return {"status": "queried", "records": len(items), "pages_read": pages}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "area": "Tabarbour, Amman, Jordan", "bounds": BOUNDS,
        "wikipedia": wikipedia(),
        "mapillary": mapillary(),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope_note": "Evidence acquisition only. Photos are not auto-mapped onto GLB façades without building-level verification."
    }
    write_json(OUT / "visual-evidence-import-report.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
