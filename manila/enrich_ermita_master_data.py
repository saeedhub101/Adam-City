#!/usr/bin/env python3
"""Conservative exact-ID metadata enrichment for the Ermita master CSV/GeoJSON."""
from __future__ import annotations
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "manila/manila"
CSV_PATH = MASTER / "ermita-buildings-master.csv"
PARTS = [MASTER / "ermita-buildings-master.parts/part-001.geojson",
         MASTER / "ermita-buildings-master.parts/part-002.geojson"]
OSM = ROOT / "complete_data/OSM/data/buildings/Ermita/osm-building-details.csv"
HEIGHTS = ROOT / "complete_data/OSM/quality/building-height-evidence.csv"
AUDIT = ROOT / "ermita/3d/building-match-audit.csv"
REPORT = MASTER / "ermita-master-enrichment-report.json"

TARGETS = {
    "name": ("name", "official_name", "building_name"),
    "official_name": ("official_name",),
    "building_type": ("building", "building:part"),
    "height_m": ("height", "building:height", "height_tag_m", "height_m"),
    "levels": ("building:levels", "levels", "building_levels_tag"),
    "roof_shape": ("roof:shape", "roof_shape_tag"),
    "house_number": ("addr:housenumber", "address_housenumber"),
    "street": ("addr:street", "address_street"),
    "postcode": ("addr:postcode", "address_postcode"),
    "city": ("addr:city", "address_city"),
    "material": ("building:material", "facade:material", "material"),
    "facade_colour": ("building:colour", "building:color", "facade:colour", "facade_colour"),
    "roof_material": ("roof:material", "roof_material"),
    "roof_colour": ("roof:colour", "roof:color", "roof_colour"),
}
OUT_FIELDS = [f"enriched_{k}" for k in TARGETS] + ["enrichment_sources", "enrichment_status"]

def s(v):
    return "" if v is None else str(v).strip()

def osm_id(row):
    for k in ("osm_feature_id", "linked_osm_feature_id", "building_osm_id",
              "source_feature_id", "source_id", "source_element_id"):
        v = s(row.get(k))
        if re.fullmatch(r"(?:node|way|relation)/\d+", v):
            return v
    return ""

def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def norm_value(v):
    v=s(v)
    if not v or v.lower() in {"none","null","unknown","n/a","nan"}: return ""
    return v

def add_candidate(index, ident, source, fields):
    if not ident: return
    for target, aliases in TARGETS.items():
        vals=[]
        for alias in aliases:
            val=norm_value(fields.get(alias))
            if val and val not in vals: vals.append(val)
        if len(vals)==1:
            index[ident][target].append((vals[0], source))

def load_sources():
    idx=defaultdict(lambda: defaultdict(list))
    source_rows=Counter()
    for row in read_csv(OSM):
        ident=s(row.get("osm_feature_id"))
        try: tags=json.loads(row.get("tags_json") or "{}")
        except Exception: tags={}
        fields={**tags, "name":tags.get("name") or row.get("name")}
        add_candidate(idx, ident, "osm-building-details.csv", fields)
        source_rows["osm-building-details.csv"]+=1
    for row in read_csv(HEIGHTS):
        add_candidate(idx, s(row.get("source_id")), "building-height-evidence.csv", row)
        source_rows["building-height-evidence.csv"]+=1
    for row in read_csv(AUDIT):
        add_candidate(idx, s(row.get("osm_feature_id")), "building-match-audit.csv", row)
        source_rows["building-match-audit.csv"]+=1
    return idx, source_rows

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
    result["enrichment_status"]="conflict_review" if conflicts else ("exact_osm_id_enriched" if used else "no_exact_id_evidence")
    return result, conflicts

def main():
    for p in [CSV_PATH, *PARTS, OSM, HEIGHTS, AUDIT]:
        if not p.is_file(): raise FileNotFoundError(p)
    index, source_rows=load_sources()
    report={"schema_version":"1.0","status":"completed","policy":"Exact OSM ID only; add enriched_* fields without overwriting source columns. Conflicting source values remain unfilled and are recorded. Geometry, coordinates, feature IDs, render heights, source IDs, images and textures are not changed.",
            "sources":dict(source_rows),"csv":{"path":str(CSV_PATH.relative_to(ROOT))},"geojson_parts":[],"filled_fields":Counter(),"conflicts":Counter(),"matched_records":Counter()}
    rows=read_csv(CSV_PATH)
    original_fields=list(rows[0].keys()) if rows else []
    fields=original_fields+[f for f in OUT_FIELDS if f not in original_fields]
    for row in rows:
        ident=osm_id(row)
        values, conflicts=resolve(index, ident) if ident else ({}, {})
        for field in OUT_FIELDS: row[field]=values.get(field,"")
        report["matched_records"][row["enrichment_status"]]+=1
        for k,v in values.items():
            if k.startswith("enriched_") and v: report["filled_fields"][k]+=1
        for k in conflicts: report["conflicts"][k]+=1
    with CSV_PATH.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    report["csv"].update({"rows":len(rows),"columns_before":len(original_fields),"columns_after":len(fields)})
    for part in PARTS:
        with part.open(encoding="utf-8") as f: doc=json.load(f)
        features=doc.get("features") or []
        part_counts=Counter(); part_conflicts=Counter()
        for feature in features:
            props=feature.setdefault("properties",{})
            ident=s(props.get("osm_feature_id"))
            if not ident:
                kind=s(props.get("osm_type") or props.get("type"))
                raw=s(props.get("osm_id") or feature.get("id"))
                if kind in {"node","way","relation"} and raw and not raw.startswith(kind+"/"): ident=f"{kind}/{raw}"
                elif raw.startswith(("node/","way/","relation/")): ident=raw
            values, conflicts=resolve(index, ident) if ident else ({}, {})
            for field in OUT_FIELDS: props[field]=values.get(field,"")
            part_counts[props["enrichment_status"]]+=1
            for k in conflicts: part_conflicts[k]+=1
        with part.open("w",encoding="utf-8") as f:
            json.dump(doc,f,ensure_ascii=False,separators=(",",":")); f.write("\n")
        report["geojson_parts"].append({"path":str(part.relative_to(ROOT)),"features":len(features),"status_counts":dict(part_counts),"conflict_fields":dict(part_conflicts)})
    report["filled_fields"]=dict(report["filled_fields"]); report["conflicts"]=dict(report["conflicts"]); report["matched_records"]=dict(report["matched_records"])
    report["note"]="Exact-ID pass only. No external search, spatial-only matching, photo verification, or inferred architectural measurements were applied."
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"csv_rows":len(rows),"csv_columns_added":len([f for f in OUT_FIELDS if f not in original_fields]),"geojson_features":[x["features"] for x in report["geojson_parts"]],"filled_fields":report["filled_fields"],"conflicts":report["conflicts"],"report":str(REPORT.relative_to(ROOT))},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
