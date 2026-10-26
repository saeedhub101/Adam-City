#!/usr/bin/env python3
"""Keyless Wikipedia evidence and freely licensed Wikimedia image intake for Tabarbour.
Uses public endpoints without API keys or tokens. Photos remain evidence candidates until
their real-world building identity is verified; no image is falsely assigned to a facade.
"""
import hashlib, json, os, pathlib, time, urllib.parse, urllib.request

ROOT = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
OUT = ROOT / "middle east/BuildGLB/tabarbour-real/photos"
WIKI_OUT = OUT / "wikipedia"
BOUNDS = {"west": 35.90, "east": 35.99, "south": 31.96, "north": 32.04}
CENTER = (31.997579, 35.940358)
UA = "Adam-City-Tabarbour-EvidenceImporter/1.0 (open-source project; no API key)"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as res:
        return json.load(res)

def request_url(base, params):
    return base + "?" + urllib.parse.urlencode(params)

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

def license_is_reusable(meta):
    def val(k):
        v = meta.get(k) or {}
        return v.get("value", "") if isinstance(v, dict) else str(v)
    text = (val("LicenseShortName") + " " + val("UsageTerms")).lower()
    return any(x in text for x in ("cc0", "public domain", "cc by", "cc-by", "cc by-sa", "cc-by-sa"))

def fetch_commons_image(record, index):
    thumb = record.get("thumbnail_url")
    if not thumb or not thumb.startswith("https://upload.wikimedia.org/"):
        record["image_status"] = "no_direct_wikimedia_thumbnail"
        return
    try:
        pathparts = urllib.parse.urlparse(thumb).path.split("/")
        filename = urllib.parse.unquote(pathparts[-2] if "thumb" in pathparts else pathparts[-1])
        title = "File:" + filename
        data = get_json(request_url("https://commons.wikimedia.org/w/api.php", {
            "action":"query", "format":"json", "prop":"imageinfo",
            "iiprop":"url|extmetadata", "iiurlwidth":"1600", "titles":title
        }))
        page = next(iter(data.get("query", {}).get("pages", {}).values()), {})
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = meta.get("LicenseShortName") or {}
        lic = lic.get("value", "") if isinstance(lic, dict) else str(lic)
        if not license_is_reusable(meta):
            record.update({"image_status":"skipped_license_not_confirmed_free", "image_license":lic, "commons_file_title":title})
            return
        url = info.get("thumburl") or thumb
        ext = pathlib.Path(urllib.parse.urlparse(url).path).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"): ext = ".jpg"
        target = WIKI_OUT / "images" / (str(record.get("language","xx")) + "_" + str(record.get("pageid",index)) + ext)
        target.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent":UA})
        with urllib.request.urlopen(req, timeout=60) as res:
            payload = res.read(18*1024*1024+1)
            ctype = res.headers.get("Content-Type","").lower()
        if len(payload)>18*1024*1024 or not ctype.startswith("image/") or len(payload)<4096:
            record.update({"image_status":"skipped_invalid_or_oversize_image", "image_license":lic})
            return
        tmp=target.with_suffix(target.suffix+".part"); tmp.write_bytes(payload); tmp.replace(target)
        artist=meta.get("Artist") or {}
        record.update({"image_status":"downloaded_license_checked_thumbnail",
          "image_file":str(target.relative_to(ROOT)), "image_bytes":target.stat().st_size,
          "image_sha256":sha256(target), "image_license":lic,
          "image_artist":artist.get("value","") if isinstance(artist,dict) else str(artist),
          "commons_file_title":title, "download_url":url})
    except Exception as e:
        record["image_status"]="thumbnail_download_failed"
        record["image_error"]=repr(e)[:400]

def wikipedia():
    WIKI_OUT.mkdir(parents=True, exist_ok=True)
    found = {}
    for lang, api in (("en","https://en.wikipedia.org/w/api.php"),("ar","https://ar.wikipedia.org/w/api.php")):
        params = {"action":"query","format":"json","formatversion":"2","generator":"geosearch",
          "ggscoord":f"{CENTER[0]}|{CENTER[1]}","ggsradius":"10000","ggslimit":"50",
          "prop":"coordinates|pageimages|extracts|info","piprop":"thumbnail","pithumbsize":"1600",
          "exintro":"1","explaintext":"1","inprop":"url"}
        try:
            data=get_json(request_url(api,params))
            for page in data.get("query",{}).get("pages",[]):
                coords=(page.get("coordinates") or [{}])[0]
                point=[coords.get("lon"),coords.get("lat")]
                if point[0] is not None and not (BOUNDS["west"]<=point[0]<=BOUNDS["east"] and BOUNDS["south"]<=point[1]<=BOUNDS["north"]):
                    continue
                rec={"source":"Wikipedia","language":lang,"pageid":page.get("pageid"),
                  "title":page.get("title"),"article_url":page.get("fullurl"),
                  "coordinates_lon_lat":point if point[0] is not None else None,
                  "thumbnail_url":(page.get("thumbnail") or {}).get("source"),
                  "thumbnail_width":(page.get("thumbnail") or {}).get("width"),
                  "thumbnail_height":(page.get("thumbnail") or {}).get("height"),
                  "extract":(page.get("extract") or "")[:5000],"status":"article_evidence_candidate",
                  "note":"Geographic proximity does not prove this image depicts a particular building."}
                found[(lang,page.get("pageid"))]=rec
        except Exception as e:
            print("WIKIPEDIA_QUERY_FAILED",lang,repr(e),flush=True)
    records=list(found.values())
    manifest=WIKI_OUT/"wikipedia-article-manifest.json"
    downloaded=0
    # Save progress every five records, so an interrupted run retains completed work.
    for i, rec in enumerate(records[:30],1):
        fetch_commons_image(rec,i)
        if rec.get("image_status")=="downloaded_license_checked_thumbnail": downloaded+=1
        if i%5==0:
            write_json(manifest,{"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,
              "source":"Wikipedia public API; Commons license metadata checked before image download",
              "records":len(records),"downloaded_images":downloaded,"items":records})
    write_json(manifest,{"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,
      "source":"Wikipedia public endpoints in Arabic and English; no API key; Commons image license checked",
      "records":len(records),"downloaded_images":downloaded,"items":records})
    print("WIKIPEDIA_EVIDENCE_RECORDS",len(records),"downloaded_images",downloaded,flush=True)
    return {"records":len(records),"downloaded_images":downloaded,"languages":["en","ar"]}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,
      "wikipedia":wikipedia(),"generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
      "source_policy":"No API keys or tokens. Wikipedia/Wikimedia are public keyless endpoints.",
      "scope_note":"Evidence intake only; photos are not automatically assigned to buildings without verified identity."}
    write_json(OUT/"visual-evidence-import-report.json",report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__": main()
