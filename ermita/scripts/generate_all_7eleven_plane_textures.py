#!/usr/bin/env python3
"""Generate image-textured vertical planes for every mapped 7-Eleven in Ermita.

This is a plane-texture signage experiment: each plane uses the official transparent
7-Eleven logo, is positioned against the nearest mapped building footprint, and is
exported as one independent GLB overlay. It does not replace buildings or windows.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import cairosvg, requests, trimesh
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "ermita/maps/generated/ermita-building-details.geojson"
STORES_FILE = ROOT / "complete_data/OSM/Markets/ermita-branded-stores.geojson"
ORIGIN_FILE = ROOT / "complete_data/OSM/Markets/commercial-facades-origin.json"
OUT_DIR = ROOT / "complete_data/OSM/Buildings/Markets/facidals"
OUT_GLB = OUT_DIR / "all-7eleven-plane-textures.glb"
OUT_REPORT = ROOT / "complete_data/OSM/Markets/all-7eleven-plane-textures-report.json"
ASSET_DIR = ROOT / "complete_data/OSM/Markets/assets"
OUT_PNG = ASSET_DIR / "7-eleven-plane-texture.png"
LOGO_URL = "https://www.7-eleven.com/assets/img/header/7e-logo-color.svg"
HEADERS = {"User-Agent": "Adam-City/1.0 (open-data 3D facade research; https://github.com/saeedhub101/Adam-City)"}
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform

def fid(f):
    p=f.get("properties") or {}
    return str(p.get("osm_feature_id") or f.get("id") or "")

def parts(g):
    if g.geom_type == "Polygon": return [g]
    if g.geom_type == "MultiPolygon": return list(g.geoms)
    return []

def nearest_edge(poly, pt):
    choices=[]
    coords=list(poly.exterior.coords)
    for a,b in zip(coords[:-1],coords[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        if length<2: continue
        t=max(0,min(1,((pt.x-a[0])*dx+(pt.y-a[1])*dy)/(length*length)))
        qx,qy=a[0]+t*dx,a[1]+t*dy
        choices.append((math.hypot(pt.x-qx,pt.y-qy),a,b,length,math.atan2(dy,dx)))
    return min(choices,key=lambda x:x[0]) if choices else None

def outward(poly,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
    nx,ny=dy/length,-dx/length
    mid=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
    if poly.contains(Point(mid.x+nx*.4,mid.y+ny*.4)): nx,ny=-nx,-ny
    return nx,ny

def main():
    for p in (MAP_FILE,STORES_FILE,ORIGIN_FILE):
        if not p.is_file(): raise FileNotFoundError(p)
    buildings=json.loads(MAP_FILE.read_text(encoding="utf-8")).get("features",[])
    stores=json.loads(STORES_FILE.read_text(encoding="utf-8")).get("features",[])
    targets=[]
    for f in stores:
        p=f.get("properties") or {}
        brand=str(p.get("brand") or p.get("name") or "").strip().lower()
        if "7-eleven" not in brand and "7 eleven" not in brand: continue
        g=f.get("geometry") or {}
        if g.get("type")!="Point": continue
        targets.append((f,geom_transform(PROJECT,Point(g["coordinates"]))))
    if not targets: raise RuntimeError("No mapped 7-Eleven point features found; refusing to produce an empty GLB")

    ASSET_DIR.mkdir(parents=True,exist_ok=True)
    response=requests.get(LOGO_URL,headers=HEADERS,timeout=45); response.raise_for_status()
    if b"<svg" not in response.content[:1000].lower(): raise RuntimeError("Official logo URL did not return SVG")
    cairosvg.svg2png(bytestring=response.content,write_to=str(OUT_PNG),output_width=900,output_height=1200)
    image=Image.open(OUT_PNG).convert("RGBA")
    ratio=image.width/max(1,image.height)
    logo_height=1.35
    logo_width=min(1.55,logo_height*ratio)
    origin=json.loads(ORIGIN_FILE.read_text(encoding="utf-8"))
    ox,oy=PROJECT(float(origin["longitude"]),float(origin["latitude"]))
    material=trimesh.visual.material.PBRMaterial(name="7-Eleven official logo plane texture",baseColorFactor=[255,255,255,255],baseColorTexture=image,metallicFactor=0.0,roughnessFactor=.85,alphaMode="BLEND",doubleSided=True)
    scene=trimesh.Scene()
    report=[]; used_buildings=set()
    for store,pt in targets:
        candidates=[]
        for b in buildings:
            geom=b.get("geometry") or {}
            if geom.get("type") not in ("Polygon","MultiPolygon"): continue
            try:
                projected=geom_transform(PROJECT,shape(geom))
                if projected.is_empty or not projected.is_valid: continue
                polys=parts(projected)
                if not polys: continue
                poly=max(polys,key=lambda x:x.area)
                distance=projected.distance(pt)
                if distance<=28: candidates.append((distance,b,poly))
            except Exception: continue
        if not candidates:
            report.append({"store_osm_id":fid(store),"status":"skipped","reason":"No mapped building footprint within 28 m"})
            continue
        candidates.sort(key=lambda x:x[0])
        distance,building,poly=candidates[0]
        edge=nearest_edge(poly,pt)
        if edge is None:
            report.append({"store_osm_id":fid(store),"status":"skipped","reason":"No usable facade edge"})
            continue
        edge_dist,a,b,length,angle=edge
        nx,ny=outward(poly,a,b)
        # The selected wall midpoint can be distant from the store along a large building.
        # Use the closest point on the chosen edge, not its midpoint.
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((pt.x-a[0])*dx+(pt.y-a[1])*dy)/(length*length)))
        cx=a[0]+t*dx+nx*.08; cy=a[1]+t*dy+ny*.08
        ux,uy=dx/length,dy/length
        z=2.45
        vertices=[[cx-ux*logo_width/2-ox,cy-uy*logo_width/2-oy,z-logo_height/2],
                  [cx+ux*logo_width/2-ox,cy+uy*logo_width/2-oy,z-logo_height/2],
                  [cx+ux*logo_width/2-ox,cy+uy*logo_width/2-oy,z+logo_height/2],
                  [cx-ux*logo_width/2-ox,cy-uy*logo_width/2-oy,z+logo_height/2]]
        mesh=trimesh.Trimesh(vertices=vertices,faces=[[0,1,2],[0,2,3]],process=False)
        mesh.visual=trimesh.visual.TextureVisuals(uv=[[0,1],[1,1],[1,0],[0,0]],material=material)
        mesh.metadata["type"]="flat plane with transparent 7-Eleven image texture"
        sid=fid(store) or f"store-{len(report)+1}"
        name=str((store.get("properties") or {}).get("name") or "7-Eleven")
        scene.add_geometry(mesh,node_name="7-Eleven plane texture "+sid)
        building_id=fid(building)
        report.append({"store_osm_id":sid,"store_name":name,"matched_building_osm_id":building_id,
          "poi_to_building_distance_m":round(distance,2),"poi_to_selected_facade_edge_m":round(edge_dist,2),
          "decal_width_m":round(logo_width,2),"decal_height_m":round(logo_height,2),
          "decal_center_height_m":z,"facade_offset_m":.08,"status":"generated"})
        used_buildings.add(building_id)
    generated=sum(1 for r in report if r.get("status")=="generated")
    if not generated: raise RuntimeError("All 7-Eleven placements failed; refusing to publish empty GLB")
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    OUT_GLB.write_bytes(scene.export(file_type="glb"))
    summary={"source_7eleven_points":len(targets),"generated_plane_textures":generated,"skipped":len(report)-generated,
      "unique_matched_buildings":len(used_buildings),"image_source":LOGO_URL,"image_asset":str(OUT_PNG.relative_to(ROOT)),
      "glb_path":str(OUT_GLB.relative_to(ROOT)),"glb_bytes":OUT_GLB.stat().st_size,
      "origin_file":str(ORIGIN_FILE.relative_to(ROOT)),
      "note":"Independent image-textured planes; approximate placements derived from OSM points and nearest building footprint edges, not surveyed facade measurements.",
      "placements":report}
    OUT_REPORT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="placements"},ensure_ascii=False,indent=2))
    if generated < max(1,int(len(targets)*.7)): raise RuntimeError(f"Only {generated}/{len(targets)} 7-Eleven signs placed; refusing to treat partial matching as complete")

if __name__=="__main__": main()
