#!/usr/bin/env python3
"""Stream/crop Jordan thematic GeoJSON layers to Tabarbour; tolerate common coordinate encodings."""
import gzip, json, math, pathlib, sys
import ijson

BOUNDS=(35.90,31.96,35.99,32.04)
LAYERS=("buildings","building_details","streets","streetnames","water","landcover","places","addresses")

def points(value):
    if isinstance(value,(list,tuple)):
        if len(value)>=2 and isinstance(value[0],(int,float)) and isinstance(value[1],(int,float)):
            x,y=float(value[0]),float(value[1])
            # Handle projected Web Mercator coordinates when present.
            if abs(x)>180 or abs(y)>90:
                try:
                    lon=x/6378137.0*180.0/math.pi
                    lat=(2.0*math.atan(math.exp(y/6378137.0))-math.pi/2.0)*180.0/math.pi
                    x,y=lon,lat
                except (OverflowError,ValueError):
                    return
            # Correct common latitude/longitude-swapped GeoJSON.
            if 29.0 <= x <= 36.5 and 33.0 <= y <= 37.0:
                x,y=y,x
            yield x,y
        else:
            for v in value:
                yield from points(v)

def intersects(feature):
    geom=(feature or {}).get("geometry") or {}
    coords=geom.get("coordinates")
    if coords is None:
        return False
    # Bounding-box intersection avoids dropping long roads/polygons because their
    # vertex-average centre lies outside the target area.
    west,south,east,north=BOUNDS
    found=False
    for lon,lat in points(coords):
        found=True
        # At least one coordinate in the crop is sufficient for points/lines;
        # polygon extents crossing the crop are handled by the geometry bounds below.
        if west <= lon <= east and south <= lat <= north:
            return True
    if not found:
        return False
    vals=list(points(coords))
    if not vals:
        return False
    xs=[p[0] for p in vals]; ys=[p[1] for p in vals]
    return max(xs)>=west and min(xs)<=east and max(ys)>=south and min(ys)<=north

def main(src,dst):
    src=pathlib.Path(src); dst=pathlib.Path(dst); dst.mkdir(parents=True,exist_ok=True)
    report={"bounds":{"west":BOUNDS[0],"south":BOUNDS[1],"east":BOUNDS[2],"north":BOUNDS[3]},"layers":{}}
    for name in LAYERS:
        inp=src/(name+".geojson.gz")
        if not inp.exists():
            report["layers"][name]={"status":"missing_source","features":0}
            print("LAYER_MISSING",name,flush=True); continue
        out=dst/(name+".geojson.gz"); tmp=out.with_suffix(out.suffix+".part"); count=0; scanned=0
        with gzip.open(inp,"rb") as fin, gzip.open(tmp,"wt",encoding="utf-8",compresslevel=5) as fout:
            fout.write('{"type":"FeatureCollection","features":[')
            first=True
            for feature in ijson.items(fin,"features.item", use_float=True):
                scanned+=1
                if not intersects(feature): continue
                if not first: fout.write(",")
                json.dump(feature,fout,ensure_ascii=False,separators=(",",":"))
                first=False; count+=1
            fout.write("]}")
        tmp.replace(out)
        report["layers"][name]={"status":"cropped","features":count,"scanned":scanned,"bytes":out.stat().st_size}
        print("LAYER_CROPPED",name,count,"scanned",scanned,out.stat().st_size,flush=True)
    (dst/"crop-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    required=("buildings","streets")
    missing=[x for x in required if report["layers"].get(x,{}).get("features",0)==0]
    if missing: raise SystemExit("No features found for required layers: "+", ".join(missing)+"; see crop-report.json for scanned counts")
    print("TABARBOUR_LAYER_CROP_COMPLETE",json.dumps(report["layers"]),flush=True)

if __name__=="__main__":
    if len(sys.argv)!=3: raise SystemExit("usage: crop_tabarbour_layers.py <source-layer-dir> <output-dir>")
    main(sys.argv[1],sys.argv[2])
