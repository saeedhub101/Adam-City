#!/usr/bin/env python3
"""Resumable public LiDAR discovery/import for Jordan and Palestine.
Every catalog page and completed asset is checkpointed under middle east/LiDAR and
pushed to main immediately. Interrupted .part downloads resume with HTTP Range where supported.
Files above GitHub's per-file limit are split into numbered chunks plus a reassembly manifest.
"""
import hashlib, json, os, re, subprocess, time, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT=Path("middle east/LiDAR"); RAW=ROOT/"downloads"; CAT=ROOT/"catalog"
STATE_PATH=CAT/"progress.json"; REPORT=ROOT/"LIDAR_IMPORT_REPORT.md"
CHUNK=80*1024*1024
S=requests.Session(); S.headers.update({"User-Agent":"Adam-City-public-LiDAR-import/2.0"})
for p in (ROOT,RAW,CAT): p.mkdir(parents=True,exist_ok=True)

def load_state():
    try: x=json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception: x={}
    for k in ("completed_assets","catalog_pages","skipped_assets","errors"): x.setdefault(k,{})
    return x
state=load_state(); bytes_run=0; assets_run=0

def save_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); tmp.replace(path)

def checkpoint(message):
    save_json(STATE_PATH,state)
    subprocess.run(["git","add","--",str(ROOT)],check=True)
    if subprocess.run(["git","diff","--cached","--quiet"]).returncode==0: return
    subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
    subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
    subprocess.run(["git","commit","-m",message[:180]],check=True)
    # A concurrent commit can land on main between fetch/rebase/push. Retry the
    # whole synchronization several times rather than losing the checkpoint.
    last_error=""
    for attempt in range(1,6):
        subprocess.run(["git","fetch","origin","main"],check=True)
        p=subprocess.run(["git","-c","rebase.autoStash=true","rebase","-X","ours","origin/main"])
        if p.returncode:
            subprocess.run(["git","rebase","--abort"],check=False)
            last_error=f"rebase failed on attempt {attempt}"
            time.sleep(attempt*2)
            continue
        pushed=subprocess.run(["git","push","origin","HEAD:main"])
        if pushed.returncode==0:
            return
        last_error=f"push rejected on attempt {attempt}"
        time.sleep(attempt*2)
    raise RuntimeError(f"Could not push LiDAR checkpoint after 5 retries ({last_error}); local checkpoint is retained for resume")

def safe(s,n=100): return (re.sub(r"[^A-Za-z0-9._-]+","_",str(s)).strip("._") or "asset")[:n]
def aid(url): return hashlib.sha256(url.encode()).hexdigest()[:20]
def fetch_json(url,params):
    r=S.get(url,params=params,timeout=120); r.raise_for_status(); return r.json()
def catalog_page(key,obj):
    path=CAT/(safe(key,150)+".json"); save_json(path,obj)
    state["catalog_pages"][key]={"file":str(path),"saved":True}
    checkpoint("LiDAR catalog checkpoint: "+safe(key,100))

def download(url,title,source):
    global bytes_run,assets_run
    ident=aid(url)
    if ident in state["completed_assets"]: return "already imported"
    if ident in state["skipped_assets"]: return state["skipped_assets"][ident].get("status","previously skipped")
    if not isinstance(url,str) or not url.startswith("https://"):
        state["skipped_assets"][ident]={"url":url,"title":title,"source":source,"status":"not an HTTPS direct URL"}
        checkpoint("LiDAR checkpoint: skipped non-HTTPS link"); return "not HTTPS"
    suffix=Path(urlparse(url).path).suffix.lower()
    if suffix not in {".h5",".hdf5",".nc",".laz",".las",".tif",".tiff",".zip",".gz",".bin"}: suffix=".bin"
    stem=safe(title,80)+"_"+ident
    part=RAW/(stem+suffix+".part")
    # Reconstruct any committed resume chunks from a previous interrupted attempt.
    resume_chunks=sorted(RAW.glob(stem+suffix+".resume.part[0-9][0-9][0-9][0-9]"))
    if not part.exists() and resume_chunks:
        with open(part,"wb") as out:
            for chunk_path in resume_chunks:
                with open(chunk_path,"rb") as src:
                    while True:
                        block=src.read(4*1024*1024)
                        if not block: break
                        out.write(block)
    try:
        offset=part.stat().st_size if part.exists() else 0
        headers={"Range":f"bytes={offset}-"} if offset else {}
        with S.get(url,headers=headers,stream=True,timeout=(30,180),allow_redirects=True) as r:
            if r.status_code in (401,403,404):
                # Persist any interrupted partial as small resume chunks before checkpointing.
                if part.exists() and part.stat().st_size>CHUNK:
                    for old in resume_chunks: old.unlink(missing_ok=True)
                    with open(part,"rb") as src:
                        index=0
                        while True:
                            block=src.read(CHUNK)
                            if not block: break
                            (RAW/f"{stem}{suffix}.resume.part{index:04d}").write_bytes(block); index+=1
                    part.unlink(missing_ok=True)
                state["skipped_assets"][ident]={"url":url,"title":title,"source":source,"status":f"HTTP {r.status_code}; not anonymously downloadable"}
                checkpoint("LiDAR checkpoint: unavailable public asset"); return state["skipped_assets"][ident]["status"]
            if offset and r.status_code!=206: offset=0; part.unlink(missing_ok=True)
            if r.status_code not in (200,206): raise RuntimeError(f"HTTP {r.status_code}")
            with open(part,"ab" if offset else "wb") as f:
                for chunk in r.iter_content(1024*1024):
                    if chunk: f.write(chunk); bytes_run+=len(chunk)
                f.flush(); os.fsync(f.fileno())
        size=part.stat().st_size
        if not size: raise RuntimeError("empty download")
        stored=[]
        if size<=CHUNK:
            final=RAW/(stem+suffix); part.replace(final); stored=[{"file":str(final),"bytes":size}]
        else:
            with open(part,"rb") as src:
                i=0
                while True:
                    data=src.read(CHUNK)
                    if not data: break
                    p=RAW/f"{stem}{suffix}.part{i:04d}"
                    if not p.exists(): p.write_bytes(data)
                    stored.append({"file":str(p),"bytes":len(data)}); i+=1
            part.unlink(missing_ok=True)
            manifest=RAW/(stem+suffix+".chunks.json")
            save_json(manifest,{"original_filename":stem+suffix,"source_url":url,"chunk_size":CHUNK,"chunks":stored,"reassembly":"concatenate chunk files in numeric order"})
            stored.append({"file":str(manifest),"bytes":manifest.stat().st_size})
        for old in resume_chunks: old.unlink(missing_ok=True)
        state["completed_assets"][ident]={"url":url,"title":title,"source":source,"bytes":size,"stored":stored}
        state["errors"].pop(ident,None); assets_run+=1
        checkpoint("Import LiDAR asset checkpoint: "+safe(title,80))
        print(f"IMPORTED {source}: {title} ({size} bytes)",flush=True)
        return f"downloaded {size} bytes"
    except Exception as e:
        partial_size=part.stat().st_size if part.exists() else 0
        # Persist interrupted downloads in sub-100-MiB chunks so GitHub can store them.
        if partial_size>CHUNK:
            for old in resume_chunks: old.unlink(missing_ok=True)
            with open(part,"rb") as src:
                index=0
                while True:
                    block=src.read(CHUNK)
                    if not block: break
                    (RAW/f"{stem}{suffix}.resume.part{index:04d}").write_bytes(block)
                    index+=1
            part.unlink(missing_ok=True)
            partial_size=sum(p.stat().st_size for p in RAW.glob(stem+suffix+".resume.part[0-9][0-9][0-9][0-9]"))
        state["errors"][ident]={"url":url,"title":title,"source":source,"error":f"{type(e).__name__}: {e}","partial_bytes":partial_size}
        checkpoint("LiDAR retry checkpoint: "+safe(title,80))
        print(f"RETRY NEXT RUN {title}: {e}",flush=True); return f"retryable error: {e}"

# Public AWS Open LiDAR: follow all S3 listing pages, record every page, import regional filename matches.
try:
    token=None; page=1
    while True:
        params={"list-type":"2","max-keys":"1000"}
        if token: params["continuation-token"]=token
        r=S.get("https://open-lidar-data.s3.eu-central-1.amazonaws.com/",params=params,timeout=120); r.raise_for_status()
        xml=ET.fromstring(r.content); ns={"s3":"http://s3.amazonaws.com/doc/2006-03-01/"}
        keys=[x.text for x in xml.findall(".//s3:Contents/s3:Key",ns) if x.text]
        catalog_page(f"aws-open-lidar-page-{page:04d}",{"page":page,"keys":keys})
        for key in keys:
            if re.search(r"(jordan|palestin|west.?bank|gaza|israel|levant|middle.?east)",key,re.I):
                url="https://open-lidar-data.s3.eu-central-1.amazonaws.com/"+requests.utils.quote(key,safe="/")
                download(url,key.replace("/","__"),"AWS Open LiDAR Data")
        trunc=xml.find(".//s3:IsTruncated",ns)
        nxt=xml.find(".//s3:NextContinuationToken",ns)
        if trunc is None or trunc.text!="true" or nxt is None or not nxt.text: break
        token=nxt.text; page+=1
except Exception as e:
    state["errors"]["aws_open_lidar_catalog"]={"error":f"{type(e).__name__}: {e}"}
    checkpoint("LiDAR catalog error checkpoint: AWS"); print(f"AWS catalog error: {e}",flush=True)

# NASA CMR laser-altimetry collections. Page through the complete returned granule list for each bbox.
collections=[
 ("GEDI02_A.002","GEDI L2A elevation/height"),
 ("GEDI02_B.002","GEDI L2B canopy metrics"),
 ("GEDI04_A.002","GEDI L4A footprint biomass"),
 ("ATL03","ICESat-2 photon data"),
 ("ATL06","ICESat-2 elevation segments"),
 ("ATL08","ICESat-2 land/vegetation segments")]
boxes={"jordan":"34.9,29.1,39.4,33.4","historic-palestine":"34.1,29.3,35.9,33.4"}
for short,description in collections:
 for region,bbox in boxes.items():
    page=1
    while True:
        key=f"cmr-{short}-{region}-page-{page:04d}"
        try:
            p=CAT/(safe(key,150)+".json")
            if key in state["catalog_pages"] and p.exists():
                saved=json.loads(p.read_text(encoding="utf-8")); entries=saved.get("granules",[])
                total=saved.get("hits")
            else:
                result=fetch_json("https://cmr.earthdata.nasa.gov/search/granules.json",{
                    "short_name":short,"bounding_box":bbox,"page_size":200,"page_num":page,"sort_key":"-start_date"})
                feed=result.get("feed",{}); entries=feed.get("entry",[])
                total=feed.get("opensearch$totalResults")
                catalog_page(key,{"collection":short,"description":description,"region":region,"bbox":bbox,
                                  "page":page,"hits":total,"granules":entries})
            if not entries: break
            for item in entries:
                title=item.get("title",short+"-granule")
                for link in item.get("links",[]):
                    href=link.get("href",""); rel=link.get("rel","")
                    if not href.startswith("https://") or "data#" not in rel: continue
                    if not re.search(r"\.(h5|hdf5|nc|laz|las|tif|tiff|zip|gz)(\?|$)",href,re.I): continue
                    download(href,title+"_"+os.path.basename(urlparse(href).path),"NASA CMR "+short)
            try:
                if page*200>=int(total): break
            except (TypeError,ValueError):
                if len(entries)<200: break
            page+=1
        except Exception as e:
            state["errors"][key]={"error":f"{type(e).__name__}: {e}","retry_page":page}
            checkpoint("LiDAR catalog retry checkpoint: "+safe(key,100))
            print(f"CMR error {key}: {e}; moving to next collection",flush=True); break

done=state["completed_assets"]; skipped=state["skipped_assets"]; errors=state["errors"]
lines=["# Jordan and Palestine — public LiDAR import","",
"Storage target: middle east/LiDAR/.","",
"## Incremental and resume behavior","",
"- Each catalog page and each completed asset is committed and pushed to main during the run.",
"- Committed progress prevents already imported assets from being downloaded again.",
"- Interrupted .part files are retained and resumed using HTTP Range when supported.",
"- Files larger than 80 MiB are split into numbered chunks and described by a reassembly JSON file.",
"- Auth-gated/unavailable sources are catalogued as skipped, not falsely reported as downloaded.",
"- GEDI and ICESat-2 are sparse satellite laser observations, not complete airborne city scans.","",
"## Totals","",f"- Completed assets: {len(done)}",f"- Bytes downloaded this run: {bytes_run}",
f"- New assets this run: {assets_run}",f"- Skipped assets: {len(skipped)}",f"- Retry points/errors: {len(errors)}","",
"## Completed assets",""]
for x in done.values(): lines.append(f"- {x.get('source')}: {x.get('title')} — {x.get('bytes')} bytes")
lines+=["","## Skipped assets",""]
for x in skipped.values(): lines.append(f"- {x.get('source')}: {x.get('title')} — {x.get('status')}")
lines+=["","## Errors and resume points",""]
for k,x in errors.items(): lines.append(f"- {k}: {x.get('error',x)}")
REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
checkpoint("Update LiDAR import report and resume state")
print(f"Pass ended: completed={len(done)} new={assets_run} bytes={bytes_run} retry_points={len(errors)}",flush=True)
