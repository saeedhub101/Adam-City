#!/usr/bin/env python3
"""Export separate additional OSM themes from the committed Ermita snapshot."""
from __future__ import annotations
import csv, hashlib, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ermita/maps/generated/ermita-features.geojson"
OSM = ROOT / "complete_data/OSM"
QUALITY = OSM / "quality"
LICENSE = "OpenStreetMap contributors, ODbL 1.0"

def tags_of(feature):
    p = feature.get("properties") or {}
    t = p.get("tags")
    if isinstance(t, dict):
        return t
    excluded = {"osm_feature_id", "osm_id", "type", "id", "source", "license"}
    return {k: v for k, v in p.items() if k not in excluded}

def fid(feature):
    p = feature.get("properties") or {}
    return str(p.get("osm_feature_id") or feature.get("id") or f'{p.get("type", "feature")}/{p.get("id", "unknown")}')

def is_address_or_street(f):
    t = tags_of(f)
    address = any(k.startswith("addr:") for k in t) or "postal_code" in t or "postcode" in t
    street = ("highway" in t or "railway" in t) and any(k in t for k in ("name", "official_name", "alt_name", "ref", "int_ref"))
    return address or street

def is_admin_boundary(f):
    t = tags_of(f)
    return t.get("boundary") == "administrative" or ("admin_level" in t and "boundary" in t)

def is_place_or_service(f):
    t = tags_of(f)
    keys = {"shop", "amenity", "healthcare", "office", "craft", "tourism", "public_transport", "emergency", "leisure"}
    building_values = {"school", "university", "college", "kindergarten", "hospital", "clinic", "church", "chapel", "mosque", "temple", "synagogue"}
    return bool(keys.intersection(t)) or t.get("building") in building_values or "religion" in t

def is_water_natural(f):
    t = tags_of(f)
    if "waterway" in t or "water" in t or "coastline" in t:
        return True
    if t.get("natural") in {"water", "wetland", "bay", "beach", "shoal", "spring", "hot_spring", "glacier", "reef", "bare_rock", "scree", "shingle", "sand", "mud", "cliff", "cave_entrance", "sinkhole", "volcano", "geyser"}:
        return True
    return t.get("landuse") in {"reservoir", "basin"} or t.get("leisure") == "water_park"

def is_vegetation(f):
    t = tags_of(f)
    if t.get("natural") in {"tree", "tree_row", "shrub", "wood", "scrub", "heath", "grassland", "wetland"}:
        return True
    return t.get("landuse") in {"forest", "grass", "meadow", "orchard", "vineyard", "plant_nursery"} or t.get("leisure") in {"park", "garden", "nature_reserve", "recreation_ground", "common"}

def write_layer(base, layer_name, features):
    geo_path, csv_path = base.with_suffix(".geojson"), base.with_suffix(".csv")
    geo_path.parent.mkdir(parents=True, exist_ok=True)
    collection = {"type":"FeatureCollection", "name":layer_name, "source":"https://www.openstreetmap.org/copyright",
                  "license":LICENSE, "provenance":str(SOURCE.relative_to(ROOT)), "feature_count":len(features), "features":features}
    geo_path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    fields = ["osm_feature_id","name","geometry_type","latitude","longitude","tags_json","source","license"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for feat in features:
            t, geom = tags_of(feat), feat.get("geometry") or {}
            p, coords = feat.get("properties") or {}, geom.get("coordinates")
            center = p.get("center") or {}; lat, lon = center.get("lat", ""), center.get("lon", "")
            if geom.get("type") == "Point" and isinstance(coords, list) and len(coords) >= 2:
                lon, lat = coords[0], coords[1]
            w.writerow({"osm_feature_id":fid(feat),"name":t.get("name",""),"geometry_type":geom.get("type",""),
                        "latitude":lat,"longitude":lon,"tags_json":json.dumps(t,ensure_ascii=False,sort_keys=True),
                        "source":"OpenStreetMap contributors","license":"ODbL 1.0"})
    return [geo_path, csv_path]

def git_blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main():
    if not SOURCE.is_file(): raise SystemExit(f"Missing committed OSM snapshot: {SOURCE}")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    features = source.get("features", [])
    if not isinstance(features, list): raise SystemExit("Source GeoJSON does not contain a features list.")
    specs = [
      ("addresses_street_names_postcodes","Address, street-name and postal-code features",OSM/"data/addresses/ermita-addresses-street-names-postcodes",is_address_or_street),
      ("administrative_boundaries","Administrative boundary features",OSM/"data/administrative/ermita-administrative-boundaries",is_admin_boundary),
      ("shops_food_health_education_religion_services","Shops, food, health, education, religion and services",OSM/"data/places/ermita-shops-food-health-education-religion-services",is_place_or_service),
      ("water_and_natural_features","Water bodies, waterways, coastline and natural features",OSM/"data/nature/ermita-water-and-natural-features",is_water_natural),
      ("trees_parks_vegetation","Trees, tree rows, parks and vegetation",OSM/"data/nature/ermita-trees-parks-vegetation",is_vegetation),
    ]
    outputs, report = [], {"source_file":str(SOURCE.relative_to(ROOT)),"source_feature_count":len(features),
      "method":"Export from existing committed snapshot; no live Overpass request.","license":LICENSE,"layers":{}}
    for key, desc, base, predicate in specs:
        selected = [f for f in features if predicate(f)]
        paths = write_layer(base,key,selected); outputs.extend(paths)
        key_counts, value_counts, geom_counts = Counter(), Counter(), Counter()
        relevant = {"addr:postcode","postcode","postal_code","admin_level","boundary","shop","amenity","healthcare","office","craft","tourism","natural","waterway","water","leisure","landuse","religion","building","name"}
        for feat in selected:
            t = tags_of(feat); key_counts.update(t.keys()); geom_counts[(feat.get("geometry") or {}).get("type","None")] += 1
            for k,v in t.items():
                if k in relevant: value_counts[f"{k}={v}"] += 1
        report["layers"][key] = {"description":desc,"feature_count":len(selected),"files":[str(p.relative_to(OSM)) for p in paths],
          "geometry_type_counts":dict(sorted(geom_counts.items())),"tag_key_presence_counts":dict(sorted(key_counts.items())),
          "selected_tag_value_counts":dict(sorted(value_counts.items()))}
    report_path = QUALITY/"osm-additional-theme-export-report.json"; QUALITY.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); outputs.append(report_path)

    manifest_path = OSM/"manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.setdefault("files", []); output_relpaths = {str(p.relative_to(ROOT)) for p in outputs}
    entries[:] = [e for e in entries if e.get("copied_path") not in output_relpaths]
    descriptions = {
      "ermita-addresses-street-names-postcodes":"OSM addresses, street names and postal-code attributes",
      "ermita-administrative-boundaries":"OSM administrative boundaries and administrative levels",
      "ermita-shops-food-health-education-religion-services":"OSM shops, food, health, education, religious institutions and services",
      "ermita-water-and-natural-features":"OSM waterways, water bodies, coastlines and natural features",
      "ermita-trees-parks-vegetation":"OSM trees, tree rows, parks and vegetation",
      "osm-additional-theme-export-report":"Counts, geometry types, tag keys and selected values for additional OSM exports"}
    for path in outputs:
        rel, stem = str(path.relative_to(ROOT)), path.stem
        desc = next((v for k,v in descriptions.items() if stem.startswith(k)), "OSM additional-theme export report")
        entries.append({"source_path":str(SOURCE.relative_to(ROOT)),"copied_path":rel,"size_bytes":path.stat().st_size,"blob_sha":git_blob_sha(path),"description":desc})
    manifest["note"] = "Original OSM snapshot and source files are preserved. Separate pedestrian, road, building, address, administrative, services, water/natural and vegetation datasets are derived from the committed feature snapshot; these exports are not a fresh Overpass download. Every exported file is inventoried below."
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    readme_path = OSM/"README.md"; readme = readme_path.read_text(encoding="utf-8")
    start, end = "<!-- ADDITIONAL OSM THEMES START -->", "<!-- ADDITIONAL OSM THEMES END -->"
    section = (start+"\n## Additional OSM themes\n\n"+
      "The following independent layers are exported from ermita/maps/generated/ermita-features.geojson:\n\n"+
      "- data/addresses/ermita-addresses-street-names-postcodes — address tags, street names and postal-code attributes.\n"+
      "- data/administrative/ermita-administrative-boundaries — administrative boundaries and levels.\n"+
      "- data/places/ermita-shops-food-health-education-religion-services — mapped shops, food, health, education, religious institutions and services.\n"+
      "- data/nature/ermita-water-and-natural-features — mapped waterways, water bodies, coastlines and other natural features.\n"+
      "- data/nature/ermita-trees-parks-vegetation — trees, tree rows, parks, gardens and vegetation.\n"+
      "- quality/osm-additional-theme-export-report.json — counts, geometry types, tag-key coverage and selected tag values.\n\n"+
      "Each layer has CSV and GeoJSON files. GeoJSON retains source geometries and original tags; CSV provides searchable rows with tags_json. Categories can overlap when a source feature carries multiple themes. Missing values are not inferred. This run re-exports the committed snapshot; it does not fetch live OSM data. Refresh the OSM snapshot separately if newer or absent source features are required.\n"+end)
    if start in readme and end in readme:
        readme = readme.split(start)[0].rstrip()+"\n\n"+section+"\n\n"+readme.split(end,1)[1].lstrip()
    else: readme = readme.rstrip()+"\n\n"+section+"\n"
    readme_path.write_text(readme,encoding="utf-8")
    print("Source features:",len(features))
    for key,data in report["layers"].items(): print(key+":",data["feature_count"],"features")
    print("Generated",len(outputs),"CSV/GeoJSON/report files; updated manifest and README.")

if __name__ == "__main__": main()
