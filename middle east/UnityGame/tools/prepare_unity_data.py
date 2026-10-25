#!/usr/bin/env python3
"""Create spatially chunked Unity runtime data from only middle east/Jordan and Palestine."""
import gzip, json, math
from pathlib import Path
GAME=Path(__file__).resolve().parents[1]
ROOT=GAME.parent
TILE=0.02

def read_features(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        obj=json.load(f)
    return obj.get("features", [])

def val(props, *keys):
    for key in keys:
        value=props.get(key)
        if value not in (None, "", "no"):
            return value
    return ""

def number(value):
    try:
        return float(str(value).lower().replace("meters","").replace("metres","").replace("m","").strip())
    except (TypeError, ValueError):
        return 0.0

def tile_for(lon, lat):
    return (math.floor(lon/TILE), math.floor(lat/TILE))

def coords_for(layer, feature):
    geom=feature.get("geometry") or {}
    coords=geom.get("coordinates")
    if not coords: return []
    if layer=="buildings":
        polys=coords if geom.get("type")=="MultiPolygon" else [coords] if geom.get("type")=="Polygon" else []
        result=[]
        for poly in polys:
            if not poly or not poly[0]: continue
            ring=[[p[0],p[1]] for p in poly[0] if isinstance(p,list) and len(p)>1]
            if len(ring)>=4: result.append(ring)
        return result
    if geom.get("type")=="LineString": return [coords]
    if geom.get("type")=="MultiLineString": return coords
    return []

def main():
    for region in ("Jordan","Palestine"):
        src=ROOT/region/"layers"
        out=GAME/"BuildData"/region
        out.mkdir(parents=True,exist_ok=True)
        manifest={"region":region,"source":region+"/layers","tile_degrees":TILE,"layers":{}}
        for layer in ("buildings","streets"):
            source=src/(layer+".geojson.gz")
            if not source.exists():
                print("SKIP missing",source); continue
            buckets={}
            count=0
            for feature in read_features(source):
                props=feature.get("properties") or {}
                parts=coords_for(layer,feature)
                for part_index,part in enumerate(parts):
                    if layer=="buildings":
                        geom=part
                        if len(geom)<4: continue
                        lon=sum(p[0] for p in geom)/len(geom)
                        lat=sum(p[1] for p in geom)/len(geom)
                        height=number(val(props,"height","building:height","render_height"))
                        levels=number(val(props,"building:levels","levels","building_levels"))
                        if height<=0: height=levels*3 if levels>0 else 6
                        item={"id":str(feature.get("id",count))+"-"+str(part_index),"name":str(val(props,"name","name:en")),"height":round(max(2.5,min(height,250)),2),"levels":int(levels),"material":str(val(props,"building:material","material")),"ring":geom}
                    else:
                        if len(part)<2: continue
                        lon=sum(p[0] for p in part)/len(part)
                        lat=sum(p[1] for p in part)/len(part)
                        item={"name":str(val(props,"name","name:en","ref")),"highway":str(val(props,"highway")),"points":part}
                    tx,ty=tile_for(lon,lat)
                    key=f"{tx}_{ty}"
                    buckets.setdefault(key,[]).append(item)
                    count+=1
            layer_dir=out/layer
            layer_dir.mkdir(parents=True,exist_ok=True)
            chunks=[]
            for key,items in buckets.items():
                target=layer_dir/(key+".json")
                target.write_text(json.dumps({"features":items},separators=(",",":"),ensure_ascii=False),encoding="utf-8")
                chunks.append({"tile":key,"file":layer+"/"+target.name,"features":len(items),"bytes":target.stat().st_size})
            manifest["layers"][layer]={"features":count,"chunks":chunks}
            print(region,layer,count,"features in",len(chunks),"chunks")
        (out/"manifest.json").write_text(json.dumps(manifest,separators=(",",":"),ensure_ascii=False),encoding="utf-8")
    print("Chunked runtime data ready. Original source archives were not changed.")

if __name__=="__main__":
    main()
