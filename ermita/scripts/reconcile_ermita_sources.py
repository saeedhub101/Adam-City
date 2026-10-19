#!/usr/bin/env python3
"""Reconcile existing Ermita datasets without deleting or overwriting source files.

Stable OSM IDs are the primary identity key. Cross-provider spatial matches are
reported as candidates, never silently merged into a false single identity.
"""
from __future__ import annotations
import csv, gzip, json, math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "ermita/maps/generated"
EXT = ROOT / "ermita/maps/external"
OFM = ROOT / "ermita/maps/sources/openfreemap"
QA = ROOT / "ermita/maps/qa"
QA.mkdir(parents=True, exist_ok=True)

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def read_jsonl(path):
    if not path.exists():
        return []
    out=[]
    with path.open(encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if not line.strip(): continue
            try: out.append(json.loads(line))
            except json.JSONDecodeError: continue
    return out

def osm_id(feature):
    p=feature.get("properties") or {}
    raw=p.get("osm_feature_id") or p.get("osm_id") or p.get("id")
    if raw is None and isinstance(p.get("tags"),dict):
        raw=p["tags"].get("osm_id")
    if raw is None: return None
    s=str(raw).strip()
    if s.isdigit():
        typ=p.get("type") or p.get("osm_type")
        return f"{typ}/{s}" if typ else s
    return s

def tags_of(feature):
    p=feature.get("properties") or {}
    tags=p.get("tags")
    return tags if isinstance(tags,dict) else p

def feature_key(feature, source, index):
    sid=osm_id(feature)
    if sid: return sid
    p=feature.get("properties") or {}
    fid=feature.get("id") or p.get("id") or p.get("OBJECTID") or p.get("objectid")
    return f"{source}:{fid}" if fid is not None else f"{source}:row-{index}"

def load_feature_collection(path):
    data=read_json(path)
    return data.get("features",[]) if isinstance(data,dict) else []

def load_raw_osm():
    data=read_json(GEN/"ermita-osm-raw.json")
    features=[]
    for e in (data or {}).get("elements",[]):
        t=e.get("tags") or {}
        typ=e.get("type")
        eid=e.get("id")
        geom=None
        if typ=="node" and e.get("lon") is not None and e.get("lat") is not None:
            geom={"type":"Point","coordinates":[e["lon"],e["lat"]]}
        elif e.get("geometry"):
            coords=[[n["lon"],n["lat"]] for n in e["geometry"] if "lon" in n and "lat" in n]
            if len(coords)>=2:
                closed=coords[0]==coords[-1]
                if typ=="way" and closed and len(coords)>=4:
                    geom={"type":"Polygon","coordinates":[coords]}
                else: geom={"type":"LineString","coordinates":coords}
        elif e.get("center"):
            geom={"type":"Point","coordinates":[e["center"]["lon"],e["center"]["lat"]]}
        features.append({"type":"Feature","id":f"{typ}/{eid}","geometry":geom,
                         "properties":{"osm_feature_id":f"{typ}/{eid}","type":typ,"id":eid,"tags":t,
                                       "_source":{"provider":"OpenStreetMap","file":"ermita-osm-raw.json"}}})
    return features

def summarize_dataset(name, features):
    counts=Counter()
    for f in features:
        p=f.get("properties") or {}
        t=tags_of(f)
        g=f.get("geometry") or {}
        counts["features"]+=1
        counts["geometry_"+str(g.get("type","missing"))]+=1
        if t.get("building") or t.get("building:part"): counts["building_or_part"]+=1
        if t.get("highway"): counts["highway"]+=1
        if t.get("name"): counts["named"]+=1
    return {"dataset":name,**dict(counts)}

def main():
    source_specs=[
      ("osm_building_footprints",GEN/"ermita-building-footprints.geojson","collection"),
      ("osm_road_network",GEN/"ermita-road-network.geojson","collection"),
      ("openfreemap_buildings",OFM/"layers/building.geojsonl","jsonl"),
      ("openfreemap_roads",OFM/"layers/transportation.geojsonl","jsonl"),
      ("dpwh_national_roads",EXT/"dpwh-national-roads-ermita.geojson","collection"),
      ("dpwh_road_surfaces",EXT/"dpwh-road-surface-type-ermita.geojson","collection"),
      ("microsoft_road_detections",EXT/"ermita-microsoft-road-detections.geojson","collection"),
    ]
    datasets={}
    dataset_summaries=[]
    for name,path,kind in source_specs:
        feats=read_jsonl(path) if kind=="jsonl" else load_feature_collection(path)
        datasets[name]=feats
        dataset_summaries.append(summarize_dataset(name,feats))
    raw_osm=load_raw_osm()
    datasets["osm_raw_elements"]=raw_osm
    dataset_summaries.append(summarize_dataset("osm_raw_elements",raw_osm))

    # Build the canonical feature register from all existing sources. Records with
    # stable OSM IDs share one entity; every source observation and all tag variants
    # are retained. Features without stable IDs stay source-specific.
    entities={}
    source_id_counts=Counter()
    duplicate_observations=0
    for source,features in datasets.items():
        for i,f in enumerate(features):
            p=f.get("properties") or {}
            sid=osm_id(f)
            # OpenMapTiles feature IDs can be tile-local; only merge these with OSM
            # when an explicit stable OSM ID field is present.
            if source.startswith("openfreemap"):
                p0=f.get("properties") or {}
                t0=p0.get("tags") if isinstance(p0.get("tags"),dict) else {}
                stable=p0.get("osm_feature_id") or p0.get("osm_id") or t0.get("osm_id")
                sid=str(stable) if stable is not None else None
                if sid and sid.isdigit():
                    sid="way/"+sid
            # Avoid accidental collision of provider-local numeric IDs with OSM IDs.
            if sid and "/" not in sid and source not in ("osm_building_footprints","osm_road_network","osm_raw_elements"):
                sid=None
            key=sid if sid else feature_key(f,source,i)
            entity=entities.setdefault(key,{"entity_id":key,"osm_id":sid,"geometry_candidates":[],"observations":[],"sources":[]})
            entity["observations"].append({"source":source,"feature_id":f.get("id") or p.get("id"),
                "geometry_type":(f.get("geometry") or {}).get("type"),
                "properties":p,"geometry":f.get("geometry")})
            if source not in entity["sources"]: entity["sources"].append(source)
            if f.get("geometry"):
                entity["geometry_candidates"].append({"source":source,"geometry":f["geometry"]})
            source_id_counts[source]+=1
            if len(entity["observations"])>1: duplicate_observations+=1

    # A compact entity index plus complete source observations. No geometry or tags
    # are discarded; source geometry differences are explicitly flagged for QA.
    canonical=[]
    source_conflicts=[]
    for key,e in sorted(entities.items()):
        geom_types=Counter(g["geometry"].get("type","missing") for g in e["geometry_candidates"])
        tag_values=defaultdict(set)
        names=set()
        for obs in e["observations"]:
            p=obs["properties"] or {}
            t=p.get("tags") if isinstance(p.get("tags"),dict) else p
            for k,v in t.items():
                if v not in (None,"",[],{}):
                    try: tag_values[k].add(json.dumps(v,sort_keys=True,ensure_ascii=False))
                    except TypeError: tag_values[k].add(str(v))
            if t.get("name"): names.add(str(t["name"]))
        conflicts={k:sorted(v) for k,v in tag_values.items() if len(v)>1}
        row={"type":"Feature","id":key,"geometry":None,
             "properties":{"entity_id":key,"osm_id":e["osm_id"],"sources":e["sources"],
             "observation_count":len(e["observations"]),"geometry_candidate_count":len(e["geometry_candidates"]),
             "geometry_types":dict(geom_types),"names":sorted(names),
             "source_tag_conflicts":conflicts,"observations":e["observations"]}}
        # The canonical file deliberately has no single chosen geometry if sources
        # disagree; all candidate geometries are kept per observation.
        canonical.append(row)
        if conflicts or len(geom_types)>1 or len(e["geometry_candidates"])>1:
            source_conflicts.append({"entity_id":key,"osm_id":e["osm_id"],"sources":e["sources"],
                "observation_count":len(e["observations"]),"geometry_types":dict(geom_types),
                "names":sorted(names),"conflicting_tags":conflicts})

    # Deduplicate repeated OSM IDs within the building footprint layer without
    # changing the original source file; flag them for a safe, separately generated view.
    footprint_seen={}
    footprint_dupes=[]
    footprints=datasets["osm_building_footprints"]
    for i,f in enumerate(footprints):
        sid=osm_id(f) or f"footprint-row-{i}"
        if sid in footprint_seen:
            footprint_dupes.append({"osm_id":sid,"first_index":footprint_seen[sid],"duplicate_index":i,
                                    "name":tags_of(f).get("name","")})
        else: footprint_seen[sid]=i
    unique_footprints=[]
    seen=set()
    for i,f in enumerate(footprints):
        sid=osm_id(f) or f"footprint-row-{i}"
        if sid in seen: continue
        seen.add(sid); unique_footprints.append(f)
    (QA/"ermita-canonical-source-register.geojson").write_text(
        json.dumps({"type":"FeatureCollection","features":canonical},ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (QA/"ermita-osm-building-footprints-deduplicated.geojson").write_text(
        json.dumps({"type":"FeatureCollection","features":unique_footprints},ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (QA/"ermita-source-conflicts.json").write_text(json.dumps(source_conflicts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (QA/"ermita-source-inventory.csv").open("w",encoding="utf-8",newline="") as out:
        fields=["dataset","features","geometry_Point","geometry_LineString","geometry_MultiLineString","geometry_Polygon","geometry_MultiPolygon","building_or_part","highway","named"]
        w=csv.DictWriter(out,fieldnames=fields);w.writeheader()
        for row in dataset_summaries: w.writerow({k:row.get(k,0) for k in fields})
    report={"status":"success","area":"Ermita, Manila, Philippines","method":"stable OSM IDs first; non-OSM features remain source-specific; all observations and geometry candidates retained",
      "source_inventory":dataset_summaries,"canonical_entity_count":len(entities),
      "observations_total":sum(len(v) for v in datasets.values()),"entities_with_multiple_observations":sum(1 for e in entities.values() if len(e["observations"])>1),
      "duplicate_observation_count":duplicate_observations,"footprint_feature_count":len(footprints),
      "unique_footprint_id_count":len(unique_footprints),"duplicate_footprint_ids":len(footprint_dupes),
      "source_conflict_entity_count":len(source_conflicts),
      "outputs":{"canonical_register":"ermita/maps/qa/ermita-canonical-source-register.geojson","deduplicated_footprints":"ermita/maps/qa/ermita-osm-building-footprints-deduplicated.geojson","source_conflicts":"ermita/maps/qa/ermita-source-conflicts.json","source_inventory":"ermita/maps/qa/ermita-source-inventory.csv"},
      "policy":"Source datasets remain unchanged. No conflicting tag, name, height, or geometry is silently discarded. Spatial-only matches are not merged without an identity key."}
    (QA/"ermita-source-reconciliation-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
