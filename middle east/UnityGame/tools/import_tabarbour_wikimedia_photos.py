#!/usr/bin/env python3
"""Keyless Wikimedia Commons photo intake for Tabarbour; candidate photos are never auto-assigned to buildings."""
import hashlib, json, os, pathlib, re, subprocess, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
OUT = ROOT / "middle east/BuildGLB/tabarbour-real/photos"
MANIFEST = OUT / "wikimedia-photo-manifest.json"
BOUNDS = {"west":35.90,"east":35.99,"south":31.96,"north":32.04}
API = "https://commons.wikimedia.org/w/api.php"
UA = "Adam-City-Tabarbour-AssetImport/1.0 (open-source research; no API key)"

def request_json(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=35) as res:
        return json.load(res)

def commit_batch(message):
    subprocess.run(["git","add","--",str(OUT.relative_to(ROOT))],cwd=ROOT,check=True)
    if subprocess.run(["git","diff","--cached","--quiet"],cwd=ROOT).returncode == 0:
        return
    subprocess.run(["git","-c","user.name=github-actions[bot]","-c","user.email=41898282+github-actions[bot]@users.noreply.github.com","commit","-m",message],cwd=ROOT,check=True)
    for attempt in range(1,6):
        subprocess.run(["git","fetch","origin","main"],cwd=ROOT,check=True)
        rebase=subprocess.run(["git","rebase","origin/main"],cwd=ROOT)
        if rebase.returncode:
            subprocess.run(["git","rebase","--abort"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            time.sleep(attempt)
            continue
        push=subprocess.run(["git","push","origin","HEAD:main"],cwd=ROOT)
        if push.returncode == 0:
            print("PHOTO_CHECKPOINT_PUSHED", message, flush=True)
            return
        time.sleep(attempt)
    raise RuntimeError("Unable to push photo checkpoint after five attempts")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def allowed(meta):
    lic=(meta.get("LicenseShortName") or "").lower()
    usage=(meta.get("UsageTerms") or "").lower()
    return any(x in lic for x in ("cc0","public domain","cc by","cc-by","cc by-sa","cc-by-sa")) or "public domain" in usage

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    old={}
    if MANIFEST.exists():
        try: old=json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception: pass
    records={x.get("pageid"):x for x in old.get("items",[]) if x.get("pageid")}
    queries=[
        ("title_search","Tabarbour Amman Jordan"),
        ("title_search","طبربور عمان"),
        ("nearby_geosearch",""),
    ]
    found={}
    for mode,q in queries:
        try:
            if mode=="nearby_geosearch":
                data=request_json({"action":"query","format":"json","generator":"geosearch","ggscoord":"31.997579|35.940358","ggsradius":10000,"ggslimit":50,"ggsnamespace":6,"prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1600})
            else:
                data=request_json({"action":"query","format":"json","generator":"search","gsrsearch":q,"gsrnamespace":6,"gsrlimit":50,"prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1600})
            for page in data.get("query",{}).get("pages",{}).values():
                info=(page.get("imageinfo") or [{}])[0]
                meta=info.get("extmetadata") or {}
                page["__info"]=info
                page["__meta"]=meta
                page["__query"]=q or "Commons geosearch within 10 km of Tabarbour"
                found[page.get("pageid")]=page
        except Exception as e:
            print("SOURCE_QUERY_FAILED",mode,q,repr(e),flush=True)
    downloaded=0
    processed=0
    for pid,page in sorted(found.items(),key=lambda kv:kv[0]):
        info=page.get("__info",{})
        meta=page.get("__meta",{})
        title=page.get("title","")
        record={
            "pageid":pid,"title":title,"commons_page":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_")),
            "query":page.get("__query"),"source":"Wikimedia Commons","license":meta.get("LicenseShortName",{}).get("value","") if isinstance(meta.get("LicenseShortName"),dict) else "",
            "artist":meta.get("Artist",{}).get("value","") if isinstance(meta.get("Artist"),dict) else "",
            "credit":meta.get("Credit",{}).get("value","") if isinstance(meta.get("Credit"),dict) else "",
            "description":meta.get("ImageDescription",{}).get("value","") if isinstance(meta.get("ImageDescription"),dict) else "",
            "width":info.get("width"),"height":info.get("height"),"downloaded":False,
            "decision":"unverified_candidate_only_not_applied_to_any_building"
        }
        if pid in records and records[pid].get("sha256"):
            record.update(records[pid])
            records[pid]=record
            continue
        if not allowed(meta):
            record["status"]="skipped_license_not_confirmed_free"
            records[pid]=record
            continue
        url=info.get("thumburl") or info.get("url")
        if not url or not str(url).startswith("https://upload.wikimedia.org/"):
            record["status"]="skipped_unexpected_download_host"
            records[pid]=record
            continue
        ext=pathlib.Path(urllib.parse.urlparse(url).path).suffix.lower()
        if ext not in (".jpg",".jpeg",".png",".webp"):
            ext=".jpg"
        name=re.sub(r"[^A-Za-z0-9._-]+","_",pathlib.Path(title).stem).strip("._")[:90] or str(pid)
        target=OUT/(str(pid)+"_"+name+ext)
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=60) as res:
                ctype=res.headers.get("Content-Type","").lower()
                payload=res.read(18*1024*1024+1)
            if len(payload)>18*1024*1024:
                record["status"]="skipped_over_18MiB"
            elif not ctype.startswith("image/") or len(payload)<4096:
                record["status"]="skipped_invalid_image_payload"
            else:
                tmp=target.with_suffix(target.suffix+".part")
                tmp.write_bytes(payload)
                tmp.replace(target)
                record.update({"downloaded":True,"status":"downloaded_candidate","file":str(target.relative_to(ROOT)),"bytes":target.stat().st_size,"sha256":sha256(target),"download_url":url})
                downloaded+=1
        except Exception as e:
            record["status"]="download_failed"
            record["error"]=repr(e)[:500]
        records[pid]=record
        processed+=1
        if downloaded and downloaded%5==0:
            MANIFEST.write_text(json.dumps({"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,"policy":"Only freely licensed Wikimedia Commons images; no API key; geosearch proximity is not proof of building identity; images are candidates and are not applied automatically.","items":list(records.values())},ensure_ascii=False,indent=2),encoding="utf-8")
            commit_batch("Checkpoint Tabarbour Wikimedia photo evidence batch")
    MANIFEST.write_text(json.dumps({"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,"policy":"Only freely licensed Wikimedia Commons images; no API key; geosearch proximity is not proof of building identity; images are candidates and are not applied automatically.","queries_attempted":[q or "geosearch radius 10 km" for _,q in queries],"items":list(records.values())},ensure_ascii=False,indent=2),encoding="utf-8")
    commit_batch("Save Tabarbour Wikimedia photo intake manifest")
    print(json.dumps({"query_pages":len(found),"downloaded_this_run":downloaded,"manifest":str(MANIFEST.relative_to(ROOT)),"total_manifest_items":len(records)},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
