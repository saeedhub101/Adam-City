#!/usr/bin/env python3
"""Keyless Wikipedia evidence and freely licensed Wikimedia image intake for Tabarbour.
Uses public endpoints without API keys or tokens. Photos remain evidence candidates until
their real-world building identity is verified; no image is falsely assigned to a facade.
"""
import gzip, hashlib, json, os, pathlib, re, subprocess, time, urllib.parse, urllib.request

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

def checkpoint(message):
    try:
        subprocess.run(["git","add","--",str(OUT.relative_to(ROOT))],cwd=ROOT,check=True)
        if subprocess.run(["git","diff","--cached","--quiet"],cwd=ROOT).returncode==0: return True
        subprocess.run(["git","-c","user.name=github-actions[bot]","-c","user.email=41898282+github-actions[bot]@users.noreply.github.com","commit","-m",message],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for attempt in range(1,6):
            if subprocess.run(["git","fetch","origin","main"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
                time.sleep(attempt); continue
            rb=subprocess.run(["git","rebase","origin/main"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if rb.returncode:
                subprocess.run(["git","rebase","--abort"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                time.sleep(attempt); continue
            if subprocess.run(["git","push","origin","HEAD:main"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
                print("WIKIPEDIA_CHECKPOINT_PUSHED",message,flush=True); return True
            time.sleep(attempt)
        print("WIKIPEDIA_CHECKPOINT_PUSH_FAILED",message,flush=True)
        return False
    except Exception as e:
        print("WIKIPEDIA_CHECKPOINT_ERROR",repr(e),flush=True)
        return False

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def norm(value):
    value = str(value or "").casefold()
    value = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in value)
    return " ".join(value.split())

def load_building_index():
    """Read the saved local OSM building layer and index stable OSM ids by exact names."""
    candidates = [
        ROOT / "middle east/BuildGLB/tabarbour-real/source/layers/buildings.geojson.gz",
        ROOT / "middle east/Jordan/layers/buildings.geojson.gz",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if not path:
        return {}, {"status":"unavailable", "reason":"saved buildings.geojson.gz not found"}
    index = {}
    count = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        for feature in data.get("features", []):
            props = feature.get("properties") or {}
            geom = feature.get("geometry") or {}
            names = {norm(props.get(k)) for k in ("name","name:en","name:ar","official_name","brand") if props.get(k)}
            names.discard("")
            if not names:
                continue
            fid = feature.get("id") or props.get("@id") or props.get("osm_id") or props.get("way_id") or props.get("relation_id")
            if fid is None:
                continue
            kind = props.get("@type") or props.get("type") or "way"
            fid = str(fid)
            if "/" not in fid: fid = str(kind) + "/" + fid
            rec = {"osm_id":fid, "names":[n for n in (props.get("name"),props.get("name:en"),props.get("name:ar"),props.get("brand")) if n],
                   "geometry_type":geom.get("type"), "properties":props}
            for name in names: index.setdefault(name, []).append(rec)
            count += 1
        return index, {"status":"loaded", "file":str(path.relative_to(ROOT)), "named_building_features":count, "unique_names":len(index)}
    except Exception as e:
        return {}, {"status":"error", "file":str(path), "error":repr(e)[:300]}

def exact_building_matches(title, index):
    matches = index.get(norm(title), [])
    return [{"osm_id":x["osm_id"],"osm_names":x["names"],"match_method":"exact_normalized_name",
             "confidence":"candidate_exact_name_not_visual_identity_proof"} for x in matches[:20]]

def license_is_reusable(meta):
    def val(k):
        v = meta.get(k) or {}
        return v.get("value", "") if isinstance(v, dict) else str(v)
    license_name = val("LicenseShortName").strip().lower()
    usage = val("UsageTerms").strip().lower()
    if "public domain" in license_name or license_name == "cc0": return True
    if license_name.startswith(("cc by ", "cc-by-", "cc by-sa", "cc-by-sa")):
        return not any(term in license_name for term in ("nc", "nd"))
    return "public domain" in usage or "cc0" in usage

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
    old_items={}
    if manifest.exists():
        try:
            previous=json.loads(manifest.read_text(encoding="utf-8"))
            old_items={(x.get("language"),x.get("pageid")):x for x in previous.get("items",[])}
        except Exception: pass
    building_index, building_index_report=load_building_index()
    for rec in records:
        rec["matched_buildings"]=exact_building_matches(rec.get("title"),building_index)
        rec["building_link_status"]="exact_name_match_candidates" if rec["matched_buildings"] else "unmatched_no_verified_building_identity"
        prior=old_items.get((rec.get("language"),rec.get("pageid")),{})
        for key in ("image_status","image_file","image_bytes","image_sha256","image_license","image_artist","commons_file_title","download_url"):
            if prior.get(key): rec[key]=prior[key]
    downloaded=sum(1 for rec in records if rec.get("image_sha256") and (ROOT/rec["image_file"]).is_file())
    # Skip already saved thumbnails; persist and push a checkpoint every five records.
    for i, rec in enumerate(records[:30],1):
        existing=(ROOT/rec["image_file"]) if rec.get("image_file") else None
        if not (existing and existing.is_file() and rec.get("image_sha256")):
            fetch_commons_image(rec,i)
        if i%5==0:
            write_json(manifest,{"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,
              "source":"Wikipedia public endpoints; Commons license metadata checked before download; no API key",
              "records":len(records),"downloaded_images":downloaded,"building_index":building_index_report,"items":records})
            checkpoint("Checkpoint Tabarbour Wikipedia evidence batch "+str(i))
    write_json(manifest,{"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,
      "source":"Wikipedia public endpoints in Arabic and English; no API key; Commons image license checked",
      "records":len(records),"downloaded_images":sum(1 for rec in records if rec.get("image_sha256")),
      "building_index":building_index_report,"items":records})
    checkpoint("Save Tabarbour Wikipedia evidence manifest")
    print("WIKIPEDIA_EVIDENCE_RECORDS",len(records),"downloaded_images",downloaded,flush=True)
    return {"records":len(records),"downloaded_images":downloaded,"languages":["en","ar"]}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,
      "wikipedia":wikipedia(),"generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
      "source_policy":"No API keys or tokens. Wikipedia/Wikimedia are public keyless endpoints.",
      "building_matching":"Wikipedia titles are automatically compared to locally saved OSM building names; exact matches are candidates only, not visual identity proof.",
      "scope_note":"No API keys/tokens. Photos are not automatically applied as facade textures without verified identity."}
    write_json(OUT/"visual-evidence-import-report.json",report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__": main()
