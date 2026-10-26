#!/usr/bin/env python3
"""Download-free-after-import classifier for a fresh, clipped OSM GeoJSON export."""
import gzip, json, pathlib, sys, ijson

TAGS={
 "buildings":lambda p: p.get("building") not in (None,"no",""),
 "building_details":lambda p: p.get("building") not in (None,"no","") or any(k.startswith(("building:","roof:","addr:")) for k in p),
 "streets":lambda p: p.get("highway") not in (None,""),
 "streetnames":lambda p: p.get("highway") not in (None,"") and bool(p.get("name") or p.get("name:en")),
 "addresses":lambda p: any(k.startswith("addr:") for k in p),
 "water":lambda p: any(p.get(k) not in (None,"") for k in ("natural","water","waterway")) and (p.get("natural") in ("water","wetland","spring") or p.get("water") or p.get("waterway")),
 "landcover":lambda p: any(p.get(k) not in (None,"") for k in ("landuse","leisure","natural","surface")),
 "places":lambda p: p.get("place") not in (None,""),
}
def main(src,dst):
 src=pathlib.Path(src);dst=pathlib.Path(dst);dst.mkdir(parents=True,exist_ok=True)
 out={k:gzip.open(dst/(k+".geojson.gz"),"wt",encoding="utf-8",compresslevel=5) for k in TAGS}
 counts={k:0 for k in TAGS}
 try:
  for f in out.values(): f.write('{"type":"FeatureCollection","features":[')
  first={k:True for k in TAGS}
  with src.open("rb") as inp:
   for feature in ijson.items(inp,"features.item"):
    p=feature.get("properties") or {}
    for name,match in TAGS.items():
     if match(p):
      if not first[name]: out[name].write(",")
      json.dump(feature,out[name],ensure_ascii=False,separators=(",",":"))
      first[name]=False;counts[name]+=1
  for name,f in out.items():
   f.write("]}")
   print("SOURCE_LAYER",name,"features",counts[name],flush=True)
 finally:
  for f in out.values(): f.close()
 if not counts["buildings"] or not counts["streets"]:
  raise SystemExit("Fresh source export contains no buildings or streets: "+json.dumps(counts))
 (dst/"source-import-report.json").write_text(json.dumps({"source":"Geofabrik Jordan OSM PBF, clipped to Tabarbour","counts":counts},indent=2),encoding="utf-8")
if __name__=="__main__":
 if len(sys.argv)!=3: raise SystemExit("usage: import_tabarbour_source_layers.py <osm-export.geojson> <output-dir>")
 main(sys.argv[1],sys.argv[2])
