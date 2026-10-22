#!/usr/bin/env python3
"""Conservative, repository-first enrichment of Ermita master building records.

Only explicit OSM IDs or exact stable source-feature IDs are used for joins.
Geometry, coordinates, feature IDs, source IDs, and rendering heights are never
rewritten. Candidate images and business tenants are stored as candidates, not
mistaken for verified facade observations.
"""
from __future__ import annotations
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "manila/manila"
CSV_PATH = MASTER / "ermita-buildings-master.csv"
PARTS = [MASTER / "ermita-buildings-master.parts/part-001.geojson",
         MASTER / "ermita-buildings-master.parts/part-002.geojson"]
REPORT = MASTER / "ermita-master-enrichment-report.json"

SOURCE_PATHS = {
    "osm_details": ROOT / "complete_data/OSM/data/buildings/Ermita/osm-building-details.csv",
    "height_evidence": ROOT / "complete_data/OSM/quality/building-height-evidence.csv",
    "match_audit": ROOT / "ermita/3d/building-match-audit.csv",
    "detailed_tags": ROOT / "ermita/maps/generated/ermita-building-details.csv",
    "signage_index": ROOT / "complete_data/OSM/data/buildings/windows/facade-signage-index.csv",
    "consolidated_register": ROOT / "ermita/maps/qa/consolidated-building-register.csv",
    "facade_photos": ROOT / "ermita/3d/facade-photo-review.csv",
    "real_facade_images": ROOT / "kartaview/ermita-real-facade-images.csv",
    "brand_matches": ROOT / "ermita/stores/brand-building-match-audit.csv",
    "image_candidates": ROOT / "complete_data/OSM/data/buildings/Ermita/building-image-candidates.csv",
    "source_link_audit": ROOT / "complete_data/OSM/data/buildings/Ermita/building-source-link-audit.csv",
}

TARGETS = {
    "name": ("name", "official_name", "building_name"),
    "official_name": ("official_name",),
    "alt_name": ("alt_name", "altname"),
    "building_type": ("building", "building:part", "building_type"),
    "building_part": ("building:part", "building_part"),
    "building_use": ("building:use", "building_use", "use"),
    "height_m": ("height", "building:height", "height_tag_m", "height_m"),
    "levels": ("building:levels", "levels", "building_levels_tag"),
    "underground_levels": ("building:levels:underground", "building_levels_underground"),
    "min_level": ("building:min_level", "min_level"),
    "min_height_m": ("min_height", "min_height_tag_m"),
    "roof_shape": ("roof:shape", "roof_shape_tag", "roof_shape"),
    "roof_height_m": ("roof:height", "roof_height"),
    "roof_levels": ("roof:levels", "roof_levels"),
    "roof_angle": ("roof:angle", "roof_angle"),
    "roof_direction": ("roof:direction", "roof_direction"),
    "house_number": ("addr:housenumber", "address_housenumber"),
    "street": ("addr:street", "address_street"),
    "suburb": ("addr:suburb", "address_suburb"),
    "postcode": ("addr:postcode", "address_postcode"),
    "city": ("addr:city", "address_city"),
    "material": ("building:material", "facade:material", "material"),
    "facade_colour": ("building:colour", "building:color", "facade:colour", "facade_colour"),
    "roof_material": ("roof:material", "roof_material"),
    "roof_colour": ("roof:colour", "roof:color", "roof_colour"),
    "operator": ("operator",),
    "entrance": ("entrance",),
    "access": ("access",),
    "start_date": ("start_date", "building:start_date"),
    "architect": ("architect",),
    "heritage": ("heritage",),
    "historic": ("historic",),
    "wikidata": ("wikidata",),
    "wikipedia": ("wikipedia",),
    "website": ("website", "contact:website"),
    "building_condition": ("building:condition", "condition"),
}
OUT_FIELDS = [f"enriched_{k}" for k in TARGETS] + [
    "enrichment_sources", "enrichment_status",
    "enriched_photo_candidate_count", "enriched_photo_candidate_urls",
    "enriched_photo_candidate_ids", "enriched_photo_candidate_evidence",
    "enriched_business_names", "enriched_business_brands",
    "enriched_business_osm_ids", "enriched_business_addresses",
    "enriched_business_match_status",
    "enriched_model_estimated_height_m", "enriched_model_estimated_floor_count",
    "enriched_signage_panel_generated", "enriched_sign_text_verified",
]

def s(v):
    return "" if v is None else str(v).strip()

def norm_value(v):
    v=s(v)
    if not v or v.lower() in {"none","null","unknown","n/a","nan","-"}: return ""
    return v

def normalize_id(v):
    v=s(v)
    if re.fullmatch(r"(?:node|way|relation)/\d+", v): return v
    if re.fullmatch(r"\d+", v): return v
    return ""

def osm_id(row):
    for k in ("osm_feature_id", "linked_osm_feature_id", "building_osm_id",
              "source_feature_id", "source_id", "source_element_id", "osm_id"):
        v = s(row.get(k))
        if re.fullmatch(r"(?:node|way|relation)/\d+", v):
            return v
        typ = s(row.get("osm_type") or row.get("element_type") or row.get("type"))
        if re.fullmatch(r"\d+", v) and typ in {"node","way","relation"}:
            return f"{typ}/{v}"
    return ""

def read_csv(path):
    if not path.is_file(): return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def add_candidate(index, ident, source, fields):
    if not ident: return
    for target, aliases in TARGETS.items():
        vals=[]
        for alias in aliases:
            val=norm_value(fields.get(alias))
            if val and val not in vals: vals.append(val)
        if len(vals)==1:
            index[ident][target].append((vals[0], source))

def parse_tags(row):
    for key in ("tags_json", "all_tags_json", "tags"):
        raw = row.get(key)
        if raw:
            try:
                value=json.loads(raw)
                if isinstance(value, dict): return value
            except Exception:
                pass
    return {}

def load_sources():
    idx=defaultdict(lambda: defaultdict(list))
    source_rows=Counter()
    feature_id_map={}
    photos=defaultdict(list)
    businesses=defaultdict(list)
    signage=defaultdict(list)
    image_candidates=defaultdict(list)

    # Direct OSM detail exports: tags are the primary source for explicit metadata.
    for source_key in ("osm_details", "detailed_tags"):
        path=SOURCE_PATHS[source_key]
        for row in read_csv(path):
            ident=osm_id(row)
            tags=parse_tags(row)
            fields={**row, **tags}
            if not fields.get("name"): fields["name"]=row.get("name")
            add_candidate(idx, ident, path.name, fields)
            source_rows[path.name]+=1

    for source_key in ("height_evidence", "match_audit"):
        path=SOURCE_PATHS[source_key]
        for row in read_csv(path):
            ident=osm_id(row)
            fields=dict(row)
            add_candidate(idx, ident, path.name, fields)
            source_rows[path.name]+=1

    # The consolidated register is source-attributed text. Only accept a field
    # when every listed source agrees on the same value after removing citations.
    path=SOURCE_PATHS["consolidated_register"]
    for row in read_csv(path):
        ident=osm_id(row)
        if not ident: continue
        mapping={
            "name":"names_by_source", "building_type":"building_type_by_source",
            "height_m":"height_by_source", "levels":"levels_by_source",
            "roof_shape":"roof_shape_by_source", "roof_material":"roof_material_by_source",
            "material":"building_material_by_source", "facade_colour":"building_colour_by_source",
            "street":"address_by_source",
        }
        fields={}
        for target, col in mapping.items():
            raw=norm_value(row.get(col))
            if not raw: continue
            pieces=[p.strip() for p in raw.split(" | ") if p.strip()]
            clean=[]
            for piece in pieces:
                piece=re.sub(r"\s*\[[^\]]+\]\s*$","",piece).strip()
                if piece and piece not in clean: clean.append(piece)
            if len(clean)==1: fields[TARGETS[target][0]]=clean[0]
        add_candidate(idx, ident, path.name, fields)
        source_rows[path.name]+=1

    # Explicit source-feature to OSM crosswalks only when accepted by the source audit.
    path=SOURCE_PATHS["source_link_audit"]
    for row in read_csv(path):
        accepted=s(row.get("openfreemap_candidate_accepted")).lower() in {"true","1","yes"}
        source_id=normalize_id(row.get("openfreemap_source_feature_id") or row.get("source_feature_id"))
        linked=osm_id(row)
        if accepted and source_id and linked:
            feature_id_map[source_id]=linked
        source_rows[path.name]+=1

    # Photo sources are candidates only: direction/position metadata does not mean
    # a human verified the actual facade in the image.
    for source_key in ("facade_photos", "real_facade_images"):
        path=SOURCE_PATHS[source_key]
        for row in read_csv(path):
            ident=osm_id(row)
            if not ident: continue
            url=norm_value(row.get("image_url"))
            if not url: continue
            photos[ident].append({
                "photo_id":norm_value(row.get("photo_id")),
                "url":url,
                "date":norm_value(row.get("capture_date")),
                "status":norm_value(row.get("match_status")),
                "distance_m":norm_value(row.get("distance_to_building_wall_m")),
                "heading_difference_deg":norm_value(row.get("heading_difference_deg")),
                "license":norm_value(row.get("license")),
                "source_page":norm_value(row.get("source_page")),
                "local_image":norm_value(row.get("local_image")),
                "visual_verified":norm_value(row.get("visual_facade_verified")),
                "source":path.name,
            })
            source_rows[path.name]+=1

    path=SOURCE_PATHS["brand_matches"]
    for row in read_csv(path):
        ident=norm_value(row.get("nearest_building_osm_id"))
        if not re.fullmatch(r"(?:node|way|relation)/\d+", ident): continue
        if norm_value(row.get("match_status")) != "inside_footprint": continue
        businesses[ident].append({
            "name":norm_value(row.get("store_name")),
            "brand":norm_value(row.get("brand")),
            "store_id":norm_value(row.get("store_osm_id")),
            "street":norm_value(row.get("street")),
            "house_number":norm_value(row.get("house_number")),
            "status":norm_value(row.get("match_status")),
        })
        source_rows[path.name]+=1

    path=SOURCE_PATHS["signage_index"]
    for row in read_csv(path):
        ident=osm_id(row)
        if ident:
            signage[ident].append({
                "height":norm_value(row.get("building_height_m")),
                "levels":norm_value(row.get("estimated_floor_count")),
                "panel":norm_value(row.get("sign_panel_generated")),
                "verified":norm_value(row.get("sign_text_or_logo_verified")),
            })
        source_rows[path.name]+=1

    path=SOURCE_PATHS["image_candidates"]
    for row in read_csv(path):
        fid=normalize_id(row.get("source_feature_id"))
        if fid:
            image_candidates[fid].append({
                "url":norm_value(row.get("image_url")),
                "title":norm_value(row.get("image_title")),
                "page":norm_value(row.get("image_page")),
                "status":norm_value(row.get("status")),
                "license":norm_value(row.get("license_short_name")),
                "source_feature_id":fid,
            })
        source_rows[path.name]+=1

    return idx, source_rows, feature_id_map, photos, businesses, signage, image_candidates

def resolve(idx, ident):
    result={}
    conflicts={}
    used=set()
    for target in TARGETS:
        by_value=defaultdict(set)
        for value, source in idx.get(ident, {}).get(target, []): by_value[value].add(source)
        if len(by_value)==1:
            value, sources=next(iter(by_value.items()))
            result[f"enriched_{target}"]=value
            used.update(sources)
        elif len(by_value)>1:
            conflicts[target]={v:sorted(srcs) for v,srcs in sorted(by_value.items())}
    result["enrichment_sources"]=";".join(sorted(used))
    result["enrichment_status"]="conflict_review" if conflicts else ("exact_id_enriched" if used else "no_exact_id_evidence")
    return result, conflicts

def first_feature_id(props, feature):
    for key in ("source_feature_id","openfreemap_source_feature_id","feature_id","source_id","id","osm_feature_id"):
        val=normalize_id(props.get(key))
        if val: return val
    val=normalize_id(feature.get("id"))
    return val

def put_field(record, key, value, sparse=False):
    value = s(value)
    if sparse and not value:
        record.pop(key, None)
    else:
        record[key] = value

def decorate_record(record, ident, feature_id, idx, photos, businesses, signage, image_candidates, sparse=False):
    values, conflicts=resolve(idx, ident) if ident else ({}, {})
    for field in [f"enriched_{k}" for k in TARGETS]:
        # Keep the CSV schema explicit; in GeoJSON omit empty properties to control file size.
        put_field(record, field, values.get(field,""), sparse)
    put_field(record, "enrichment_sources", values.get("enrichment_sources",""), sparse)
    status = values.get("enrichment_status","no_exact_id_evidence")
    if sparse and not ident and status == "no_exact_id_evidence":
        record.pop("enrichment_status", None)
    else:
        record["enrichment_status"] = status
    photo_rows=photos.get(ident,[]) if ident else []
    image_rows=image_candidates.get(feature_id,[]) if feature_id else []
    all_photos=[]
    seen=set()
    for item in photo_rows:
        key=item["url"]
        if key not in seen: seen.add(key); all_photos.append(item)
    for item in image_rows:
        key=item["url"]
        if key and key not in seen:
            seen.add(key)
            all_photos.append({**item,"photo_id":"","date":"","status":item.get("status","candidate"),"distance_m":"","heading_difference_deg":"","source_page":item.get("page",""),"local_image":"","visual_verified":"NO","source":"building-image-candidates.csv"})
    put_field(record, "enriched_photo_candidate_count", str(len(all_photos)) if all_photos else "", sparse)
    put_field(record, "enriched_photo_candidate_urls", ";".join(x["url"] for x in all_photos if x.get("url")), sparse)
    put_field(record, "enriched_photo_candidate_ids", ";".join(x.get("photo_id") or x.get("source_feature_id","") for x in all_photos if x.get("photo_id") or x.get("source_feature_id")), sparse)
    put_field(record, "enriched_photo_candidate_evidence", ";".join(
        json.dumps({k:x.get(k,"") for k in ("source","photo_id","date","status","distance_m","heading_difference_deg","license","source_page","local_image","visual_verified") if x.get(k)},ensure_ascii=False,separators=(",",":"))
        for x in all_photos), sparse)
    biz=businesses.get(ident,[]) if ident else []
    put_field(record, "enriched_business_names", ";".join(sorted({x["name"] for x in biz if x["name"]})), sparse)
    put_field(record, "enriched_business_brands", ";".join(sorted({x["brand"] for x in biz if x["brand"]})), sparse)
    put_field(record, "enriched_business_osm_ids", ";".join(sorted({x["store_id"] for x in biz if x["store_id"]})), sparse)
    put_field(record, "enriched_business_addresses", ";".join(sorted({", ".join(v for v in (x["house_number"],x["street"]) if v) for x in biz if x["street"] or x["house_number"]})), sparse)
    put_field(record, "enriched_business_match_status", ";".join(sorted({x["status"] for x in biz if x["status"]})), sparse)
    sig=signage.get(ident,[]) if ident else []
    put_field(record, "enriched_model_estimated_height_m", ";".join(sorted({x["height"] for x in sig if x["height"]})), sparse)
    put_field(record, "enriched_model_estimated_floor_count", ";".join(sorted({x["levels"] for x in sig if x["levels"]})), sparse)
    panels=sorted({x["panel"] for x in sig if x["panel"]})
    verified=sorted({x["verified"] for x in sig if x["verified"]})
    if sparse:
        panels=[v for v in panels if v.lower() in {"true","yes","1"}]
        verified=[v for v in verified if v.lower() in {"true","yes","1"}]
    put_field(record, "enriched_signage_panel_generated", ";".join(panels), sparse)
    put_field(record, "enriched_sign_text_verified", ";".join(verified), sparse)
    return conflicts, bool(values.get("enrichment_sources")), len(all_photos), len(biz)

def main():
    for p in [CSV_PATH, *PARTS]:
        if not p.is_file(): raise FileNotFoundError(p)
    index, source_rows, feature_id_map, photos, businesses, signage, image_candidates=load_sources()
    report={"schema_version":"2.0","status":"completed","policy":"Repository-first enrichment. Join on explicit OSM IDs or exact stable source-feature IDs only. Candidate imagery and tenants remain explicitly labelled; no visual observations are inferred. Geometry, coordinates, feature IDs, source IDs, and rendering heights are not changed.",
            "sources":dict(source_rows),"csv":{"path":str(CSV_PATH.relative_to(ROOT))},"geojson_parts":[],"filled_fields":Counter(),"conflicts":Counter(),"matched_records":Counter(),"photo_candidates":0,"business_links":0,"feature_id_crosswalks":len(feature_id_map)}
    rows=read_csv(CSV_PATH)
    original_fields=list(rows[0].keys()) if rows else []
    fields=original_fields+[f for f in OUT_FIELDS if f not in original_fields]
    for row in rows:
        ident=osm_id(row)
        conflicts, matched, photo_count, business_count=decorate_record(row,ident,normalize_id(row.get("source_feature_id")),index,photos,businesses,signage,image_candidates)
        report["matched_records"][row["enrichment_status"]]+=1
        if matched: report["matched_records"]["records_with_metadata"]+=1
        report["photo_candidates"]+=photo_count
        report["business_links"]+=business_count
        for field in OUT_FIELDS:
            if field.startswith("enriched_") and row.get(field): report["filled_fields"][field]+=1
        for k in conflicts: report["conflicts"][k]+=1
    with CSV_PATH.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    report["csv"].update({"rows":len(rows),"columns_before":len(original_fields),"columns_after":len(fields)})
    for part in PARTS:
        with part.open(encoding="utf-8") as f: doc=json.load(f)
        features=doc.get("features") or []
        part_counts=Counter(); part_conflicts=Counter(); part_filled=Counter()
        for feature in features:
            props=feature.setdefault("properties",{})
            fid=first_feature_id(props,feature)
            ident=osm_id(props)
            if not ident and fid in feature_id_map: ident=feature_id_map[fid]
            conflicts, matched, photo_count, business_count=decorate_record(props,ident,fid,index,photos,businesses,signage,image_candidates,sparse=True)
            part_counts[props["enrichment_status"]]+=1
            report["photo_candidates"]+=photo_count
            report["business_links"]+=business_count
            for field in OUT_FIELDS:
                if field.startswith("enriched_") and props.get(field): part_filled[field]+=1
            for k in conflicts: part_conflicts[k]+=1
        with part.open("w",encoding="utf-8") as f:
            json.dump(doc,f,ensure_ascii=False,separators=(",",":")); f.write("\n")
        report["geojson_parts"].append({"path":str(part.relative_to(ROOT)),"features":len(features),"status_counts":dict(part_counts),"filled_fields":dict(part_filled),"conflict_fields":dict(part_conflicts)})
    report["filled_fields"]=dict(report["filled_fields"]); report["conflicts"]=dict(report["conflicts"]); report["matched_records"]=dict(report["matched_records"])
    report["note"]="This pass imports internal exact-ID metadata, business tenant links explicitly marked inside_footprint, model-only estimates as separately labelled estimates, and photo candidates as unverified candidates. It does not infer facade material/colour from unreviewed photos and does not perform unvalidated spatial matching."
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"csv_rows":len(rows),"csv_columns_added":len([f for f in OUT_FIELDS if f not in original_fields]),"geojson_features":[x["features"] for x in report["geojson_parts"]],"filled_fields":report["filled_fields"],"conflicts":report["conflicts"],"photo_candidates":report["photo_candidates"],"business_links":report["business_links"],"report":str(REPORT.relative_to(ROOT))},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
