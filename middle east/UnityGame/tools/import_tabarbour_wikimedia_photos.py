#!/usr/bin/env python3
"""Keyless Wikimedia Commons photo intake for Tabarbour; candidate photos are never auto-assigned to buildings."""
import gzip, hashlib, json, os, pathlib, re, subprocess, time, urllib.parse, urllib.request

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
    lic=(meta.get("LicenseShortName") or {}).get("value","").lower() if isinstance(meta.get("LicenseShortName"),dict) else str(meta.get("LicenseShortName") or "").lower()
    usage=(meta.get("UsageTerms") or {}).get("value","").lower() if isinstance(meta.get("UsageTerms"),dict) else str(meta.get("UsageTerms") or "").lower()
    if "public domain" in lic or lic.strip()=="cc0" or "public domain" in usage or "cc0" in usage: return True
    if lic.startswith(("cc by ", "cc-by-", "cc by-sa", "cc-by-sa")):
        return not any(term in lic for term in ("nc", "nd"))
    return False

def normalize_name(value):
    value=str(value or "").casefold()
    value="".join(ch if ch.isalnum() or ch.isspace() else " " for ch in value)
    return " ".join(value.split())

def load_named_buildings():
    path=ROOT/"middle east/BuildGLB/tabarbour-real/source/layers/buildings.geojson.gz"
    if not path.is_file(): return []
    out=[]
    try:
        with gzip.open(path,"rt",encoding="utf-8") as f: data=json.load(f)
        for feature in data.get("features",[]):
            p=feature.get("properties") or {}
            names=[p.get(k) for k in ("name","name:en","name:ar","official_name","brand") if p.get(k)]
            fid=feature.get("id") or p.get("@id") or p.get("osm_id") or p.get("way_id") or p.get("relation_id")
            if not fid: continue
            kind=p.get("@type") or p.get("type") or "way"
            fid=str(fid)
            if "/" not in fid: fid=kind+"/"+fid
            for name in names:
                n=normalize_name(name)
                if len(n)>=4: out.append({"osm_id":fid,"name":str(name),"normalized":n})
        return out
    except Exception as e:
        print("BUILDING_NAME_INDEX_FAILED",repr(e),flush=True)
        return []

def match_commons_image_to_buildings(title, description, building_index):
    haystack=normalize_name(str(title or "")+" "+str(description or ""))
    matches=[]
    for b in building_index:
        if b["normalized"] in haystack:
            matches.append({"osm_id":b["osm_id"],"building_name":b["name"],
              "match_method":"building_name_phrase_in_commons_title_or_description",
              "confidence":"candidate_match_requires_visual_review"})
            if len(matches)>=20: break
    return matches

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    building_index=load_named_buildings()
    old={}
    if MANIFEST.exists():
        try: old=json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception: pass
    records={x.get("pageid"):x for x in old.get("items",[]) if x.get("pageid")}
    queries=[("title_search","Tabarbour Amman Jordan"),("title_search","طبربور عمان"),("nearby_geosearch","")]
    found={}
    for mode,q in queries:
        try:
            if mode=="nearby_geosearch":
                data=request_json({"action":"query","format":"json","generator":"geosearch","ggscoord":"31.997579|35.940358","ggsradius":10000,"ggslimit":50,"ggsnamespace":6,"prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1600})
            else:
                data=request_json({"action":"query","format":"json","generator":"search","gsrsearch":q,"gsrnamespace":6,"gsrlimit":50,"prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1600})
            for page in data.get("query",{}).get("pages",{}).values():
                info=(page.get("imageinfo") or [{}])[0]
                page["__info"]=info;page["__meta"]=info.get("extmetadata") or {};page["__query"]=q or "Commons geosearch within 10 km of Tabarbour"
                found[page.get("pageid")]=page
        except Exception as e:
            print("SOURCE_QUERY_FAILED",mode,q,repr(e),flush=True)
    downloaded=0
    # Hard cap prevents unexpectedly importing a huge general-purpose image catalogue.
    for pid,page in sorted(found.items(),key=lambda kv:kv[0])[:30]:
        info=page.get("__info",{});meta=page.get("__meta",{});title=page.get("title","")
        def meta_value(key):
            v=meta.get(key,{})
            return v.get("value","") if isinstance(v,dict) else str(v or "")
        record={"pageid":pid,"title":title,"commons_page":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_")),
            "query":page.get("__query"),"source":"Wikimedia Commons","license":meta_value("LicenseShortName"),
            "artist":meta_value("Artist"),"credit":meta_value("Credit"),"description":meta_value("ImageDescription"),
            "width":info.get("width"),"height":info.get("height"),"downloaded":False,
            "decision":"candidate_not_applied_as_facade_texture"}
        record["matched_buildings"]=match_commons_image_to_buildings(title,record.get("description",""),building_index)
        record["building_link_status"]="name_match_candidates" if record["matched_buildings"] else "unmatched_no_building_name_evidence"
        record["decision"]="automatically_linked_candidate_requires_visual_review" if record["matched_buildings"] else "candidate_not_applied_as_facade_texture"
        if pid in records and records[pid].get("sha256"):
            record.update(records[pid])
            if not record.get("matched_buildings"):
                record["matched_buildings"]=match_commons_image_to_buildings(title,record.get("description",""),building_index)
                record["building_link_status"]="name_match_candidates" if record["matched_buildings"] else "unmatched_no_building_name_evidence"
            records[pid]=record;continue
        if not allowed(meta):
            record["status"]="skipped_license_not_confirmed_free";records[pid]=record;continue
        url=info.get("thumburl") or info.get("url")
        if not url or not str(url).startswith("https://upload.wikimedia.org/"):
            record["status"]="skipped_unexpected_download_host";records[pid]=record;continue
        ext=pathlib.Path(urllib.parse.urlparse(url).path).suffix.lower()
        if ext not in (".jpg",".jpeg",".png",".webp"):ext=".jpg"
        name=re.sub(r"[^A-Za-z0-9._-]+","_",pathlib.Path(title).stem).strip("._")[:90] or str(pid)
        target=OUT/(str(pid)+"_"+name+ext)
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=60) as res:
                ctype=res.headers.get("Content-Type","").lower();payload=res.read(18*1024*1024+1)
            if len(payload)>18*1024*1024:record["status"]="skipped_over_18MiB"
            elif not ctype.startswith("image/") or len(payload)<4096:record["status"]="skipped_invalid_image_payload"
            else:
                tmp=target.with_suffix(target.suffix+".part");tmp.write_bytes(payload);tmp.replace(target)
                record.update({"downloaded":True,"status":"downloaded_candidate","file":str(target.relative_to(ROOT)),"bytes":target.stat().st_size,"sha256":sha256(target),"download_url":url})
                downloaded+=1
        except Exception as e:
            record["status"]="download_failed";record["error"]=repr(e)[:500]
        records[pid]=record
        if downloaded and downloaded%5==0:
            MANIFEST.write_text(json.dumps({"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,"policy":"Free-license Wikimedia Commons only; no key. Automatically links exact building-name phrases as candidates; human visual verification is still required before using a photo as a facade texture.","named_osm_buildings_indexed":len(building_index),"items":list(records.values())},ensure_ascii=False,indent=2),encoding="utf-8")
            commit_batch("Checkpoint Tabarbour Wikimedia photo evidence batch")
    MANIFEST.write_text(json.dumps({"area":"Tabarbour, Amman, Jordan","bounds":BOUNDS,"policy":"Free-license Wikimedia Commons only; no key; proximity is not building identity; candidates are never auto-applied.","queries_attempted":[q or "geosearch radius 10 km" for _,q in queries],"items":list(records.values())},ensure_ascii=False,indent=2),encoding="utf-8")
    commit_batch("Save Tabarbour Wikimedia photo intake manifest")
    print(json.dumps({"query_pages":len(found),"candidate_limit":30,"downloaded_this_run":downloaded,"manifest":str(MANIFEST.relative_to(ROOT)),"total_manifest_items":len(records)},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
