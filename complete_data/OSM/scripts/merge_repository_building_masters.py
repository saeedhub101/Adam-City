#!/usr/bin/env python3
"""Build repository-wide masters from building-related CSV and GeoJSON files only."""
import csv, hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "complete_data/OSM/data/buildings/Ermita"
MASTER_CSV = OUT / "ermita-buildings-master.csv"
MASTER_GEO = OUT / "ermita-buildings-master.geojson"
PARTS = OUT / "ermita-buildings-master.parts"
MANIFEST = OUT / "ermita-buildings-master-manifest.json"
CHUNK_LIMIT = 85 * 1024 * 1024
WORDS = ("building", "buildings", "facade", "window", "signage", "roof", "footprint")
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()
def tracked():
    return [ROOT / p.decode() for p in subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).split(b"\0") if p]
def candidates(ext):
    out=[]; seen=set()
    for p in tracked():
        rel=p.relative_to(ROOT).as_posix().lower()
        if p.suffix.lower()!=ext or not p.is_file(): continue
        if p.name.lower() in {MASTER_CSV.name.lower(), MASTER_GEO.name.lower()} or "ermita-buildings-master.parts/" in rel or MANIFEST.name.lower() in rel: continue
        if any(x in rel for x in ("/trees/","/vegetation/","/roads/","/water/","/terrain/")): continue
        if not any(w in rel for w in WORDS): continue
        d=digest(p)
        if d in seen: continue
        seen.add(d); out.append((p,d))
    return sorted(out,key=lambda x:x[0].as_posix())
def merge_csv(sources):
    columns=[]; rows=[]
    for p,d in sources:
        try:
            with p.open(encoding="utf-8-sig",newline="") as f:
                r=csv.DictReader(f)
                if not r.fieldnames: continue
                for c in r.fieldnames:
                    if c and c not in columns and c not in ("_source_file","_source_sha256"): columns.append(c)
                rows.extend((p,d,row) for row in r)
        except (UnicodeDecodeError,csv.Error) as e: print(f"Skipping CSV {p}: {e}",file=sys.stderr)
    fields=["_source_file","_source_sha256"]+columns
    with MASTER_CSV.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader()
        for p,d,row in rows: w.writerow({"_source_file":p.relative_to(ROOT).as_posix(),"_source_sha256":d,**row})
    return {"source_files":len(sources),"rows":len(rows),"columns":len(fields),"bytes":MASTER_CSV.stat().st_size}
def merge_geo(sources):
    import ijson
    PARTS.mkdir(parents=True,exist_ok=True)
    for p in PARTS.glob("*.geojson"): p.unlink()
    parts=[]; features=[]; approx=0; total=0
    def flush():
        nonlocal features,approx
        if not features:return
        name=f"part-{len(parts)+1:03d}.geojson"; dest=PARTS/name
        dest.write_text(json.dumps({"type":"FeatureCollection","features":features},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
        parts.append({"path":dest.relative_to(ROOT).as_posix(),"features":len(features),"bytes":dest.stat().st_size})
        features=[]; approx=0
    for p,d in sources:
        rel=p.relative_to(ROOT).as_posix()
        try:
            with p.open("rb") as f:
                for feature in ijson.items(f,"features.item", use_float=True):
                    if not isinstance(feature,dict): continue
                    props=feature.get("properties")
                    if not isinstance(props,dict): props={}; feature["properties"]=props
                    props["_source_file"]=rel; props["_source_sha256"]=d
                    n=len(json.dumps(feature,ensure_ascii=False,separators=(",",":")).encode())+1
                    if features and approx+n>CHUNK_LIMIT: flush()
                    features.append(feature); approx+=n; total+=1
        except (ValueError,ijson.JSONError) as e: print(f"Skipping invalid GeoJSON {rel}: {e}",file=sys.stderr)
    flush()
    if len(parts)==1:
        MASTER_GEO.write_bytes((ROOT/parts[0]["path"]).read_bytes()); mode="single-file"
    else:
        MASTER_GEO.write_text(json.dumps({"type":"FeatureCollection","features":[],"metadata":{
            "storage":"chunked-index","reason":"All merged features exceed a safe single-file size on GitHub",
            "feature_count":total,"source_file_count":len(sources),"parts":[x["path"] for x in parts]
        }},ensure_ascii=False,indent=2),encoding="utf-8")
        mode="chunked-index"
    return {"source_files":len(sources),"features":total,"mode":mode,"parts":parts,"bytes_across_parts":sum(x["bytes"] for x in parts)}
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cs=candidates(".csv"); gs=candidates(".geojson")
    cr=merge_csv(cs); gr=merge_geo(gs)
    report={"scope":"building-related data only; trees, roads, water and terrain excluded",
      "csv":cr,"geojson":gr,
      "csv_sources":[{"path":p.relative_to(ROOT).as_posix(),"sha256":d} for p,d in cs],
      "geojson_sources":[{"path":p.relative_to(ROOT).as_posix(),"sha256":d} for p,d in gs],
      "deduplication":"Exact byte-identical source files are counted once. Features from different source files are retained even when they may describe the same real building."}
    MANIFEST.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"csv":cr,"geojson":gr,"manifest":MANIFEST.relative_to(ROOT).as_posix()},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
