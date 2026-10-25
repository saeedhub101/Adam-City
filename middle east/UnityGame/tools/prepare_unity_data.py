#!/usr/bin/env python3
"""Build runtime data exclusively from middle east/Jordan and middle east/Palestine."""
import gzip,json
from pathlib import Path
GAME=Path(__file__).resolve().parents[1]
ROOT=GAME.parent
def read(p):
 with gzip.open(p,"rt",encoding="utf-8") as f:return json.load(f).get("features",[])
def val(p,*keys):
 for k in keys:
  v=p.get(k)
  if v not in (None,"","no"):return v
 return ""
def number(v):
 try:return float(str(v).lower().replace("meters","").replace("metres","").replace("m","").strip())
 except:return 0.0
def main():
 for region in ("Jordan","Palestine"):
  src=ROOT/region/"layers";out=GAME/"BuildData"/region;out.mkdir(parents=True,exist_ok=True);manifest={"region":region,"source":str(region+"/layers"),"layers":{}}
  for layer in ("buildings","streets"):
   path=src/(layer+".geojson.gz")
   if not path.exists():continue
   features=read(path);items=[]
   for f in features:
    g=f.get("geometry") or {};p=f.get("properties") or {};typ=g.get("type");coords=g.get("coordinates")
    if layer=="buildings" and typ in ("Polygon","MultiPolygon") and coords:
     polys=coords if typ=="MultiPolygon" else [coords]
     for poly in polys:
      if not poly or not poly[0]:continue
      ring=[[q[0],q[1]] for q in poly[0] if isinstance(q,list) and len(q)>1]
      if len(ring)<4:continue
      h=number(val(p,"height","building:height","render_height"));levels=number(val(p,"building:levels","levels","building_levels"))
      if h<=0:h=levels*3 if levels>0 else 6
      items.append({"id":str(f.get("id",len(items))),"name":str(val(p,"name","name:en")),"height":round(max(2.5,min(h,250)),2),"levels":int(levels),"material":str(val(p,"building:material","material")),"ring":ring})
    elif layer=="streets" and typ in ("LineString","MultiLineString") and coords:
     lines=[coords] if typ=="LineString" else coords
     for line in lines:
      pts=[[q[0],q[1]] for q in line if isinstance(q,list) and len(q)>1]
      if len(pts)>1:items.append({"name":str(val(p,"name","name:en","ref")),"highway":str(val(p,"highway")),"points":pts})
   name=layer+".runtime.json";target=out/name;target.write_text(json.dumps({"features":items},separators=(",",":"),ensure_ascii=False),encoding="utf-8")
   manifest["layers"][layer]={"file":name,"features":len(items),"bytes":target.stat().st_size};print(region,layer,len(items))
  (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
 print("Runtime data prepared; source archives unchanged.")
if __name__=="__main__":main()
