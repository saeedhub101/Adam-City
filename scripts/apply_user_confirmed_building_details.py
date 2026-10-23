#!/usr/bin/env python3
"""Apply user-confirmed address/name/storey/facade metadata to indexed building records."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "complete_data/OSM/data/buildings/Ermita"
PART = BASE / "ermita-buildings-master.parts/part-001-readable-parts/part-001.geojson"
QUEUE_CSV = BASE / "building-visual-research-queue.csv"
MASTER_CSV = BASE / "ermita-buildings-master.csv"
MANIFEST = BASE / "ermita-buildings-master-manifest.json"
README = BASE / "USER-CONFIRMED-BUILDING-DETAILS.md"

records = {
 "footprints-feature-000342": {
  "name":"Alkhaleej International Services Inc.", "source_name_or_brand":"Alkhaleej International Services Inc.",
  "building":"commercial", "building:levels":"2", "building_use":"commercial; shops",
  "addr:suburb":"Malate", "addr:street":"Roxas Boulevard", "addr:corner":"Quirino Street",
  "addr:city":"Manila", "addr:province":"Metro Manila", "addr:country":"Philippines",
  "address_full":"Malate, Roxas Boulevard corner Quirino Street, Manila, Metro Manila, Philippines",
  "source_colour":"gray-beige exposed concrete; dark-framed large glass facade",
  "source_material":"exposed concrete columns/canopy; large glass storefront windows with dark metal frames",
  "status":"user_confirmed_identity_and_visual_notes",
  "review_decision":"user_confirmed",
  "review_notes":"User-confirmed name, two-storey commercial use, street, area and corner. Facade color/material described from user-provided Google Street View screenshots (April 2026). Height in metres unknown."
 },
 "footprints-feature-000343": {
  "building":"commercial", "building:levels":"2", "building_use":"commercial",
  "addr:suburb":"Malate", "addr:street":"HXGP Vasquez Street", "addr:barangay":"696",
  "addr:city":"Manila", "addr:province":"Metro Manila", "addr:country":"Philippines",
  "address_full":"HXGP Vasquez St, Barangay 696, Manila, Metro Manila, Philippines",
  "status":"user_confirmed_identity_and_address",
  "review_decision":"user_confirmed",
  "review_notes":"User-confirmed commercial use, two storeys, street, barangay and area. Building name, facade materials and measured height not provided."
 }
}

def apply(props, fid):
    d = records.get(fid)
    if not d: return False
    props.update(d)
    return True

# Readable first part: update the existing two indexed features without changing coordinates/order.
obj=json.loads(PART.read_text(encoding="utf-8"))
changed=0
for f in obj.get("features",[]):
    p=f.setdefault("properties",{})
    fid=p.get("source_feature_id","")
    if apply(p,fid): changed+=1
PART.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")

# Update research queue CSV in-place, preserving all rows and adding searchable fields.
def update_csv(path, id_field_candidates):
    if not path.exists(): return {"path":str(path.relative_to(ROOT)),"status":"missing"}
    with path.open(encoding="utf-8-sig",newline="") as fp:
        reader=csv.DictReader(fp); fields=list(reader.fieldnames or []); rows=list(reader)
    extra=["name","building","building:levels","building_use","addr:suburb","addr:street","addr:corner","addr:barangay","addr:city","addr:province","addr:country","address_full","source_colour","source_material","review_decision","review_notes"]
    for k in extra:
        if k not in fields: fields.append(k)
    changed=0
    for row in rows:
        fid=next((row.get(k,"") for k in id_field_candidates if row.get(k,"")), "")
        if fid in records:
            # Preserve coordinates, feature IDs, and original geometry/source columns.
            for k,v in records[fid].items(): row[k]=v
            changed+=1
    with path.open("w",encoding="utf-8-sig",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return {"path":str(path.relative_to(ROOT)),"updated_rows":changed,"rows":len(rows),"columns":len(fields)}

queue_result=update_csv(QUEUE_CSV,["source_feature_id","source_feature_id"])
master_result=update_csv(MASTER_CSV,["source_feature_id","source_feature_id","feature_id","id"])
# Add a data dictionary note in the master manifest without altering its original source counts.
if MANIFEST.exists():
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    m["user_confirmed_building_updates"]={
      "records":["footprints-feature-000342","footprints-feature-000343"],
      "supplemental_files":[
        "complete_data/OSM/data/buildings/Ermita/user-confirmed-building-details.geojson",
        "complete_data/OSM/data/buildings/Ermita/user-confirmed-building-details.csv",
        "complete_data/OSM/data/buildings/Ermita/USER-CONFIRMED-BUILDING-DETAILS.md"
      ],
      "search_fields":["addr:suburb","addr:street","addr:corner","addr:barangay","addr:city","addr:province","addr:country","address_full"],
      "coordinates_preserved":True,
      "height_policy":"Storey count is recorded as supplied; measured height in metres remains unknown unless sourced independently."
    }
    MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"readable_geojson_features_updated":changed,"queue_csv":queue_result,"master_csv":master_result},ensure_ascii=False))
