#!/usr/bin/env python3
"""Generate incremental, compact facade/roof/storefront overlay GLBs for Adam-City.
Never modifies original GLBs or origin sidecars. Each part is independently resumable.
"""
import argparse, importlib.util, json, math
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import numpy as np
import trimesh
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geom_transform

ROOT=Path(__file__).resolve().parents[3]
PARTS=ROOT/"complete_data/OSM/data/buildings/Ermita"
SOURCE=ROOT/"ermita/maps/generated/ermita-building-footprints.geojson"
OUT=PARTS/"enhanced"
ENHANCEMENT_VERSION=4
GEN=ROOT/"ermita/scripts/generate_roxas_boulevard_buildings.py"
TO_M=Transformer.from_crs("EPSG:4326","EPSG:3857",always_xy=True).transform
spec=importlib.util.spec_from_file_location("facade_generator",GEN)
facade=importlib.util.module_from_spec(spec); spec.loader.exec_module(facade)

def mat(name,color,metal=0.0,rough=.8):
    # glTF PBR baseColorFactor is normalized 0..1, not 0..255.
    rgba=[float(v) for v in color]
    if max(rgba)>1.0: rgba=[v/255.0 for v in rgba]
    return trimesh.visual.material.PBRMaterial(name=name,baseColorFactor=rgba,metallicFactor=metal,roughnessFactor=rough)
def sign_texture(label):
    # Use the real OSM shop/brand label as visible text; never fabricate a logo.
    image=Image.new("RGBA",(512,128),(30,48,57,255))
    draw=ImageDraw.Draw(image)
    draw.rectangle((5,5,506,122),outline=(225,194,113,255),width=5)
    text=str(label or "STORE").strip()[:48]
    font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    size=54
    while size>16:
        try: font=ImageFont.truetype(font_path,size)
        except OSError: font=ImageFont.load_default(); break
        box=draw.textbbox((0,0),text,font=font)
        if box[2]-box[0]<=470 and box[3]-box[1]<=82: break
        size-=2
    box=draw.textbbox((0,0),text,font=font)
    draw.text(((512-(box[2]-box[0]))/2,(128-(box[3]-box[1]))/2-box[1]),text,font=font,fill=(255,255,255,255))
    return image
def box_mesh(center, extents, material, name):
    m=trimesh.creation.box(extents=extents); m.apply_translation(center)
    m.visual=trimesh.visual.TextureVisuals(material=material); m.metadata["name"]=name
    return m
def panel(a,b,z,width,height,offset,material,name,texture=None):
    dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
    if length<1:return None
    tx,ty=dx/length,dy/length
    nx,ny=ty,-tx
    cx=(a[0]+b[0])/2+nx*offset; cy=(a[1]+b[1])/2+ny*offset
    verts=[[cx-tx*width/2,cy-ty*width/2,z-height/2],[cx+tx*width/2,cy+ty*width/2,z-height/2],
           [cx+tx*width/2,cy+ty*width/2,z+height/2],[cx-tx*width/2,cy-ty*width/2,z+height/2]]
    m=trimesh.Trimesh(vertices=verts,faces=[[0,1,2],[0,2,3]],process=False)
    if texture is not None:
        m.visual=trimesh.visual.TextureVisuals(uv=np.array([[0,0],[1,0],[1,1],[0,1]],dtype=float),material=trimesh.visual.material.PBRMaterial(name=name+"_textured",baseColorFactor=[1,1,1,1],baseColorTexture=texture,metallicFactor=0.05,roughnessFactor=0.55))
    else:
        m.visual=trimesh.visual.TextureVisuals(material=material)
    m.metadata["name"]=name
    return m
def run(part):
    for p in (SOURCE,GEN,PARTS/f"part{part}"/f"part{part}-origin.json"):
        if not p.is_file(): raise FileNotFoundError(p)
    out=OUT/f"part{part}-roof-storefront-details.glb"
    report_path=OUT/f"part{part}-roof-storefront-details-report.json"
    if out.exists() and out.stat().st_size>1000 and report_path.is_file():
        try:
            prior=json.loads(report_path.read_text(encoding="utf-8"))
            check=trimesh.load(out,force="scene",process=False)
            if prior.get("enhancement_version")==ENHANCEMENT_VERSION and len(check.geometry)>0:
                print(f"part{part}: RESUME skip valid version-{ENHANCEMENT_VERSION} overlay {out}");return
        except Exception: pass
    origin=json.loads((PARTS/f"part{part}"/f"part{part}-origin.json").read_text())
    projected=origin.get("origin_projected_m") or {}; ox,oy=float(projected["x"]),float(projected["y"])
    bounds=origin.get("bounds_epsg3857_m") or {}
    minx,maxx=float(bounds["min_x"]),float(bounds["max_x"]);miny,maxy=float(bounds["min_y"]),float(bounds["max_y"])
    features=json.loads(SOURCE.read_text(encoding="utf-8")).get("features",[])
    scene=trimesh.Scene();seen=set();roof_count=0;ac_count=0;tank_count=0;sign_count=0;door_count=0;facade_count=0;skipped=0
    roofmat=mat("Weathered_roof_membrane",[145,139,127,255],0.03,.88)
    concrete=mat("Roof_parapet_concrete",[184,178,163,255],0.0,.9)
    acmat=mat("HVAC_matte_galvanized_metal",[158,164,168,255],.42,.48)
    tankmat=mat("Water_tank_polyethylene",[65,89,104,255],.03,.72)
    signmat=mat("Storefront_sign_enamel",[225,194,113,255],.12,.42)
    doormat=mat("Shop_door_dark_glass",[30,48,57,255],.18,.22)
    for fi,f in enumerate(features):
      if not f.get("geometry"):continue
      try:
       tags=facade.tags_of(f); geom=geom_transform(TO_M,shape(f["geometry"]))
       for pi,poly in enumerate(facade.polygon_parts(geom)):
        if poly.is_empty or not poly.is_valid or poly.area<18:continue
        cx,cy=poly.centroid.x,poly.centroid.y
        if not(minx<=cx<=maxx and miny<=cy<=maxy):continue
        key=poly.wkb
        if key in seen:continue
        seen.add(key);height=max(2.8,float(facade.height_of(tags) or 3.0))
        fid=str(tags.get("osm_feature_id") or f.get("id") or f"feature-{fi}").replace("/","_")
        # Preserve existing detailed glazing/PBR facade workflow as an overlay, not a replacement base.
        for maker,suffix in ((facade.facade_texture_mesh,"pbr_facade"),(facade.facade_accent_mesh,"facade_accents"),(facade.facade_base_mesh,"facade_base"),(facade.facade_podium_mesh,"podium"),(facade.facade_upper_band_mesh,"upper_bands"),(facade.facade_vertical_fin_mesh,"vertical_fins"),(facade.facade_planetarium_dome_mesh,"planetarium_dome"),(facade.facade_red_planet_canopy_mesh,"red_canopy")):
          try:
           if maker==facade.facade_texture_mesh:
            finish=facade.pbr_for(tags,fi); mesh=maker(poly,height,tags,*finish)
           else: mesh=maker(poly,height,tags,fi) if maker in (facade.facade_accent_mesh,facade.facade_base_mesh) else maker(poly,height,tags)
           if mesh is not None:
            mesh.apply_translation([-ox,-oy,0]); scene.add_geometry(mesh,node_name=f"{fid}_{suffix}_{fi}_{pi}");facade_count+=1
          except Exception: pass
        # Low-profile parapet rails on larger flat roofs, set inside the footprint.
        if poly.area>110 and height>=5:
         roofz=height
         for a,b in zip(list(poly.exterior.coords)[:-1],list(poly.exterior.coords)[1:]):
          length=math.hypot(b[0]-a[0],b[1]-a[1])
          if length<7:continue
          dx,dy=b[0]-a[0],b[1]-a[1];tx,ty=dx/length,dy/length
          # rail segments follow roof perimeter; avoid long thin geometry outside original footprint.
          rail=box_mesh(((a[0]+b[0])/2-ox,(a[1]+b[1])/2-oy,roofz+.42),(length*.92,.16,.84),concrete,f"{fid}_roof_parapet")
          angle=math.degrees(math.atan2(dy,dx));rail.apply_transform(trimesh.transformations.rotation_matrix(math.radians(angle),[0,0,1],point=((a[0]+b[0])/2-ox,(a[1]+b[1])/2-oy,roofz+.42)))
          scene.add_geometry(rail,node_name=f"{fid}_roof_parapet_{fi}_{pi}_{roof_count}");roof_count+=1
         # Evidence-neutral rooftop utility units: sparse, small, only on large roofs.
         if poly.area>240 and height<95:
          p=poly.representative_point()
          # Place two HVAC units on the roof, in local coordinates.
          for k,(dx,dy) in enumerate(((-1.6,-1.2),(1.6,1.0))):
           unit=box_mesh((p.x+dx-ox,p.y+dy-oy,roofz+.65),(1.5,1.0,1.05),acmat,f"{fid}_hvac")
           scene.add_geometry(unit,node_name=f"{fid}_hvac_{fi}_{pi}_{k}");ac_count+=1
          # One small water tank on selected large low/mid-rise roofs.
          if height<45:
           tank=trimesh.creation.cylinder(radius=.72,height=1.65,sections=12)
           tank.apply_translation((p.x+3.2-ox,p.y-2.5-oy,roofz+.825));tank.visual=trimesh.visual.TextureVisuals(material=tankmat)
           scene.add_geometry(tank,node_name=f"{fid}_water_tank_{fi}_{pi}");tank_count+=1
        # Storefront door and fascia signs only where source tags identify a shop/business.
        shop=any(tags.get(k) for k in ("shop","amenity","brand","office","craft","tourism")) or bool(tags.get("name") or tags.get("brand"))
        if shop and height>=2.5:
         coords=list(poly.exterior.coords)[:-1]
         if coords:
          a,b=max(zip(coords,coords[1:]+coords[:1]),key=lambda ab:math.hypot(ab[1][0]-ab[0][0],ab[1][1]-ab[0][1]))
          length=math.hypot(b[0]-a[0],b[1]-a[1])
          if length>=3:
           width=min(2.4,length*.35);z=min(1.35,height*.38)
           d=panel(a,b,z,width,2.35,.075,doormat,f"{fid}_storefront_door")
           if d is not None:
            d.apply_translation([-ox,-oy,0]);scene.add_geometry(d,node_name=f"{fid}_storefront_door_{fi}_{pi}");door_count+=1
           signname=str(tags.get("brand") or tags.get("name") or tags.get("shop") or tags.get("amenity") or "STORE")
           # Use real OSM text in metadata; plain fascia panel is a restrained placeholder, not fake logo artwork.
           sm=panel(a,b,min(height-.55,3.15),min(max(1.8,len(signname)*.24),length*.82),.62,.10,signmat,f"{fid}_sign_{signname}",texture=sign_texture(signname))
           if sm is not None:
            sm.apply_translation([-ox,-oy,0]);sm.metadata["source_label"]=signname
            scene.add_geometry(sm,node_name=f"{fid}_store_sign_{fi}_{pi}");sign_count+=1
      except Exception as e:
       skipped+=1
       if skipped<=8:print(f"part{part}: skipped feature {fi}: {e}")
    if len(scene.geometry)==0:raise RuntimeError(f"part{part}: generated no detail geometry")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(scene.export(file_type="glb"))
    check=trimesh.load(out,force="scene",process=False)
    if not isinstance(check,trimesh.Scene) or not check.geometry:raise RuntimeError(f"GLB validation failed: {out}")
    if out.stat().st_size>=95*1024*1024:raise RuntimeError(f"Overlay too large ({out.stat().st_size}); refusing >95 MiB output")
    report={"enhancement_version":ENHANCEMENT_VERSION,"part":part,"output":str(out.relative_to(ROOT)),"bytes":out.stat().st_size,"meshes":len(check.geometry),"roof_parapet_segments":roof_count,"hvac_units":ac_count,"water_tanks":tank_count,"storefront_sign_panels":sign_count,"storefront_doors":door_count,"facade_material_and_accent_meshes":facade_count,"skipped_features":skipped,"origin_projected_m":{"x":ox,"y":oy},"coordinate_policy":"overlay-only; original PartsN.glb and origin sidecar unchanged","notes":["Rooftop equipment is procedural illustrative detail, not verified building-by-building inventory.","Storefront fascia panels use names/brands from OSM tags where available; they are not exact logo artwork.","Real-time shadows are renderer-controlled, not baked into GLB. PBR materials include roughness and metalness."]
    }
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--part",type=int,choices=[1,2,3,4],required=True);a=p.parse_args();run(a.part)
