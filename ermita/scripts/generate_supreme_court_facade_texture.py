#!/usr/bin/env python3
"""Create a photographic facade overlay for the existing Supreme Court OSM building.
The original OSM footprint/extrusion is preserved; this is only a shallow textured panel.
Photo: Aerous, Wikimedia Commons, CC BY-SA 3.0.
"""
from pathlib import Path
import io, json, math, requests, trimesh
from PIL import Image
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "complete_data/OSM/data/buildings/ermita-building-details.geojson"
OUT = ROOT / "complete_data/OSM/Buildings/supreme-court-main-facade.glb"
ASSET_DIR = ROOT / "complete_data/OSM/Buildings/reference_images"
PHOTO = ASSET_DIR / "supreme-court-in-manila-facade-crop.jpg"
REPORT = ROOT / "complete_data/OSM/Buildings/supreme-court-main-facade-report.json"
PHOTO_URL = "https://upload.wikimedia.org/wikipedia/commons/6/64/Supreme_Court_in_Manila.JPG"
PHOTO_PAGE = "https://commons.wikimedia.org/wiki/File:Supreme_Court_in_Manila.JPG"
LICENSE = "CC BY-SA 3.0"
HEADERS = {"User-Agent":"Adam-City/1.0 (facade texture research; https://github.com/saeedhub101/Adam-City)"}
PROJECT = Transformer.from_crs("EPSG:4326","EPSG:3857",always_xy=True).transform

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    target = next((f for f in data["features"] if str(f.get("properties",{}).get("osm_feature_id","")) == "way/156307566"), None)
    if not target:
        raise RuntimeError("OSM target way/156307566 (Supreme Court Main Building) was not found")
    ASSET_DIR.mkdir(parents=True,exist_ok=True)
    if not PHOTO.exists() or PHOTO.stat().st_size < 10000:
        r=requests.get(PHOTO_URL,headers=HEADERS,timeout=60); r.raise_for_status()
        source=Image.open(io.BytesIO(r.content)).convert("RGB")
        # Crop the central portico: columns, entrance, decorative frieze and pale stone.
        # The narrow crop intentionally avoids most foreground cars and the right-side tree.
        w,h=source.size
        crop=source.crop((int(w*.16),int(h*.30),int(w*.70),int(h*.82)))
        crop.thumbnail((1800,1800),Image.Resampling.LANCZOS)
        crop.save(PHOTO,quality=94,optimize=True)
    image=Image.open(PHOTO).convert("RGB")
    # The mapped footprint's Padre Faura-facing southern edge. Coordinates are from the
    # existing OSM polygon; only the photo panel is added, not a replacement building.
    p1=PROJECT(120.9843193,14.5795662)
    p2=PROJECT(120.9846428,14.5797339)
    dx,dy=p2[0]-p1[0],p2[1]-p1[1]
    edge_len=math.hypot(dx,dy)
    ux,uy=dx/edge_len,dy/edge_len
    # For this polygon, southeast is the exterior side of the south edge.
    nx,ny=uy,-ux
    width=min(15.0,edge_len-2.0)
    height=width/(image.width/image.height)
    cx,cy=(p1[0]+p2[0])/2+nx*0.22,(p1[1]+p2[1])/2+ny*0.22
    left=(cx-ux*width/2,cy-uy*width/2)
    right=(cx+ux*width/2,cy+uy*width/2)
    z0,z1=0.65,0.65+height
    # GLB coordinates are projected-metre offsets from the exact shared origin in
    # complete_data/OSM/Markets/commercial-facades-origin.json.
    origin_x,origin_y=PROJECT(120.98204159999997,14.58501519429619)
    vertices=[
      [left[0]-origin_x,left[1]-origin_y,z0],[right[0]-origin_x,right[1]-origin_y,z0],
      [right[0]-origin_x,right[1]-origin_y,z1],[left[0]-origin_x,left[1]-origin_y,z1]
    ]
    faces=[[0,1,2],[0,2,3]]
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    uv=[[0,1],[1,1],[1,0],[0,0]]
    material=trimesh.visual.material.PBRMaterial(
      name="SupremeCourtPhotographicFacade",
      baseColorTexture=image,
      metallicFactor=0.0,roughnessFactor=0.92,doubleSided=True)
    mesh.visual=trimesh.visual.TextureVisuals(uv=uv,material=material)
    scene=trimesh.Scene()
    scene.add_geometry(mesh,node_name="SupremeCourtMainFacadePhotoPlane",geom_name="SupremeCourtMainFacadePhotoPlane")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    scene.export(OUT,file_type="glb")
    report={
      "target":"Supreme Court Main Building","osm_feature_id":"way/156307566",
      "method":"single photographic Plane Texture overlay on the existing OSM extrusion; no replacement geometry",
      "glb":str(OUT.relative_to(ROOT)),"texture":str(PHOTO.relative_to(ROOT)),
      "source_photo":PHOTO_PAGE,"photographer":"Aerous","license":LICENSE,
      "photo_crop":"central portico, columns, entrance, frieze; cropped from the 4272x2848 source",
      "panel_width_m":round(width,2),"panel_height_m":round(height,2),
      "limitations":"A first real-world visual test. It is a single-view photographic decal, so the photo will not wrap around corners; inspect alignment in the map before adjusting placement."
    }
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
    if OUT.stat().st_size < 10000: raise RuntimeError("Generated GLB unexpectedly small")

if __name__=="__main__": main()
