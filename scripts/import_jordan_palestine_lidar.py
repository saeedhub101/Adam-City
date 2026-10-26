#!/usr/bin/env python3
"""Resumable, bounded-concurrency import of publicly downloadable laser data.

Do not crawl the entire global Open LiDAR S3 bucket: catalog records are not imported data.
Only non-empty, signature-validated direct payloads count as completed assets.
"""
import concurrent.futures, hashlib, json, os, re, subprocess, threading, time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT=Path("middle east/LiDAR"); RAW=ROOT/"downloads"; CAT=ROOT/"catalog"
STATE_PATH=CAT/"progress.json"; REPORT=ROOT/"LIDAR_IMPORT_REPORT.md"
CHUNK=80*1024*1024; WORKERS=4; MAX_PAGES=3
S=requests.Session(); S.headers.update({"User-Agent":"Adam-City-public-LiDAR-import/3.0"})
for p in (ROOT,RAW,CAT): p.mkdir(parents=True,exist_ok=True)

def load_state():
    try: data=json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception: data={}
    for k in ("completed_assets","catalog_pages","skipped_assets","errors"): data.setdefault(k,{})
    return data
state=load_state(); lock=threading.RLock(); bytes_run=0; assets_run=0

def save_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); tmp.replace(path)

def safe(s,n=100): return (re.sub(r"[^A-Za-z0-9._-]+","_",str(s)).strip("._") or "asset")[:n]
def aid(url): return hashlib.sha256(url.encode()).hexdigest()[:20]

def checkpoint(message):
    with lock:
        save_json(STATE_PATH,state)
        subprocess.run(["git","add","--",str(ROOT)],check=True)
        if subprocess.run(["git","diff","--cached","--quiet"]).returncode==0: return
        subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
        subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
        subprocess.run(["git","commit","-m",message[:180]],check=True)
        last=""
        for attempt in range(1,6):
            subprocess.run(["git","fetch","origin","main"],check=True)
            p=subprocess.run(["git","-c","rebase.autoStash=true","rebase","-X","ours","origin/main"])
            if p.returncode:
                subprocess.run(["git","rebase","--abort"],check=False); last=f"rebase {attempt}"; time.sleep(attempt); continue
            if subprocess.run(["git","push","origin","HEAD:main"]).returncode==0: return
            last=f"push {attempt}"; time.sleep(attempt)
        raise RuntimeError("Checkpoint push failed after retries: "+last)

def suffix_for(url,title=""):
    path=Path(urlparse(url).path).suffix.lower()
    if path in {".h5",".hdf5",".las",".laz",".zip"}: return path
    m=re.search(r"\.(h5|hdf5|las|laz|zip)(?:$|\?)",title,re.I)
    return "."+m.group(1).lower() if m else ""

def validate(path,suffix):
    with path.open("rb") as f: head=f.read(16)
    if not head: return False,"empty file"
    if suffix in {".h5",".hdf5"} and not head.startswith(b"\x89HDF\r\n\x1a\n"): return False,"invalid HDF5 signature"
    if suffix in {".las",".laz"} and not head.startswith(b"LASF"): return False,"invalid LAS/LAZ signature"
    if suffix==".zip" and not head.startswith(b"PK"): return False,"invalid ZIP signature"
    return True,"signature validated"

def download(item):
    global bytes_run,assets_run
    url,title,source,collection,region=item; ident=aid(url)
    with lock:
        if ident in state["completed_assets"]: return "already imported"
        if ident in state["skipped_assets"]: return state["skipped_assets"][ident].get("status","previously skipped")
    suffix=suffix_for(url,title)
    if not suffix or not url.startswith("https://"):
        with lock: state["skipped_assets"][ident]={"url":url,"title":title,"source":source,"status":"unsupported/non-direct URL"}
        return "unsupported URL"
    stem=safe(title,70)+"_"+ident; part=RAW/(stem+suffix+".part"); final=RAW/(stem+suffix)
    try:
        offset=part.stat().st_size if part.exists() else 0
        with S.get(url,headers=({"Range":f"bytes={offset}-"} if offset else {}),stream=True,timeout=(20,120),allow_redirects=True) as r:
            if r.status_code in (401,403,404):
                with lock: state["skipped_assets"][ident]={"url":url,"title":title,"source":source,"status":f"HTTP {r.status_code}; not publicly downloadable"}
                return f"HTTP {r.status_code}"
            if offset and r.status_code!=206: offset=0; part.unlink(missing_ok=True)
            if r.status_code not in (200,206): raise RuntimeError(f"HTTP {r.status_code}")
            with part.open("ab" if offset else "wb") as f:
                for block in r.iter_content(1024*1024):
                    if block:
                        f.write(block)
                        with lock: bytes_run+=len(block)
                f.flush(); os.fsync(f.fileno())
        size=part.stat().st_size; valid,check=validate(part,suffix)
        if not valid:
            part.unlink(missing_ok=True)
            with lock: state["skipped_assets"][ident]={"url":url,"title":title,"source":source,"status":check}
            return check
        stored=[]
        if size<=CHUNK:
            part.replace(final); stored=[{"file":str(final),"bytes":size}]
        else:
            chunks=[]
            with part.open("rb") as src:
                i=0
                while True:
                    block=src.read(CHUNK)
                    if not block: break
                    p=RAW/f"{stem}{suffix}.part{i:04d}"; p.write_bytes(block)
                    chunks.append({"file":str(p),"bytes":len(block)}); i+=1
            part.unlink(missing_ok=True); manifest=RAW/f"{stem}{suffix}.chunks.json"
            save_json(manifest,{"original_filename":stem+suffix,"source_url":url,"chunk_size":CHUNK,"chunks":chunks,"reassembly":"concatenate chunks in numeric order"})
            stored=chunks+[{"file":str(manifest),"bytes":manifest.stat().st_size}]
        with lock:
            state["completed_assets"][ident]={"url":url,"title":title,"source":source,"collection":collection,"region":region,
                "bytes":size,"validation":check,"stored":stored,"data_kind":"satellite laser observation; not dense airborne city LiDAR"}
            state["errors"].pop(ident,None); assets_run+=1
        checkpoint("Import verified laser asset: "+safe(title,90))
        print(f"IMPORTED VERIFIED {source}: {title} ({size} bytes)",flush=True)
        return f"downloaded and validated {size} bytes"
    except Exception as e:
        partial=part.stat().st_size if part.exists() else 0
        with lock: state["errors"][ident]={"url":url,"title":title,"source":source,"error":f"{type(e).__name__}: {e}","partial_bytes":partial}
        checkpoint("Laser retry checkpoint: "+safe(title,90))
        print(f"RETRY NEXT RUN {title}: {e}",flush=True)
        return "retryable error: "+str(e)

# Geographic CMR discovery replaces the old thousands-page global S3 crawl.
collections=[("GEDI02_A.002","GEDI L2A laser observations"),("GEDI02_B.002","GEDI L2B laser observations"),
              ("ATL03","ICESat-2 photon observations"),("ATL06","ICESat-2 elevation segments"),
              ("ATL08","ICESat-2 land/vegetation segments")]
boxes={"jordan":"34.9,29.1,39.4,33.4","palestine":"34.1,29.3,35.9,33.4"}
discovered={}; new_catalog=0
for short,description in collections:
    for region,bbox in boxes.items():
        for page in range(1,MAX_PAGES+1):
            key=f"cmr-{short}-{region}-page-{page:04d}"; path=CAT/(safe(key,150)+".json")
            try:
                if key in state["catalog_pages"] and path.exists():
                    saved=json.loads(path.read_text(encoding="utf-8")); entries=saved.get("granules",[]); total=saved.get("hits")
                else:
                    r=S.get("https://cmr.earthdata.nasa.gov/search/granules.json",
                        params={"short_name":short,"bounding_box":bbox,"page_size":200,"page_num":page,"sort_key":"-start_date"},
                        timeout=(15,60)); r.raise_for_status(); feed=r.json().get("feed",{})
                    if key not in state["catalog_pages"]:
                        entries=feed.get("entry",[]); total=feed.get("opensearch$totalResults")
                        save_json(path,{"collection":short,"description":description,"region":region,"bbox":bbox,"page":page,"hits":total,"granules":entries})
                        state["catalog_pages"][key]={"file":str(path),"saved":True,"kind":"metadata only"}; new_catalog+=1
                    else: entries=saved.get("granules",[]); total=saved.get("hits")
                if not entries: break
                for granule in entries:
                    title=granule.get("title",short+"-granule")
                    for link in granule.get("links",[]):
                        href=link.get("href",""); rel=link.get("rel","")
                        if href.startswith("https://") and "data#" in rel and suffix_for(href,os.path.basename(urlparse(href).path)):
                            discovered[aid(href)]=(href,title+"_"+os.path.basename(urlparse(href).path),"NASA CMR "+short,short,region)
                try:
                    if page*200>=int(total): break
                except (TypeError,ValueError):
                    if len(entries)<200: break
            except Exception as e:
                with lock: state["errors"][key]={"error":f"{type(e).__name__}: {e}","retry_page":page}
                print(f"CMR query failed {key}: {e}",flush=True); break

checkpoint("Checkpoint geographic LiDAR discovery metadata")
print(f"Discovery complete: {len(discovered)} unique direct URLs; new catalog pages={new_catalog}; downloads use {WORKERS} workers",flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
    futures=[pool.submit(download,item) for item in discovered.values()]
    for future in concurrent.futures.as_completed(futures):
        try: print("Download result: "+str(future.result()),flush=True)
        except Exception as e: print(f"Worker failed: {type(e).__name__}: {e}",flush=True)


# Public SlideRule fallback: obtain actual sampled satellite laser measurements through a
# public processing service when the original HDF5 granules require Earthdata credentials.
slr_saved=0
slr_observations=0
slr_errors=0
try:
    from datetime import datetime, timezone
    from sliderule import icesat2
    icesat2.init(url="slideruleearth.io", verbose=True, max_resources=4, loglevel=20, rethrow=True)
    t1=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for region,bbox in boxes.items():
        west,south,east,north=[float(x) for x in bbox.split(",")]
        ident=aid(f"sliderule|ATL03|{region}|2023-01-01|{t1[:10]}")
        with lock:
            if ident in state["completed_assets"]:
                continue
        params={
            "poly":[
                {"lon":west,"lat":south},{"lon":east,"lat":south},
                {"lon":east,"lat":north},{"lon":west,"lat":north},{"lon":west,"lat":south}
            ],
            "t0":"2023-01-01T00:00:00Z","t1":t1,"srt":0,"cnf":3
        }
        try:
            frame=icesat2.atl03sp(params,keep_id=True)
            if frame is None or len(frame)==0:
                print(f"SlideRule returned no ATL03 observations for {region}",flush=True)
                continue
            original_rows=len(frame)
            stride=max(1,(original_rows+24999)//25000)
            if stride>1:
                frame=frame.iloc[::stride].copy()
            payload=json.loads(frame.to_json())
            target=RAW/"sliderule"/region/"atl03_ground_observations.geojson"
            save_json(target,payload)
            size=target.stat().st_size
            saved_rows=len(frame)
            with lock:
                state["completed_assets"][ident]={
                    "url":"https://slideruleearth.io (public processing API)",
                    "title":target.name,"source":"SlideRule Earth / NASA ICESat-2 ATL03",
                    "collection":"ATL03","region":region,"bytes":size,
                    "validation":f"GeoJSON parsed; saved observations={saved_rows}; source rows={original_rows}",
                    "stored":[{"file":str(target),"bytes":size}],
                    "data_kind":"actual sampled spaceborne laser observations; not dense airborne city LiDAR",
                    "source_rows":original_rows,"saved_rows":saved_rows,"sampling_stride":stride
                }
                slr_saved+=1
                slr_observations+=saved_rows
            checkpoint("Checkpoint actual SlideRule ATL03 observations: "+region)
            print(f"SAVED ACTUAL SLIDERULE OBSERVATIONS: {region} rows={saved_rows} source_rows={original_rows}",flush=True)
        except Exception as exc:
            slr_errors+=1
            with lock:
                state["errors"][f"sliderule-{region}"]={"error":f"{type(exc).__name__}: {exc}"}
            print(f"SlideRule request failed for {region}: {type(exc).__name__}: {exc}",flush=True)
except Exception as exc:
    slr_errors+=1
    with lock:
        state["errors"]["sliderule-init"]={"error":f"{type(exc).__name__}: {exc}"}
    print(f"SlideRule fallback unavailable: {type(exc).__name__}: {exc}",flush=True)
print(f"SlideRule fallback complete: files={slr_saved}, observations={slr_observations}, errors={slr_errors}",flush=True)

done=state["completed_assets"]; skipped=state["skipped_assets"]; errors=state["errors"]
total_bytes=sum(int(x.get("bytes",0)) for x in done.values())
lines=["# Jordan and Palestine — verified LiDAR / laser-data import","",
"Storage target: middle east/LiDAR/downloads/.","","## Method","",
"- Geographic NASA CMR searches only; no full global S3 catalog crawl.",
f"- Up to {MAX_PAGES} pages per collection/region; {WORKERS} concurrent downloads.",
"- Direct HDF5, LAS/LAZ and ZIP payloads are signature-validated. If raw granules require Earthdata authentication, the public SlideRule processing service is queried for actual sampled ATL03 laser observations saved as local GeoJSON.",
"- Existing completed URLs are skipped and partial downloads resume with HTTP Range where supported.",
"- Files over 80 MiB are split into chunks with a reassembly manifest.",
"- Satellite laser footprints are not dense airborne city point clouds; metadata is not counted as data.","",
"## Verified totals","",f"- Completed validated payloads: {len(done)}",f"- Bytes represented by completed payloads: {total_bytes}",
f"- Bytes transferred this run: {bytes_run}",f"- Newly completed this run: {assets_run}",f"- Skipped/unavailable: {len(skipped)}",f"- Errors/retry points: {len(errors)}","","## Completed payloads",""]
for x in done.values(): lines.append(f"- {x.get('source')}: {x.get('title')} — {x.get('bytes')} bytes; {x.get('validation')}")
lines += ["","## Skipped/unavailable",""]
for x in skipped.values(): lines.append(f"- {x.get('source')}: {x.get('title')} — {x.get('status')}")
lines += ["","## Errors / resume points",""]
for k,x in errors.items(): lines.append(f"- {k}: {x.get('error',x)}")
if not done: lines += ["","## Coverage warning","","No verified laser payload is recorded yet. NASA Earthdata-protected URLs are not counted as imported. GEDI/ICESat-2 cannot replace dense airborne LiDAR for realistic city buildings."]
REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
checkpoint("Update verified LiDAR import report")
print(f"Pass ended: verified={len(done)} bytes={total_bytes} new={assets_run} run_bytes={bytes_run} skipped={len(skipped)} errors={len(errors)}",flush=True)
