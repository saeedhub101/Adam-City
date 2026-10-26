#!/usr/bin/env python3
"""Stream the repository's compressed Jordan GeoJSON layers down to Tabarbour bounds."""
import gzip, json, pathlib, sys
import ijson

BOUNDS=(35.90,31.96,35.99,32.04)
LAYERS=("buildings","building_details","streets","streetnames","water","landcover","places","addresses")

def points(value):
    if isinstance(value,(list,tuple)):
        if len(value)>=2 and isinstance(value[0],(int,float)) and isinstance(value[1],(int,float)):
            yield float(value[0]),float(value[1])
        else:
            for v in value: yield from points(v)

def center(feature):
    geom=(feature or {}).get("geometry") or {}
    coords=geom.get("coordinates")
    vals=list(points(coords)) if coords is not None else []
    if not vals:return None
    return sum(p[0] for p in vals)/len(vals),sum(p[1] for p in vals)/len(vals)

def main(src,dst):
    src=pathlib.Path(src);dst=pathlib.Path(dst);dst.mkdir(parents=True,exist_ok=True)
    report={"bounds":{"west":BOUNDS[0],"south":BOUNDS[1],"east":BOUNDS[2],"north":BOUNDS[3]},"layers":{}}
    for name in LAYERS:
        inp=src/(name+".geojson.gz")
        if not inp.exists():
            report["layers"][name]={"status":"missing_source","features":0}
            print("LAYER_MISSING",name,flush=True);continue
        out=dst/(name+".geojson.gz");tmp=out.with_suffix(out.suffix+".part");count=0
        with gzip.open(inp,"rb") as fin, gzip.open(tmp,"wt",encoding="utf-8",compresslevel=5) as fout:
            fout.write('{"type":"FeatureCollection","features":[')
            first=True
            for feature in ijson.items(fin,"features.item"):
                c=center(feature)
                if c is None or not(BOUNDS[0]<=c[0]<=BOUNDS[2] and BOUNDS[1]<=c[1]<=BOUNDS[3]):continue
                if not first:fout.write(",")
                json.dump(feature,fout,ensure_ascii=False,separators=(",",":"))
                first=False;count+=1
            fout.write("]}")
        tmp.replace(out)
        report["layers"][name]={"status":"cropped","features":count,"bytes":out.stat().st_size}
        print("LAYER_CROPPED",name,count,out.stat().st_size,flush=True)
    (dst/"crop-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    required=("buildings","streets")
    missing=[x for x in required if report["layers"].get(x,{}).get("features",0)==0]
    if missing:raise SystemExit("No features found for required layers: "+", ".join(missing))
    print("TABARBOUR_LAYER_CROP_COMPLETE",json.dumps(report["layers"]),flush=True)

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: crop_tabarbour_layers.py <source-layer-dir> <output-dir>")
    main(sys.argv[1],sys.argv[2])
