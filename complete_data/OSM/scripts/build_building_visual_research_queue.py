#!/usr/bin/env python3
"""Create a coordinate-first visual review queue; does not change building geometry or matches."""
from __future__ import annotations
import csv, json
from pathlib import Path
from urllib.parse import quote
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[3]
PARTS = ROOT / "complete_data/OSM/data/buildings/parts"
INDEX = PARTS / "building-enrichment-index.json"
CSV_OUT = PARTS / "building-visual-research-queue.csv"
GEOJSON_OUT = PARTS / "building-visual-research-queue.geojson"
DOC_OUT = PARTS / "BUILDING-VISUAL-RESEARCH.md"
TO_WGS84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def main():
    enriched = load_json(INDEX)
    inventory = {}
    for part in range(1, 5):
        path = PARTS / f"part{part}" / f"part{part}-inventory.json"
        for feature in load_json(path).get("features", []):
            inventory[(part, feature.get("source_key"), feature.get("source_feature_index"))] = feature

    rows, geo_features = [], []
    for record in enriched.get("buildings", []):
        method = record.get("match_method")
        if method not in ("unmatched", "spatial_review"):
            continue
        key = (record.get("part"), record.get("source_key"), record.get("source_feature_index"))
        inv = inventory.get(key, {})
        centroid = inv.get("centroid_epsg3857_m") or {}
        if "x" not in centroid or "y" not in centroid:
            continue
        lon, lat = TO_WGS84(float(centroid["x"]), float(centroid["y"]))
        props = inv.get("source_properties") or {}
        tags = inv.get("source_tags") or props.get("tags") or {}
        name = record.get("name") or tags.get("name") or tags.get("brand") or ""
        query_terms = " ".join(str(v) for v in (name, "building", "Ermita", "Manila") if v)
        evidence = record.get("spatial_match_evidence") or {}
        osm_id = evidence.get("candidate_osm_id") or record.get("source_feature_id")
        osm_url = f"https://www.openstreetmap.org/{osm_id}" if isinstance(osm_id, str) and (osm_id.startswith("way/") or osm_id.startswith("relation/") or osm_id.startswith("node/")) else ""
        row = {
            "part": record.get("part"), "source_key": record.get("source_key"),
            "source_feature_index": record.get("source_feature_index"),
            "source_feature_id": record.get("source_feature_id"), "status": method,
            "candidate_osm_id_for_review_only": evidence.get("candidate_osm_id", ""),
            "candidate_name_for_review_only": evidence.get("candidate_name", ""),
            "latitude": round(lat, 7), "longitude": round(lon, 7),
            "area_m2": inv.get("area_m2", ""),
            "height_m": inv.get("height_m", inv.get("height", "")),
            "base_height_m": inv.get("base_height_m", inv.get("min_height", "")),
            "source_name_or_brand": name, "source_building_type": tags.get("building", ""),
            "source_colour": tags.get("building:colour", tags.get("colour", "")),
            "source_material": tags.get("building:material", tags.get("material", "")),
            "google_maps": f"https://www.google.com/maps/search/?api=1&query={lat:.7f}%2C{lon:.7f}",
            "mapillary": f"https://www.mapillary.com/app/?lat={lat:.7f}&lng={lon:.7f}&z=18",
            "wikimedia_commons_search": "https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=" + quote(query_terms),
            "openstreetmap_candidate": osm_url, "review_decision": "", "review_notes": "",
        }
        rows.append(row)
        geo_features.append({"type":"Feature","properties":{k:v for k,v in row.items() if k not in ("latitude","longitude")},"geometry":{"type":"Point","coordinates":[round(lon,7),round(lat,7)]}})

    fields = list(rows[0].keys()) if rows else ["part","source_key","source_feature_index","source_feature_id","status","candidate_osm_id_for_review_only","candidate_name_for_review_only","latitude","longitude","area_m2","height_m","base_height_m","source_name_or_brand","source_building_type","source_colour","source_material","google_maps","mapillary","wikimedia_commons_search","openstreetmap_candidate","review_decision","review_notes"]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    GEOJSON_OUT.write_text(json.dumps({"type":"FeatureCollection","name":"Unmatched and ambiguous building visual research queue","description":"Coordinates are research entry points only. Candidate OSM IDs are unconfirmed and must not be treated as matched identities.","features":geo_features},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    counts = {"queued_total":len(rows),"unmatched":sum(r["status"]=="unmatched" for r in rows),"spatial_review":sum(r["status"]=="spatial_review" for r in rows),"with_candidate_for_review":sum(bool(r["candidate_osm_id_for_review_only"]) for r in rows)}
    DOC_OUT.write_text("# Building visual research queue\n\nThis queue includes each exported building-part record that has no accepted OSM link or has an ambiguous spatial candidate. It provides coordinate-specific Google Maps and Mapillary entry points plus a Wikimedia Commons image search. These links are research shortcuts, not proof that a photo depicts the exact building.\n\n## Counts\n\n"+"".join(f"- **{key.replace('_',' ')}:** {value}\n" for key,value in counts.items())+"\n## Review rules\n\n- Inspect coordinate-specific imagery before recording an identity or façade attributes.\n- Confirm a Commons image depicts the same building and check its license/attribution.\n- Candidate OSM IDs and names are unconfirmed hints, not accepted links.\n- Fill review_decision and review_notes only after visual/source verification. Do not infer exact colors, materials, windows, signs, or addresses from coordinates alone.\n- This workflow does not alter GLBs, geometry, positions, IDs, heights, or existing colors; it does not claim imagery has already been verified.\n",encoding="utf-8")
    print(json.dumps(counts,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
