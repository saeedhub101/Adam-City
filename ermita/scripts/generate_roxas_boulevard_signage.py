#!/usr/bin/env python3
"""Generate a source-traceable signage overlay for the Roxas Boulevard GLB.

Deployment smoke-tested with the current Pages workflow.

Sign text is taken from the repository's OSM building and address/business records.
This generator never invents business names or house numbers. Unknown signage is
reported as missing instead of being mislabeled as photo-verified.
"""
from __future__ import annotations
import csv, json, math, re
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection, Point
from shapely.ops import transform as geom_transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings/ermita-building-footprints.geojson"
ROADS = ROOT / "complete_data/OSM/data/roads/ermita-road-network.geojson"
POIS = ROOT / "complete_data/OSM/data/addresses/ermita-addresses-street-names-postcodes.geojson"
OUT = ROOT / "complete_data/OSM/data/buildings/roxas-boulevard"
GLB = OUT / "roxas-boulevard-signage.glb"
REPORT = OUT / "roxas-boulevard-signage-report.json"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
FROM_METERS = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
BUFFER_M = 70.0
ATLAS_TILE_W, ATLAS_TILE_H, ATLAS_COLS = 256, 96, 8

def tags_of(f):
    p=f.get("properties") or {}
    t=p.get("tags")
    return {**p, **t} if isinstance(t,dict) else p

def polygons(g):
    if isinstance(g,Polygon): return [g]
    if isinstance(g,MultiPolygon): return list(g.geoms)
    if isinstance(g,GeometryCollection): return [p for x in g.geoms for p in polygons(x)]
    return []

def height_of(t):
    for key in ("height","building:height"):
        m=re.search(r"\d+(?:\.\d+)?",str(t.get(key) or ""))
        if m and 2 <= float(m.group()) <= 500: return float(m.group())
    m=re.search(r"\d+(?:\.\d+)?",str(t.get("building:levels") or t.get("levels") or ""))
    return max(3.2, float(m.group())*3.2) if m else 9.6

def feature_id(f):
    p=f.get("properties") or {}
    return str(p.get("osm_feature_id") or (f"{p.get('type')}/{p.get('id')}" if p.get("id") else ""))

def label_for(tags):
    name = tags.get("name") or tags.get("official_name") or tags.get("brand") or tags.get("operator") or ""
    number = tags.get("addr:housenumber") or tags.get("addr:unit") or ""
    brand = tags.get("brand") or ""
    if not name and not number: return None
    return {"name":str(name).strip(), "number":str(number).strip(), "brand":str(brand).strip()}

def main():
    for p in (BUILDINGS, ROADS, POIS):
        if not p.is_file(): raise FileNotFoundError(p)
    buildings=json.loads(BUILDINGS.read_text(encoding="utf-8"))["features"]
    roads=json.loads(ROADS.read_text(encoding="utf-8"))["features"]
    pois=json.loads(POIS.read_text(encoding="utf-8"))["features"]
    road_geoms=[]
    for f in roads:
        t=tags_of(f)
        road_name=" ".join(str(t.get(k) or "") for k in ("name","official_name","alt_name","name:en")).lower()
        if "roxas boulevard" not in road_name and "roxas blvd" not in road_name: continue
        try: road_geoms.append(geom_transform(TO_METERS,shape(f["geometry"])))
        except Exception: pass
    if not road_geoms: raise RuntimeError("No named Roxas Boulevard road geometries found")
    corridor=trimesh.util.concatenate([]) if False else None
    from shapely.ops import unary_union
    road_buffer=unary_union(road_geoms).buffer(BUFFER_M)
    selected=[]
    for f in buildings:
        try:
            g=geom_transform(TO_METERS,shape(f["geometry"]))
            t=tags_of(f)
            if not g.is_valid: g=g.buffer(0)
            if g.is_empty or g.geom_type not in ("Polygon","MultiPolygon") or not g.intersects(road_buffer): continue
            for poly in polygons(g):
                if poly.area >= 8: selected.append({"id":feature_id(f),"poly":poly,"tags":t,"height":height_of(t)})
        except Exception: continue
    if not selected: raise RuntimeError("No building footprints selected for Roxas Boulevard")
    # The source contains multiple building-part polygons per OSM building. Keep one
    # representative footprint per OSM ID so a tower does not receive hundreds of duplicate signs.
    by_id={}
    for item in selected:
        key=item["id"] or f"unnamed-part-{len(by_id)}"
        if key not in by_id or item["poly"].area > by_id[key]["poly"].area:
            by_id[key]=item
    selected=list(by_id.values())
    # Assign each named store/amenity node to its closest selected footprint only when the
    # point lies in/very close to that footprint. KartaView data are deliberately not used.
    polys=[x["poly"] for x in selected]
    tree=STRtree(polys)
    poi_by_building={}
    poi_count=0
    for f in pois:
        try:
            if f.get("geometry",{}).get("type")!="Point": continue
            t=tags_of(f)
            lbl=label_for(t)
            if not lbl or not (lbl["name"] or lbl["brand"]): continue
            pt=geom_transform(TO_METERS,Point(f["geometry"]["coordinates"]))
            # Restrict to actual businesses/institutions and address-bearing nodes.
            if not any(t.get(k) for k in ("shop","amenity","tourism","office","craft","leisure","healthcare","brand","addr:housenumber","building")): continue
            candidates=tree.query(pt.buffer(12))
            if len(candidates)==0: continue
            idx=min((int(i) for i in candidates),key=lambda i: polys[i].distance(pt))
            dist=polys[idx].distance(pt)
            if dist>12: continue
            poi_by_building.setdefault(idx,[]).append((dist,lbl,t,feature_id(f)))
            poi_count+=1
        except Exception: continue
    # Building sign takes precedence; attach nearby business signs too, up to three per footprint.
    signs=[]
    missing=[]
    for idx,item in enumerate(selected):
        own=label_for(item["tags"])
        candidates=[]
        if own: candidates.append((0.0,own,item["tags"],item["id"]))
        seen={own["name"].casefold() if own and own["name"] else ""}
        for dist,lbl,t,fid in sorted(poi_by_building.get(idx,[]),key=lambda x:x[0]):
            key=(lbl["name"] or lbl["brand"]).casefold()
            if key in seen: continue
            seen.add(key); candidates.append((dist,lbl,t,fid))
        if not candidates:
            missing.append(item["id"] or f"unnamed-footprint-{idx}")
            continue
        # The largest / main building gets a sign for its own name and up to two storefront signs.
        for ci,(dist,lbl,t,source_id) in enumerate(candidates[:3]):
            text=lbl["name"] or lbl["brand"]
            if not text and lbl["number"]: text=lbl["number"]
            if not text: continue
            signs.append({"building_index":idx,"building_id":item["id"],"poly":item["poly"],"height":item["height"],
                          "name":text,"number":lbl["number"],"brand":lbl["brand"],"source_id":source_id,
                          "source":"OSM tags / address point","sign_index":ci})
    if not signs: raise RuntimeError("No name/address labels available; refusing to emit an empty signage overlay")
    # One atlas keeps the overlay compact while retaining a distinct texture panel per sign.
    rows=math.ceil(len(signs)/ATLAS_COLS)
    atlas=Image.new("RGB",(ATLAS_TILE_W*ATLAS_COLS,ATLAS_TILE_H*rows),(238,235,225))
    draw=ImageDraw.Draw(atlas)
    try:
        font_bold=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",19)
        font_small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
    except OSError:
        font_bold=ImageFont.load_default(); font_small=ImageFont.load_default()
    vertices=[]; faces=[]; uvs=[]; records=[]
    # local model coordinates use the existing GLB's exact EPSG:3857 center.
    origin=json.loads((OUT/"roxas-bulivard-buildings-origin.json").read_text(encoding="utf-8"))
    cx,cy=TO_METERS(origin["longitude"],origin["latitude"])
    for i,s in enumerate(signs):
        col,row=i%ATLAS_COLS,i//ATLAS_COLS
        x0,y0=col*ATLAS_TILE_W,row*ATLAS_TILE_H
        poly=s["poly"]
        # Face the sign along the longest facade edge, set a shallow plaque just off the wall.
        edges=list(zip(list(poly.exterior.coords)[:-1],list(poly.exterior.coords)[1:]))
        eligible=[(math.hypot(b[0]-a[0],b[1]-a[1]),a,b) for a,b in edges if math.hypot(b[0]-a[0],b[1]-a[1])>1.6]
        if not eligible: continue
        length,a,b=max(eligible,key=lambda x:x[0])
        dx,dy=b[0]-a[0],b[1]-a[1]; tx,ty=dx/length,dy/length
        if poly.exterior.is_ccw: nx,ny=ty,-tx
        else: nx,ny=-ty,tx
        # Keep plaques near the front/lower facade; storefront panels sit lower than tower name signs.
        is_shop=bool(s["brand"] or any(k in s["name"].lower() for k in ("shop","store","restaurant","cafe","drug","market","bank")))
        z=min(max(2.4, s["height"]*0.18), max(2.5,s["height"]-0.8)) if is_shop else min(max(3.2,s["height"]*0.72),max(3.3,s["height"]-0.8))
        width=min(8.0,max(1.5,len(s["name"])*0.23+0.7),length*0.76)
        height=min(1.15,max(0.42,width*0.18))
        # OSM way winding is not a reliable facade-facing signal: make each panel outward on this edge.
        # Keep the plaque clearly outside the building's facade/detail meshes; 0.11 m was
        # buried behind the generated wall shells, so Three.js loaded the GLB but hid the signs.
        off=0.85
        center_u=length*0.5
        px=a[0]+tx*center_u+nx*off; py=a[1]+ty*center_u+ny*off
        verts=[
          [px-tx*width/2-cx,py-ty*width/2-cy,z],
          [px+tx*width/2-cx,py+ty*width/2-cy,z],
          [px+tx*width/2-cx+nx*0.025,py+ty*width/2-cy+ny*0.025,z+height],
          [px-tx*width/2-cx+nx*0.025,py-ty*width/2-cy+ny*0.025,z+height]]
        base=len(vertices); vertices.extend(verts)
        faces.extend([[base,base+1,base+2],[base,base+2,base+3]])
        uvs.extend([
          [x0/(ATLAS_TILE_W*ATLAS_COLS),(y0+ATLAS_TILE_H)/(ATLAS_TILE_H*rows)],
          [(x0+ATLAS_TILE_W)/(ATLAS_TILE_W*ATLAS_COLS),(y0+ATLAS_TILE_H)/(ATLAS_TILE_H*rows)],
          [(x0+ATLAS_TILE_W)/(ATLAS_TILE_W*ATLAS_COLS),y0/(ATLAS_TILE_H*rows)],
          [x0/(ATLAS_TILE_W*ATLAS_COLS),y0/(ATLAS_TILE_H*rows)]])
        # Plaque visual style: exact wording from source; recognizable brand color families are only a
        # fallback styling aid, not a claim of exact logo reconstruction.
        name=s["name"]
        brand=s["brand"].lower()
        if "7-eleven" in brand or "7 eleven" in brand: bg,fg=(0,112,63),(255,255,255)
        elif "mcdonald" in brand: bg,fg=(196,24,39),(255,210,0)
        elif "starbucks" in brand: bg,fg=(0,87,64),(255,255,255)
        elif "mercury drug" in brand: bg,fg=(206,22,45),(255,255,255)
        elif "jollibee" in brand: bg,fg=(212,24,39),(255,255,255)
        elif "kfc" in brand: bg,fg=(202,25,32),(255,255,255)
        elif "bank" in s["name"].lower() or "bpi" in brand: bg,fg=(27,54,100),(255,255,255)
        elif "hotel" in s["name"].lower() or "suites" in s["name"].lower(): bg,fg=(24,48,68),(242,224,180)
        else: bg,fg=(232,226,210),(40,45,49)
        draw.rounded_rectangle((x0+1,y0+1,x0+ATLAS_TILE_W-2,y0+ATLAS_TILE_H-2),radius=8,fill=bg,outline=(45,48,49),width=2)
        # Brand/name on first line, address/number on second when known.
        maxw=ATLAS_TILE_W-18
        label=name
        while draw.textbbox((0,0),label,font=font_bold)[2]>maxw and len(label)>5:
            label=label[:-1]
        if label!=name: label=label.rstrip()+"…"
        bb=draw.textbbox((0,0),label,font=font_bold)
        draw.text((x0+(ATLAS_TILE_W-(bb[2]-bb[0]))/2,y0+13),label,font=font_bold,fill=fg)
        detail=s["number"] or ("ROXAS BOULEVARD" if not is_shop else "")
        if detail:
            bb=draw.textbbox((0,0),detail,font=font_small)
            draw.text((x0+(ATLAS_TILE_W-(bb[2]-bb[0]))/2,y0+59),detail,font=font_small,fill=fg)
        records.append({k:s[k] for k in ("building_id","name","number","brand","source_id","source","sign_index")} | {"sign_width_m":round(width,2),"sign_height_m":round(height,2),"placement":"longest exterior footprint edge; estimated facade height","exact_photo_match":False})
    if not vertices: raise RuntimeError("No valid sign panels generated")
    mat=trimesh.visual.material.PBRMaterial(name="OSM_name_and_storefront_signage_atlas",
       baseColorFactor=[255,255,255,255],baseColorTexture=atlas,metallicFactor=0.02,roughnessFactor=0.66,
       alphaMode="OPAQUE",doubleSided=True)
    mesh=trimesh.Trimesh(vertices=np.asarray(vertices),faces=np.asarray(faces),process=False)
    mesh.visual=trimesh.visual.TextureVisuals(uv=np.asarray(uvs),material=mat)
    scene=trimesh.Scene(); scene.add_geometry(mesh,node_name="roxas_boulevard_source_name_signs",geom_name="roxas_boulevard_source_name_signs")
    OUT.mkdir(parents=True,exist_ok=True); GLB.write_bytes(scene.export(file_type="glb"))
    report={"output":str(GLB.relative_to(ROOT)),"sign_panels_generated":len(records),"buildings_with_at_least_one_sign":len({r["building_id"] for r in records}),
      "selected_building_parts":len(selected),"unlabelled_building_parts":len(missing),"unlabelled_ids_sample":missing[:80],
      "business_points_near_selected_buildings":poi_count,"named_roxas_road_features":len(road_geoms),"selection_buffer_m":BUFFER_M,
      "source":"OpenStreetMap contributors / repository address and business records, ODbL 1.0",
      "limitations":["Only names, brands and house numbers present in source tags are rendered; missing real-world text is not fabricated.",
       "Placement and panel dimensions are approximate and have not been individually matched to a current photograph.",
       "Brand-colored panels are visual stand-ins, not exact trademark logo artwork. A photo or verified logo asset is required for an exact sign."],
      "signs":records}
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="signs"},indent=2,ensure_ascii=False))
if __name__=="__main__": main()
