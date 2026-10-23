#!/usr/bin/env python3
"""Fault-tolerant repository-wide GeoJSON/CSV consolidation with incremental checkpoints."""
import csv, json, os, subprocess, hashlib, traceback
from pathlib import Path

ROOT=Path.cwd(); OUT=ROOT/"Philippine"; GEO=OUT/"GeoJSON"; CSVOUT=OUT/"CSV"; ERR=OUT/"error"
LIMIT=int(os.getenv("PHILIPPINE_CHUNK_BYTES","1800000"))
for p in (GEO,CSVOUT,ERR): p.mkdir(parents=True,exist_ok=True)
stats={"geojson_files":0,"csv_files":0,"geojson_features":0,"csv_rows":0,"bad_files":0}
errors=[]; geo_conf=[]; csv_conf=[]; geodata={}; csvdata={}

def checkpoint(label):
    if os.getenv("GITHUB_ACTIONS")!="true": return
    try:
        subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
        subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
        subprocess.run(["git","add","Philippine"],check=True)
        if subprocess.run(["git","diff","--cached","--quiet"]).returncode: 
            subprocess.run(["git","commit","-m",("Philippine checkpoint: "+label)[:72]],check=True)
            subprocess.run(["git","push","origin","HEAD:main"],check=True)
    except Exception as e: print("Checkpoint warning; continuing:",e,flush=True)

def feature_key(f):
    geom=f.get("geometry") or {}; coords=geom.get("coordinates")
    pts=[]
    def walk(v):
        if isinstance(v,list):
            if len(v)>=2 and isinstance(v[0],(int,float)) and isinstance(v[1],(int,float)): pts.append((round(v[0],6),round(v[1],6)))
            else:
                for x in v: walk(x)
    walk(coords)
    if pts:
        if len(pts)==1: return "xy:"+str(pts[0][0])+","+str(pts[0][1])
        return "geom:"+hashlib.sha1(json.dumps(pts,separators=(",",":")).encode()).hexdigest()
    p=f.get("properties") or {}
    for k,v in p.items():
        if k.lower() in ("osm_id","osm_way_id","osm_relation_id","@id","id","full_id") and v not in (None,""): return "id:"+str(v)
    return None

def merge(a,b,source,conflicts,key):
    for k,v in b.items():
        if v in (None,""): continue
        if k not in a or a[k] in (None,""): a[k]=v
        elif isinstance(a[k],dict) and isinstance(v,dict): merge(a[k],v,source,conflicts,key+"/"+k)
        elif isinstance(a[k],list) and isinstance(v,list):
            for x in v:
                if x not in a[k]: a[k].append(x)
        elif a[k]!=v:
            vals=a.setdefault(k+"__conflicts",[])
            for x in (a[k],v):
                if x not in vals: vals.append(x)
            conflicts.append({"key":key,"field":k,"primary":a[k],"alternative":v,"source":source})

def sources():
    for base,dirs,files in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in (".git","node_modules",".venv","__pycache__","Philippine")]
        for name in sorted(files):
            p=Path(base)/name
            if p.suffix.lower()==".geojson" or (p.suffix.lower()==".json" and "geojson" in name.lower()): yield "geo",p
            elif p.suffix.lower()==".csv": yield "csv",p

def save_chunks(kind,records):
    folder=GEO if kind=="geo" else CSVOUT; ext="geojson" if kind=="geo" else "csv"
    for old in folder.glob("Philippine*."+ext): old.unlink()
    if kind=="geo":
        batches=[]; size=0; chunks=[]
        for r in records:
            line=json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n"; n=len(line.encode())
            if batches and size+n>LIMIT: chunks.append("".join(batches)); batches=[]; size=0
            batches.append(line); size+=n
        if batches or not chunks: chunks.append("".join(batches))
        for i,data in enumerate(chunks,1): (folder/f"Philippine{i:02d}.{ext}").write_text(data,encoding="utf-8")
    else:
        import io
        fields=[]
        for r in records:
            for k in r:
                if k not in fields: fields.append(k)
        batch=[]; size=0; chunks=[]
        for r in records:
            batch.append(r); size+=sum(len(str(v or "")) for v in r.values())+len(fields)*2
            if size>=LIMIT and len(batch)>1: chunks.append(batch); batch=[]; size=0
        if batch or not chunks: chunks.append(batch)
        for i,items in enumerate(chunks,1):
            s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(items)
            (folder/f"Philippine{i:02d}.{ext}").write_text(s.getvalue(),encoding="utf-8")

files=list(sources()); print("Input files:",len(files),flush=True)
for i,(kind,path) in enumerate(files,1):
    rel=path.relative_to(ROOT).as_posix()
    try:
        if kind=="geo":
            data=json.loads(path.read_text(encoding="utf-8-sig"))
            feats=data.get("features",[]) if isinstance(data,dict) and data.get("type")=="FeatureCollection" else ([data] if isinstance(data,dict) and data.get("type")=="Feature" else data if isinstance(data,list) else [])
            stats["geojson_files"]+=1
            for n,f in enumerate(feats):
                stats["geojson_features"]+=1
                if not isinstance(f,dict): errors.append({"source":rel,"index":n,"error":"Not an object"}); continue
                f=json.loads(json.dumps(f)); props=f.setdefault("properties",{})
                if not isinstance(props,dict): props={"original_properties":props}; f["properties"]=props
                srcs=props.setdefault("_sources",[])
                if rel not in srcs: srcs.append(rel)
                key=feature_key(f)
                if not key: key="unkeyed:"+rel+":"+str(n); errors.append({"source":rel,"index":n,"error":"No coordinates or stable ID; retained separately"})
                if key not in geodata: geodata[key]=f
                else:
                    if geodata[key].get("geometry")!=f.get("geometry"): geo_conf.append({"key":key,"source":rel,"reason":"geometry differs","alternative":f})
                    merge(geodata[key].setdefault("properties",{}),props,rel,geo_conf,key)
        else:
            stats["csv_files"]+=1
            with path.open(encoding="utf-8-sig",newline="") as fh:
                for n,row in enumerate(csv.DictReader(fh),2):
                    stats["csv_rows"]+=1; row={k:(v if v not in ("",None) else None) for k,v in row.items()}; row["_source_file"]=rel
                    lo=next((v for k,v in row.items() if k.lower() in ("lon","longitude","lng","x") and v),None)
                    la=next((v for k,v in row.items() if k.lower() in ("lat","latitude","y") and v),None)
                    oid=next((v for k,v in row.items() if k.lower() in ("osm_id","osm_way_id","osm_relation_id","@id","id","full_id") and v),None)
                    try: key="xy:"+str(round(float(lo),6))+","+str(round(float(la),6)) if lo and la else ("id:"+str(oid) if oid else None)
                    except Exception: key=None
                    if not key: key="unkeyed:"+rel+":"+str(n); errors.append({"source":rel,"row":n,"error":"No coordinates or stable ID; retained separately"})
                    if key not in csvdata: csvdata[key]=row
                    else: merge(csvdata[key],row,rel,csv_conf,key)
    except Exception as e:
        stats["bad_files"]+=1; errors.append({"source":rel,"error":repr(e),"trace":traceback.format_exc(limit=2)})
        print("ERROR; continuing:",rel,repr(e),flush=True)
    try:
        save_chunks("geo",list(geodata.values())); save_chunks("csv",list(csvdata.values()))
        (OUT/"progress.json").write_text(json.dumps({"processed_files":i,"total_files":len(files),"last_source":rel,"stats":stats},indent=2),encoding="utf-8")
        for name,rows in (("error-records.jsonl",errors),("error-geojson-conflicts.jsonl",geo_conf),("error-csv-conflicts.jsonl",csv_conf)):
            (ERR/name).write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in rows),encoding="utf-8")
        checkpoint(f"{i}-{rel}")
        print(f"[{i}/{len(files)}] {rel} | merged GeoJSON={len(geodata)} CSV={len(csvdata)}",flush=True)
    except Exception as e: print("Save/checkpoint warning; continuing:",repr(e),flush=True)

save_chunks("geo",list(geodata.values())); save_chunks("csv",list(csvdata.values()))
stats["merged_geojson_records"]=len(geodata); stats["merged_csv_records"]=len(csvdata); stats["conflicts"]=len(geo_conf)+len(csv_conf)
for name,rows in (("error-records.jsonl",errors),("error-geojson-conflicts.jsonl",geo_conf),("error-csv-conflicts.jsonl",csv_conf)):
    (ERR/name).write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in rows),encoding="utf-8")
(OUT/"report.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(stats,ensure_ascii=False,indent=2),flush=True)
checkpoint("final report")
