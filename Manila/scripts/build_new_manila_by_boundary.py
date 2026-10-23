#!/usr/bin/env python3
"""Build a NEW boundary-partitioned PBF dataset from Manila/vector-tiles.
Reads the boundary and building layers directly from source PBFs. Source files are read-only.
"""
from __future__ import annotations
import json, math, time, shutil
from pathlib import Path
import mapbox_vector_tile
from shapely.geometry import Point, shape
from shapely.ops import unary_union, polygonize, transform

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"Manila"/"vector-tiles"
OUT=ROOT/"Manila"/"New_Manila"
EARTH_R=6378137.0
RAD=math.pi/180
REF_LAT=14.59
BOUNDARY_NAMES={"boundary","boundaries","admin","administrative"}
BUILDING_NAMES={"building","buildings"}
buckets={}

def tile_lonlat(path,extent,x,y):
    z,tx,ty=map(int,path.relative_to(SOURCE).with_suffix("").parts[-3:])
    n=2**z
    return ((tx+x/extent)/n*360-180, math.degrees(math.atan(math.sinh(math.pi*(1-2*(ty+y/extent)/n)))))

def metric_xy(lon,lat):
    return EARTH_R*lon*RAD*math.cos(REF_LAT*RAD), EARTH_R*lat*RAD

def convert_geom(path,gd,extent,metric=False):
    g=shape(gd)
    def fn(x,y,z=None):
        if hasattr(x,"__iter__"):
            pairs=[]
            for a,b in zip(x,y):
                ll=tile_lonlat(path,extent,float(a),float(b))
                pairs.append(metric_xy(*ll) if metric else ll)
            return [p[0] for p in pairs],[p[1] for p in pairs]
        ll=tile_lonlat(path,extent,float(x),float(y))
        return metric_xy(*ll) if metric else ll
    return transform(fn,g)

def fid(props,f,i):
    for k in ("osm_id","osm_way_id","osm_wayid","way_id","id","name"):
        if props.get(k) not in (None,""): return str(props[k])
    return str(f.get("id") or i)

def main():
    tiles=sorted(p for p in SOURCE.rglob("*.pbf") if p.is_file())
    if not tiles: raise RuntimeError("No PBF tiles found under Manila/vector-tiles")
    polygons=[]; lines=[]; boundary_layers=set(); scan_errors=[]
    print(f"Scanning {len(tiles)} source PBF tiles for their boundary vector layer.",flush=True)
    for ti,path in enumerate(tiles,1):
        try:
            decoded=mapbox_vector_tile.decode(path.read_bytes(),default_options={"y_coord_down":True})
            for lname,layer in decoded.items():
                if str(lname).lower() not in BOUNDARY_NAMES: continue
                boundary_layers.add(str(lname)); extent=int(layer.get("extent",4096))
                for fi,f in enumerate(layer.get("features",[])):
                    gd=f.get("geometry")
                    if not gd or not gd.get("coordinates"): continue
                    try:
                        g=convert_geom(path,gd,extent,metric=True)
                        props=f.get("properties") or {}
                        if g.geom_type in ("Polygon","MultiPolygon"):
                            polygons.append((fid(props,f,fi),props,g))
                        elif g.geom_type in ("LineString","MultiLineString"):
                            lines.append(g)
                    except Exception as e:
                        scan_errors.append({"tile":str(path.relative_to(ROOT)),"feature":fi,"error":str(e)})
        except Exception as e: scan_errors.append({"tile":str(path.relative_to(ROOT)),"error":str(e)})
        if ti%10==0 or ti==len(tiles): print(f"[boundary {ti}/{len(tiles)}] polygons={len(polygons)} lines={len(lines)}",flush=True)
    if polygons:
        unique={}
        for fid0,props,g in polygons:
            if not g.is_empty and g.is_valid: unique[(fid0,g.wkb_hex)]=(fid0,props,g)
        areas=list(unique.values())
    elif lines:
        merged=unary_union(lines)
        polys=[p for p in polygonize(merged) if p.is_valid and p.area>100]
        unique={p.wkb_hex:p for p in polys}
        if not unique: raise RuntimeError("PBF boundary layer has linework but it cannot form closed polygons; no approximate nearest-line assignment was attempted.")
        areas=[(f"polygon-{i:04d}",{"derived_from":"PBF boundary linework"},p) for i,p in enumerate(sorted(unique.values(),key=lambda g:(g.centroid.x,g.centroid.y,g.area)),1)]
    else:
        raise RuntimeError("No usable boundary features found in PBF layer. Detected layers: "+", ".join(sorted(boundary_layers)))
    areas=[a for a in areas if not a[2].is_empty and a[2].is_valid and a[2].area>100]
    areas.sort(key=lambda a:(str(a[0]),a[2].area,a[2].centroid.x,a[2].centroid.y))
    if not areas: raise RuntimeError("No usable boundary polygons found.")
    OUT.mkdir(parents=True,exist_ok=True)
    for p in OUT.iterdir():
        if p.is_dir() and p.name.startswith("area-"): shutil.rmtree(p)
    counts=[0]*len(areas); building_layers=set(); tile_errors=[]
    for ti,path in enumerate(tiles,1):
        rel=path.relative_to(SOURCE); z,tx,ty=map(int,rel.with_suffix("").parts[-3:])
        try:
            decoded=mapbox_vector_tile.decode(path.read_bytes(),default_options={"y_coord_down":True})
            for lname,layer in decoded.items():
                if str(lname).lower() not in BUILDING_NAMES: continue
                building_layers.add(str(lname)); extent=int(layer.get("extent",4096))
                for fi,f in enumerate(layer.get("features",[])):
                    gd=f.get("geometry")
                    if not gd or not gd.get("coordinates"): continue
                    try:
                        center=convert_geom(path,gd,extent,metric=True).centroid
                        candidates=[(a[2].area,i) for i,a in enumerate(areas) if a[2].covers(center)]
                        if not candidates: continue
                        _,ai=min(candidates)
                        outpath=OUT/f"area-{ai+1:04d}"/str(z)/str(tx)/f"{ty}.pbf"
                        key=(ai,outpath)
                        if key not in buckets: buckets[key]={}
                        if str(lname) not in buckets[key]:
                            buckets[key][str(lname)]={"name":str(lname),"features":[],"extent":extent}
                        buckets[key][str(lname)]["features"].append(f); counts[ai]+=1
                    except Exception as e: tile_errors.append({"tile":str(rel),"feature":fi,"error":str(e)})
        except Exception as e: tile_errors.append({"tile":str(rel),"error":str(e)})
        if ti%10==0 or ti==len(tiles): print(f"[buildings {ti}/{len(tiles)}] assigned={sum(counts)}",flush=True)
    out_count=0
    for (ai,outpath),layers in buckets.items():
        outpath.parent.mkdir(parents=True,exist_ok=True)
        payload=[{"name":v["name"],"features":v["features"],"extent":v["extent"],"version":2} for v in layers.values()]
        encoded=mapbox_vector_tile.encode(payload,default_options={"y_coord_down":True})
        check=mapbox_vector_tile.decode(encoded,default_options={"y_coord_down":True})
        got=sum(len(v.get("features",[])) for n,v in check.items() if str(n).lower() in BUILDING_NAMES)
        expected=sum(len(v["features"]) for n,v in layers.items() if n.lower() in BUILDING_NAMES)
        if got!=expected: raise RuntimeError(f"Verification failed for {outpath}: expected {expected}, got {got}")
        outpath.write_bytes(encoded); out_count+=1
    summary={"status":"completed_with_errors" if scan_errors or tile_errors else "completed",
      "source":"Manila/vector-tiles","source_pbf_tiles":len(tiles),"boundary_layer_names":sorted(boundary_layers),
      "boundary_areas_created":len(areas),"building_layer_names":sorted(building_layers),
      "building_features_assigned":sum(counts),"new_pbf_files_written":out_count,
      "output_root":"Manila/New_Manila","source_pbf_modified":False,
      "method":"Uses the boundary layer inside source PBFs. Polygon boundary features are used directly; if the layer contains only lines, the merged linework is polygonized. Buildings are assigned by centroid to the smallest polygon that covers it. No nearest-line fallback.",
      "areas":[{"folder":f"area-{i+1:04d}","source_boundary_id":str(areas[i][0]),"properties":areas[i][1],"building_features":counts[i]} for i in range(len(areas))],
      "boundary_scan_errors":scan_errors,"building_scan_errors":tile_errors,
      "completed_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"README.md").write_text("# New_Manila: boundary-partitioned PBF dataset\n\n"+
      f"- Source tiles: {len(tiles)}\n- PBF boundary layers: {', '.join(sorted(boundary_layers))}\n"+
      f"- Areas: {len(areas)}\n- Building features assigned: {sum(counts)}\n- New PBF files: {out_count}\n"+
      "- Original PBFs modified: no\n- See summary.json for per-area counts and errors.\n",encoding="utf-8")
    print(json.dumps({"source_tiles":len(tiles),"boundary_areas":len(areas),"buildings_assigned":sum(counts),"new_pbf_files":out_count,"errors":len(scan_errors)+len(tile_errors)},ensure_ascii=False),flush=True)
    if not out_count: raise RuntimeError("No output PBF files were created.")
if __name__=="__main__": main()
