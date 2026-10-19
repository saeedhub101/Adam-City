#!/usr/bin/env python3
"""Reconcile independent Google and Microsoft satellite building detections.

The source GeoJSON files are never edited or merged destructively. This script
creates a crosswalk of likely same-building matches and leaves disagreements
visible for review. It never queries OpenStreetMap.
"""
from __future__ import annotations
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
GOOGLE = ROOT / "ermita/maps/sources/google-open-buildings/google-open-buildings-v3-ermita.geojson"
MICROSOFT = ROOT / "ermita/maps/sources/microsoft-satellite-buildings/microsoft-philippines-satellite-footprints-ermita.geojson"
QA = ROOT / "ermita/maps/qa"
QA.mkdir(parents=True, exist_ok=True)
OUT = QA / "non-osm-building-footprint-crosswalk.csv"
REPORT = QA / "non-osm-building-footprint-reconciliation-report.json"
IOU_MIN = 0.25
CENTROID_MAX_M = 18.0

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def load_features(path, source):
    collection=json.loads(path.read_text(encoding="utf-8"))
    out=[]
    for i,f in enumerate(collection.get("features",[])):
        try:
            g=shape(f["geometry"])
            if g.is_empty:
                continue
            p=f.get("properties") or {}
            out.append({"id":str(f.get("id") or p.get("source_feature_id") or f"{source}-{i+1}"),
                        "geometry":g,"properties":p,"area":float(g.area)})
        except Exception:
            continue
    return out

def main():
    if OUT.exists() and REPORT.exists():
        print(json.dumps({"status":"reused_existing_not_overwritten",
                          "crosswalk":str(OUT.relative_to(ROOT)),
                          "report":str(REPORT.relative_to(ROOT))},indent=2))
        return
    report={
        "status":"waiting_for_source",
        "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
        "policy":"Google and Microsoft source records remain unchanged; only identity crosswalk is produced; no OSM queries.",
        "sources":{"google":{"path":str(GOOGLE.relative_to(ROOT)),"exists":GOOGLE.exists()},
                   "microsoft":{"path":str(MICROSOFT.relative_to(ROOT)),"exists":MICROSOFT.exists()}},
        "matching":{"method":"spatial intersection-over-union plus centroid distance",
                    "minimum_iou":IOU_MIN,"maximum_centroid_distance_m":CENTROID_MAX_M},
        "counts":{},"warnings":[]
    }
    if not GOOGLE.exists() or not MICROSOFT.exists():
        report["warnings"].append("Waiting until both independent satellite-derived footprint datasets are committed.")
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return

    if not OUT.exists():
        google=load_features(GOOGLE,"google")
        microsoft=load_features(MICROSOFT,"microsoft")
        # Use a local projected CRS for distance/area measurements in central Manila.
        from pyproj import Transformer
        from shapely.ops import transform
        project=Transformer.from_crs("EPSG:4326","EPSG:32651",always_xy=True).transform
        for f in google+microsoft:
            f["metric"]=transform(project,f["geometry"])
            f["metric_area"]=f["metric"].area
        from shapely.strtree import STRtree
        m_geoms=[f["metric"] for f in microsoft]
        tree=STRtree(m_geoms)
        candidate_pairs=[]
        for gi,g in enumerate(google):
            try:
                candidates=tree.query(g["metric"])
            except Exception:
                candidates=[]
            for item in candidates:
                mi=int(item) if isinstance(item,(int,)) else next((i for i,x in enumerate(m_geoms) if x is item),-1)
                if mi<0 or mi>=len(microsoft):
                    continue
                m=microsoft[mi]
                try:
                    inter=g["metric"].intersection(m["metric"]).area
                    if inter<=0:
                        continue
                    union=g["metric"].union(m["metric"]).area
                    iou=inter/union if union else 0
                    dist=g["metric"].centroid.distance(m["metric"].centroid)
                    overlap_g=inter/g["metric_area"] if g["metric_area"] else 0
                    overlap_m=inter/m["metric_area"] if m["metric_area"] else 0
                    if iou>=IOU_MIN and dist<=CENTROID_MAX_M:
                        candidate_pairs.append((iou,inter,dist,gi,mi,overlap_g,overlap_m))
                except Exception:
                    continue
        candidate_pairs.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True)
        used_g=set();used_m=set();matches={}
        for iou,inter,dist,gi,mi,overlap_g,overlap_m in candidate_pairs:
            if gi in used_g or mi in used_m:
                continue
            used_g.add(gi);used_m.add(mi)
            matches[gi]=(mi,iou,inter,dist,overlap_g,overlap_m)
        fields=["match_status","google_feature_id","google_confidence","google_area_m2",
                "microsoft_feature_id","microsoft_area_m2","intersection_over_union",
                "overlap_fraction_google","overlap_fraction_microsoft","centroid_distance_m",
                "geometry_policy","google_source_path","microsoft_source_path"]
        with OUT.open("w",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader()
            for gi,g in enumerate(google):
                if gi in matches:
                    mi,iou,inter,dist,og,om=matches[gi]
                    m=microsoft[mi]
                    writer.writerow({"match_status":"matched_probable_same_building",
                        "google_feature_id":g["id"],"google_confidence":g["properties"].get("confidence",""),
                        "google_area_m2":round(g["metric_area"],2),"microsoft_feature_id":m["id"],
                        "microsoft_area_m2":round(m["metric_area"],2),"intersection_over_union":round(iou,4),
                        "overlap_fraction_google":round(og,4),"overlap_fraction_microsoft":round(om,4),
                        "centroid_distance_m":round(dist,2),"geometry_policy":"Both source geometries preserved; no source overwrites the other.",
                        "google_source_path":str(GOOGLE.relative_to(ROOT)),"microsoft_source_path":str(MICROSOFT.relative_to(ROOT))})
                else:
                    writer.writerow({"match_status":"google_only_or_geometry_conflict","google_feature_id":g["id"],
                        "google_confidence":g["properties"].get("confidence",""),"google_area_m2":round(g["metric_area"],2),
                        "geometry_policy":"Review needed; original geometry preserved.",
                        "google_source_path":str(GOOGLE.relative_to(ROOT)),"microsoft_source_path":str(MICROSOFT.relative_to(ROOT))})
            for mi,m in enumerate(microsoft):
                if mi not in used_m:
                    writer.writerow({"match_status":"microsoft_only_or_geometry_conflict",
                        "microsoft_feature_id":m["id"],"microsoft_area_m2":round(m["metric_area"],2),
                        "geometry_policy":"Review needed; original geometry preserved.",
                        "google_source_path":str(GOOGLE.relative_to(ROOT)),"microsoft_source_path":str(MICROSOFT.relative_to(ROOT))})
        report["status"]="success"
        report["inputs_sha256"]={"google":digest(GOOGLE),"microsoft":digest(MICROSOFT)}
        report["counts"]={"google_features":len(google),"microsoft_features":len(microsoft),
                          "probable_matches":len(matches),"google_only_or_conflict":len(google)-len(matches),
                          "microsoft_only_or_conflict":len(microsoft)-len(used_m),
                          "candidate_pairs_passing_threshold":len(candidate_pairs)}
        report["crosswalk_file"]=str(OUT.relative_to(ROOT))
        report["crosswalk_bytes"]=OUT.stat().st_size
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
