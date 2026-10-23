#!/usr/bin/env python3
"""Read-only multimodal RAG for Manila buildings; never edits source PBF or map HTML."""
from __future__ import annotations
import csv, hashlib, json, math, os, subprocess, sys, time
from pathlib import Path
from typing import Any
import mapbox_vector_tile, requests

ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parent; TILES=ROOT/"vector-tiles"; OUT=ROOT/"3d-rag"
DATA=OUT/"building-evidence.jsonl"; REPORT=OUT/"progress-report.json"; CATALOG_DIR=OUT/"retrieval-catalog"; CATALOG_PART_BYTES=20*1024*1024
KV="https://api.openstreetcam.org/1.0/list/nearby-photos/"; COMMONS="https://commons.wikimedia.org/w/api.php"; WIKI="https://en.wikipedia.org/w/api.php"
KEY=os.getenv("OPENAI_API_KEY","").strip(); VISION=os.getenv("RAG_VISION_MODEL","gpt-4.1-mini"); SYNTH=os.getenv("RAG_SYNTHESIS_MODEL","gpt-4.1")
RADIUS=int(os.getenv("RAG_PHOTO_RADIUS_M","500")); MAX_IMAGES=int(os.getenv("RAG_MAX_IMAGES_PER_BUILDING","4")); MAX_VISION=int(os.getenv("RAG_MAX_VISION_BUILDINGS","150")); BATCH=max(1,int(os.getenv("RAG_CHECKPOINT_EVERY","10")))
S=requests.Session(); S.headers.update({"User-Agent":"Adam-City-Multimodal-RAG/1.0 (building evidence research)"})
LAST_KV=0.0

def num(v):
 try: return float(v) if v not in (None,"") else None
 except (TypeError,ValueError): return None
def dist(a,b):
 la,lo=map(math.radians,a); lb,lob=map(math.radians,b); dlat=lb-la; dlo=lob-lo
 return 6371000*2*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(la)*math.cos(lb)*math.sin(dlo/2)**2)))
def center(path,feat,extent):
 try:
  z,x,y=map(int,path.relative_to(TILES).with_suffix("").parts[-3:]); pts=[]
  def walk(v):
   if isinstance(v,(list,tuple)):
    if len(v)>=2 and isinstance(v[0],(int,float)) and isinstance(v[1],(int,float)): pts.append((float(v[0]),float(v[1])))
    else:
     for c in v: walk(c)
  walk((feat.get("geometry") or {}).get("coordinates")); pts=list(dict.fromkeys(pts))
  if not pts:return None
  px=sum(p[0] for p in pts)/len(pts); py=sum(p[1] for p in pts)/len(pts); n=2**z
  lon=(x+px/extent)/n*360-180; lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*(y+py/extent)/n))))
  return {"lat":lat,"lon":lon}
 except (ValueError,IndexError,TypeError): return None
def read_jsonl(path):
 out={}
 if path.exists():
  for line in path.read_text(encoding="utf-8").splitlines():
   try:
    r=json.loads(line)
    if r.get("building_key"):out[r["building_key"]]=r
   except json.JSONDecodeError:pass
 return out
def buildings():
 out=[]
 for p in sorted(TILES.rglob("*.pbf")):
  try: decoded=mapbox_vector_tile.decode(p.read_bytes(),default_options={"y_coord_down":True})
  except Exception as e: print(f"Decode skipped {p}: {e}",file=sys.stderr); continue
  rel=str(p.relative_to(REPO))
  for ln,layer in decoded.items():
   if str(ln).lower() not in ("building","buildings"):continue
   for i,f in enumerate(layer.get("features",[])):
    g=f.get("geometry") or {}
    if g.get("type") not in ("Polygon","MultiPolygon"):continue
    pr=f.get("properties") if isinstance(f.get("properties"),dict) else {}; uid=pr.get("building_uid") or pr.get("osm_id") or f.get("id")
    k=f"{ln}:{uid}" if uid else "tile:"+hashlib.sha1(f"{rel}|{ln}|{i}|{json.dumps(g,sort_keys=True)}".encode()).hexdigest()[:20]
    out.append({"building_key":k,"tile":rel,"layer":ln,"feature_index":i,"building_uid":uid,
     "center":center(p,f,int(layer.get("extent",4096))),"source_properties":pr,
     "geometry_sha1":hashlib.sha1(json.dumps(g,sort_keys=True).encode()).hexdigest()})
 return out
def first_coord(g):
 try:
  c=g.get("coordinates")
  while isinstance(c,list) and c and isinstance(c[0],list):c=c[0]
  if len(c)>=2 and isinstance(c[0],(int,float)) and isinstance(c[1],(int,float)):return {"lon":c[0],"lat":c[1]}
 except (AttributeError,TypeError):pass
 return None
def local_record(src,row):
 def pick(*keys):
  return next((row[k] for k in keys if row.get(k) not in (None,"")),None)
 lat=num(pick("lat","latitude","center_lat")); lon=num(pick("lon","lng","longitude","center_lon"))
 return {"source_file":src,"record_id":pick("building_uid","osm_id","id","osm_way_id","building_number"),
  "name":pick("name","building_name","brand","operator","official_name"),
  "coordinates":{"lat":lat,"lon":lon} if lat is not None and lon is not None and -90<=lat<=90 and -180<=lon<=180 else None,
  "attributes":{str(k):v for k,v in row.items() if v not in (None,"") and k!="geometry"}}
def local_index(bs):
 idx=[]; excluded={".git",".github","node_modules","vector-tiles","3d-rag"}
 for p in REPO.rglob("*"):
  if not p.is_file() or any(x in excluded for x in p.parts) or p.suffix.lower() not in (".csv",".json",".geojson",".jsonl"):continue
  try:
   if p.stat().st_size>20_000_000:continue
   rel=str(p.relative_to(REPO)); suf=p.suffix.lower()
   if suf==".csv":
    with p.open(encoding="utf-8-sig",newline="") as f: idx.extend(local_record(rel,r) for r in csv.DictReader(f))
   elif suf==".jsonl":
    for line in p.read_text(encoding="utf-8").splitlines():
     try:idx.append(local_record(rel,json.loads(line)))
     except json.JSONDecodeError:pass
   else:
    obj=json.loads(p.read_text(encoding="utf-8"))
    if isinstance(obj,dict) and obj.get("type")=="FeatureCollection":
     for f in obj.get("features",[]):
      r=local_record(rel,f.get("properties") or {}); c=first_coord(f.get("geometry"))
      if c:r["coordinates"]=c
      idx.append(r)
    elif isinstance(obj,list):idx.extend(local_record(rel,r) for r in obj if isinstance(r,dict))
  except (OSError,UnicodeDecodeError,json.JSONDecodeError,csv.Error):continue
 OUT.mkdir(parents=True,exist_ok=True)
 CATALOG_DIR.mkdir(parents=True,exist_ok=True)
 for stale in CATALOG_DIR.glob("part-*.jsonl"): stale.unlink()
 part_no=1; part_bytes=0; catalog_file=None
 for r in idx:
  line=(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\\n").encode("utf-8")
  if catalog_file is None or (part_bytes and part_bytes+len(line)>CATALOG_PART_BYTES):
   if catalog_file: catalog_file.close()
   catalog_file=(CATALOG_DIR/f"part-{part_no:04d}.jsonl").open("wb"); part_no+=1; part_bytes=0
  catalog_file.write(line); part_bytes+=len(line)
 if catalog_file: catalog_file.close()
 print(f"Repository retrieval catalog written in {part_no-1} part(s), each limited to about 20 MiB",flush=True)
 matches={}
 for b in bs:
  c=b["center"]; rank=[]
  if c:
   for r in idx:
    rc=r.get("coordinates")
    if rc and num(rc.get("lat")) is not None and num(rc.get("lon")) is not None:
     d=dist((c["lat"],c["lon"]),(float(rc["lat"]),float(rc["lon"])))
     if d<=150:rank.append((d,r))
    else:
     vals={str(b["source_properties"].get(k)) for k in ("osm_id","building_uid","name","building_name") if b["source_properties"].get(k)}
     if any(v and (v==str(r.get("record_id")) or v==str(r.get("name"))) for v in vals):rank.append((999999,r))
  rank.sort(key=lambda x:x[0]); matches[b["building_key"]]=[{**r,"distance_m":round(d,1) if d<999999 else None} for d,r in rank[:8]]
 return matches
def get_json(url,params,post=False):
 for attempt in range(3):
  try:
   r=S.post(url,data=params,timeout=30) if post else S.get(url,params=params,timeout=30)
   if r.status_code in (429,500,502,503,504):time.sleep(2**attempt);continue
   r.raise_for_status();return r.json()
  except (requests.RequestException,ValueError) as e:
   if attempt==2:print(f"Evidence source failed: {e}",file=sys.stderr)
   else:time.sleep(2**attempt)
 return {}
def photo(p,src):
 def pick(*ks):return next((p[k] for k in ks if p.get(k) not in (None,"")),None)
 url=pick("fileurl","fileUrl","fileurlProc","fileurlTh","url")
 if url and str(url).startswith("/"):url="https://api.openstreetcam.org"+str(url)
 return {"source":src,"photo_id":pick("id","photoId","pageid"),"title":pick("title","name"),
  "lat":num(pick("lat","latitude")),"lon":num(pick("lng","lon","longitude")),"image_url":url,
  "page_url":pick("descriptionurl","canonicalurl"),"date":pick("shotDate","dateAdded","timestamp"),
  "license":pick("license"),"artist":pick("artist")}
def external(c):
 global LAST_KV
 lat,lon=c["lat"],c["lon"]; out=[]
 wait=37-(time.monotonic()-LAST_KV)
 if wait>0:time.sleep(wait)
 LAST_KV=time.monotonic()
 d=get_json(KV,{"lat":lat,"lng":lon,"radius":RADIUS},True); data=(d.get("result") or {}).get("data") or []
 if isinstance(data,dict):data=data.get("photos") or data.get("data") or []
 for p in data if isinstance(data,list) else []:
  if isinstance(p,dict):out.append(photo(p,"KartaView"))
 wm=get_json(COMMONS,{"action":"query","format":"json","generator":"geosearch","ggscoord":f"{lat}|{lon}","ggsradius":min(10000,max(100,RADIUS)),"ggslimit":20,"ggsnamespace":6,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1200})
 for p in ((wm.get("query") or {}).get("pages") or {}).values():
  ii=(p.get("imageinfo") or [{}])[0]; meta=ii.get("extmetadata") or {}
  out.append({"source":"Wikimedia Commons","photo_id":p.get("pageid"),"title":p.get("title"),"lat":lat,"lon":lon,
   "image_url":ii.get("thumburl") or ii.get("url"),"page_url":ii.get("descriptionurl"),
   "license":(meta.get("LicenseShortName") or {}).get("value"),"artist":(meta.get("Artist") or {}).get("value")})
 wp=get_json(WIKI,{"action":"query","format":"json","list":"geosearch","gscoord":f"{lat}|{lon}","gsradius":min(10000,max(100,RADIUS)),"gslimit":10})
 for p in ((wp.get("query") or {}).get("geosearch") or []):
  out.append({"source":"Wikipedia geosearch","title":p.get("title"),"page_url":"https://en.wikipedia.org/?curid="+str(p.get("pageid")),"lat":p.get("lat"),"lon":p.get("lon")})
 return out
def openai_json(model,messages,tokens=900):
 if not KEY:return None
 try:
  r=S.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":"Bearer "+KEY},
   json={"model":model,"messages":messages,"temperature":0,"max_tokens":tokens,"response_format":{"type":"json_object"}},timeout=100)
  r.raise_for_status(); return json.loads(r.json()["choices"][0]["message"]["content"])
 except (requests.RequestException,ValueError,KeyError,IndexError,TypeError) as e:return {"model_error":str(e)[:500]}
def visual_analysis(b,ev):
 imgs=[x for x in ev if x.get("image_url") and str(x["image_url"]).startswith("https://")][:MAX_IMAGES]
 if not imgs or not KEY:return None
 content=[{"type":"text","text":"Cautious building-photo analysis. Nearby photos may show a different building; do not assert identity from proximity alone. Return JSON: building_match (confirmed/likely/uncertain/not_match), visible_features (each feature has value, confidence high/medium/low, image_index), observations[], limitations[]. Only report visible evidence; unknown fields null. Context: "+json.dumps({"key":b["building_key"],"center":b["center"],"properties":b["source_properties"]},ensure_ascii=False)}]
 for i,p in enumerate(imgs):
  content += [{"type":"text","text":f"Photo {i+1}; source={p.get('source')}; title={p.get('title')}; distance_m={p.get('distance_m')}; page={p.get('page_url')}; license={p.get('license')}"},
              {"type":"image_url","image_url":{"url":p["image_url"],"detail":"low"}}]
 return openai_json(VISION,[{"role":"system","content":"You are the visual evidence model for building reconstruction. Never guess hidden features or identity."},{"role":"user","content":content}],1000)
def synthesize(b,local,ev,visual):
 if not KEY:return None
 ctx={"building_key":b["building_key"],"tile":b["tile"],"center":b["center"],"source_properties":b["source_properties"],
      "repository_evidence":local,"retrieved_evidence":ev,"visual_analysis":visual}
 return openai_json(SYNTH,[{"role":"system","content":"Evidence reconciliation stage in a multimodal RAG pipeline. Use only supplied evidence; never invent. Do not alter geometry or coordinates. Return JSON with building_key, identity_match, proposed_attributes (each {value,status:verified|inferred|conflicting|unknown,confidence:0..1,evidence_ids:[]}), conflicts[], review_required, review_reasons[], evidence_summary. Nearby images are not proof of identity. Keep source facts separate from inference."},
 {"role":"user","content":json.dumps(ctx,ensure_ascii=False)[:22000]}],1300)
def retrieved(b,raw,local):
 c=b.get("center")
 if not c:return []
 out=[]
 for p in raw:
  d=None
  if num(p.get("lat")) is not None and num(p.get("lon")) is not None:
   d=dist((c["lat"],c["lon"]),(float(p["lat"]),float(p["lon"])))
   if d>RADIUS:continue
  elif p.get("source")=="Wikipedia geosearch":d=RADIUS+1
  else:continue
  out.append({**p,"distance_m":round(d,1) if d<=RADIUS else None,
   "evidence_id":"ext:"+hashlib.sha1((str(p.get("source"))+str(p.get("page_url") or p.get("image_url") or p.get("photo_id"))).encode()).hexdigest()[:16]})
 for i,r in enumerate(local):out.append({"evidence_id":f"local:{i}","source":"repository","record":r,"distance_m":r.get("distance_m")})
 return out
def checkpoint(records,report,push=False):
 OUT.mkdir(parents=True,exist_ok=True)
 with DATA.open("w",encoding="utf-8") as f:
  for k in sorted(records):f.write(json.dumps(records[k],ensure_ascii=False,separators=(",",":"))+"\n")
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 if not push:return
 rel=[str(DATA.relative_to(REPO)),str(REPORT.relative_to(REPO)),str(CATALOG_DIR.relative_to(REPO))]
 def git(args,check=True):return subprocess.run(["git",*args],cwd=REPO,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=check)
 git(["add","-A","--",*rel])
 if git(["diff","--cached","--quiet"],False).returncode==0:return
 git(["config","user.name","github-actions[bot]"]);git(["config","user.email","41898282+github-actions[bot]@users.noreply.github.com"])
 git(["commit","-m","Checkpoint Manila multimodal RAG evidence"])
 for _ in range(5):
  p=git(["push","origin","HEAD:main"],False)
  if p.returncode==0:print("RAG checkpoint pushed to main",flush=True);return
  print(p.stdout,file=sys.stderr,flush=True)
  if git(["fetch","origin","main"],False).returncode:break
  if git(["rebase","origin/main"],False).returncode:git(["rebase","--abort"],False);break
 raise RuntimeError("Checkpoint push failed; local working copy retained until runner ends.")
def main():
 if not TILES.exists():print(f"Missing source folder {TILES}",file=sys.stderr);return 2
 OUT.mkdir(parents=True,exist_ok=True); bs=buildings()
 if not bs:print("No polygon building features found in source PBFs",file=sys.stderr);return 3
 old=read_jsonl(DATA); lm=local_index(bs); raw_by_tile={}
 report={}
 try:report=json.loads(REPORT.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError):pass
 report.update({"status":"running","pipeline":"multimodal-rag","pipeline_version":1,"source_tiles_root":"Manila/vector-tiles",
  "source_pbf_modified":False,"map_html_modified":False,"tile_files_found":len(list(TILES.rglob("*.pbf"))),"building_features_found":len(bs),
  "processed_buildings":len(old),"retrieval_sources":["repository CSV/JSON/GeoJSON","KartaView","Wikimedia Commons","Wikipedia"],
  "models":{"vision":VISION if KEY else None,"synthesis":SYNTH if KEY else None,"api_key_configured":bool(KEY)},
  "mode":"multimodal_model_enabled" if KEY else "evidence_retrieval_only_no_OPENAI_API_KEY",
  "visual_analyses":sum(bool(r.get("visual_analysis")) for r in old.values()),"syntheses":sum(bool(r.get("rag_result")) for r in old.values()),
  "errors":report.get("errors",[])})
 print(f"RAG starting: {len(bs)} building features; {len(old)} already recorded; model API key configured={bool(KEY)}",flush=True)
 pending=0
 for b in bs:
  k=b["building_key"]
  if k in old and old[k].get("geometry_sha1")==b["geometry_sha1"]:continue
  tile=b["tile"]
  if tile not in raw_by_tile:
   raw_by_tile[tile]=external(b["center"]) if b.get("center") else []
   report["external_tile_queries"]=report.get("external_tile_queries",0)+1
  local=lm.get(k,[]); ev=retrieved(b,raw_by_tile[tile],local); visual=None; rag=None
  if KEY and ev and report["visual_analyses"]<MAX_VISION:
   try:
    visual=visual_analysis(b,ev)
    if visual:report["visual_analyses"]+=1
   except Exception as e:report["errors"].append({"building_key":k,"stage":"vision","error":str(e)[:300]})
  if KEY:
   try:rag=synthesize(b,local,ev,visual)
   except Exception as e:report["errors"].append({"building_key":k,"stage":"synthesis","error":str(e)[:300]})
  old[k]={"building_key":k,"tile":tile,"layer":b["layer"],"feature_index":b["feature_index"],"building_uid":b["building_uid"],
   "center":b["center"],"source_properties":b["source_properties"],"geometry_sha1":b["geometry_sha1"],"geometry_modified":False,
   "local_evidence":local,"retrieved_evidence":ev,"visual_analysis":visual,"rag_result":rag,
   "evidence_status":"model_reviewed" if rag else ("visual_reviewed" if visual else "retrieved_only"),
   "updated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
  report["processed_buildings"]=len(old);report["syntheses"]=sum(bool(r.get("rag_result")) for r in old.values())
  report["review_required"]=sum(bool((r.get("rag_result") or {}).get("review_required")) for r in old.values())
  report["records_with_images"]=sum(any(x.get("image_url") for x in r.get("retrieved_evidence",[])) for r in old.values())
  pending+=1;print(f"Processed {len(old)}/{len(bs)} {k}: evidence={len(ev)}, visual={bool(visual)}, RAG={bool(rag)}",flush=True)
  if pending>=BATCH:checkpoint(old,report,True);pending=0
 report["status"]="completed";report["completed_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
 report["source_pbf_modified"]=False;report["map_html_modified"]=False
 checkpoint(old,report,True);print(json.dumps(report,ensure_ascii=False,indent=2),flush=True);return 0
if __name__=="__main__":raise SystemExit(main())
