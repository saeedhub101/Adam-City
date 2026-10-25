#!/usr/bin/env python3
from pathlib import Path
import math
import requests
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_bounds
from PIL import Image

ROOT=Path("complete_data/Government/Terrain")
RAW=Path("/tmp/cop-dem-90"); RAW.mkdir(parents=True,exist_ok=True)
OUT=ROOT/"terrarium"; OUT.mkdir(parents=True,exist_ok=True)
WEST,SOUTH,EAST,NORTH=33.0,28.0,41.0,35.0
BASE="https://copernicus-dem-90m.s3.amazonaws.com"
files=[]
for lat in range(28,35):
 for lon in range(33,41):
  ns="N" if lat>=0 else "S"; ew="E" if lon>=0 else "W"
  name=f"Copernicus_DSM_COG_30_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"
  url=f"{BASE}/{name}/{name}.tif"; path=RAW/(name+".tif")
  if not path.exists():
   try:
    with requests.get(url,stream=True,timeout=(20,120)) as r:
     if r.status_code==404: print("Missing tile",name); continue
     r.raise_for_status()
     with path.open("wb") as f:
      for chunk in r.iter_content(1024*1024):
       if chunk:f.write(chunk)
    if path.stat().st_size<10000: path.unlink(missing_ok=True); continue
   except Exception as e:
    path.unlink(missing_ok=True); print("Download failed",name,str(e)); continue
  files.append(path)
if not files: raise SystemExit("No public Copernicus GLO-90 tiles downloaded; check tile URLs.")
print("Downloaded tiles:",len(files))
srcs=[rasterio.open(p) for p in files]
mosaic,transform=merge(srcs,bounds=(WEST,SOUTH,EAST,NORTH),nodata=-32768)
profile=srcs[0].profile.copy()
profile.update(driver="GTiff",height=mosaic.shape[1],width=mosaic.shape[2],transform=transform,count=1,dtype="float32",crs="EPSG:4326",nodata=-32768,compress="DEFLATE",predictor=3,tiled=True,bigtiff="IF_SAFER")
ROOT.mkdir(parents=True,exist_ok=True)
dem_path=ROOT/"jordan-palestine-dem-glo90.tif"
with rasterio.open(dem_path,"w",**profile) as dst: dst.write(mosaic[0].astype("float32"),1)
for s in srcs:s.close()
def tile_bounds(z,x,y):
 n=2**z; west=x/n*360-180; east=(x+1)/n*360-180
 def lat(yy): return math.degrees(math.atan(math.sinh(math.pi*(1-2*yy/n))))
 return west,lat(y+1),east,lat(y)
def xtile(lon,z): return int((lon+180)/360*2**z)
def ytile(lat,z):
 lat=max(-85.05112878,min(85.05112878,lat))
 return int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*2**z)
with rasterio.open(dem_path) as src:
 for z in range(0,11):
  for x in range(max(0,xtile(WEST,z)),min(2**z-1,xtile(EAST,z))+1):
   for y in range(max(0,ytile(NORTH,z)),min(2**z-1,ytile(SOUTH,z))+1):
    b=tile_bounds(z,x,y)
    if b[2]<WEST or b[0]>EAST or b[3]<SOUTH or b[1]>NORTH: continue
    out=np.full((256,256),-32768,dtype=np.float32)
    dst_transform=from_bounds(*transform_bounds("EPSG:4326","EPSG:3857",*b),256,256)
    reproject(source=rasterio.band(src,1),destination=out,src_transform=src.transform,src_crs=src.crs,src_nodata=-32768,dst_transform=dst_transform,dst_crs="EPSG:3857",dst_nodata=-32768,resampling=Resampling.bilinear)
    valid=np.isfinite(out)&(out!=-32768)
    if not valid.any(): continue
    h=np.clip(np.where(valid,out,0)+32768,0,65535.996).astype(np.float32)
    rr=np.floor(h/256).astype(np.uint8); gg=np.floor(h-rr.astype(np.float32)*256).astype(np.uint8)
    bb=np.clip(np.rint((h-np.floor(h))*256),0,255).astype(np.uint8)
    rgba=np.stack([rr,gg,bb,np.where(valid,255,0).astype(np.uint8)],axis=-1)
    p=OUT/str(z)/str(x)/(str(y)+".png"); p.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(rgba,"RGBA").save(p,optimize=True)
  print("Generated zoom",z)
(ROOT/"README.md").write_text("""# Jordan + Palestine local elevation data

- jordan-palestine-dem-glo90.tif: clipped Copernicus DEM GLO-90 elevation raster.
- terrarium/{z}/{x}/{y}.png: locally stored Terrarium-encoded elevation tiles for MapLibre; zooms 0–10.
- Coverage bounds: 33°E–41°E, 28°N–35°N.
- Source: Copernicus DEM GLO-90, derived from WorldDEM/TanDEM-X.
- Required attribution: © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
- These are surface elevations (DSM), so vegetation and structures may affect heights. GLO-90 is approximately 90 m resolution.
""",encoding="utf-8")
print("Terrain build complete; PNG tiles:",sum(1 for p in OUT.rglob("*.png")))
