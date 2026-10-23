#!/usr/bin/env python3
"""Precompute the Roxas Boulevard enhancement selection as static GeoJSON.

This moves all road buffering/intersection work out of the browser main thread.
The output preserves the source footprint coordinates and IDs.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings/Ermita/ermita-buildings-master.geojson"
ROADS = ROOT / "complete_data/OSM/data/roads/ermita-road-network.geojson"
OUT = ROOT / "complete_data/OSM/data/buildings/roxas-boulevard/roxas-boulevard-enhanced.geojson"
TO_M = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
FROM_M = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def load_buildings():
    doc = json.loads(BUILDINGS.read_text(encoding="utf-8"))
    features = doc.get("features") or []
    if features:
        return features
    parts = (doc.get("metadata") or {}).get("parts") or []
    result = []
    for item in parts:
        p = Path(item)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            # Some indexes store paths relative to the repository root without a leading slash.
            p = ROOT / str(item).lstrip("./")
        if p.exists():
            chunk = json.loads(p.read_text(encoding="utf-8"))
            result.extend(chunk.get("features") or [])
    if not result:
        for p in sorted(BUILDINGS.parent.glob("*.parts/part-*.geojson")):
            result.extend((json.loads(p.read_text(encoding="utf-8")).get("features") or []))
    return result

def num(value, low, high):
    m = re.search(r"-?\d+(?:\.\d+)?", str(value if value is not None else "").replace(",", "."))
    if not m: return None
    n = float(m.group())
    return n if low <= n <= high else None

def height(p):
    ident = str(p.get("osm_feature_id") or p.get("@id") or p.get("full_id") or "").lower()
    name = str(p.get("name") or p.get("official_name") or "").lower()
    overrides = {"way/575422161":168,"way/822386816":168,"way/575422162":230,
                 "way/90308376":203,"way/87754850":46,"way/314226123":34,"way/314226156":16}
    if ident in overrides: return overrides[ident]
    for term, value in (("grand riviera suites",230),("1322 golden empire",203),
                        ("bayview park hotel",46),("national library",34),("planetarium",16)):
        if term in name: return value
    h = num(p.get("height",p.get("building:height",p.get("render_height"))),2,500)
    lv = num(p.get("building:levels",p.get("levels")),1,150)
    if h is not None and lv is not None:
        if lv >= 8 and h < lv*2: return lv*3.2
        if lv <= 8 and h > lv*6: return lv*3.2
    return h if h is not None else (lv*3.2 if lv is not None else 9.6)

def color(p, i):
    ident = str(p.get("osm_feature_id") or p.get("@id") or p.get("full_id") or "").lower()
    name = str(p.get("name") or p.get("official_name") or p.get("brand") or "").lower()
    if ident in {"way/575422161","way/822386813","way/822386814","way/822386816"}: return "#476e8f"
    if ident in {"way/90308376","way/822386807","way/822386809","way/822386811"} or "golden empire" in name: return "#856b40"
    if ident=="way/575422162" or "grand riviera" in name: return "#9aaeb7"
    if ident=="way/575422164" or "eton baypark" in name: return "#b0aaa3"
    if ident=="way/136842220" or "luneta hotel" in name: return "#c7b77f"
    if ident=="way/87754850" or "bayview park" in name: return "#c2522b"
    if ident=="way/314226123" or "national library" in name: return "#c9cbc5"
    if ident=="way/314226156" or "planetarium" in name: return "#d4d4cd"
    if ident=="way/89770558" or "red planet" in name: return "#383e43"
    mat = str(p.get("building:material") or p.get("facade:material") or p.get("material") or "").lower()
    c = str(p.get("building:colour") or p.get("building:color") or p.get("colour") or p.get("color") or "").lower()
    if "glass" in mat or "glazing" in mat or "blue" in c: return "#5d7b87"
    if any(x in mat for x in ("stone","marble")) or any(x in c for x in ("white","ivory")): return "#c6bea8"
    if any(x in mat for x in ("concrete","plaster")) or any(x in c for x in ("grey","gray")): return "#9c9a91"
    if any(x in mat for x in ("brick","terracotta")) or any(x in c for x in ("red","brown")): return "#965d48"
    palette = ["#b8ad97","#c9c5b4","#92958e","#b09a7d","#8f5a48","#5d7b87"]
    seed = sum(ord(ch) for ch in (ident or name or str(i)))
    return palette[seed % len(palette)]

def main():
    roads_doc = json.loads(ROADS.read_text(encoding="utf-8"))
    lines = []
    for f in roads_doc.get("features") or []:
        p = f.get("properties") or {}
        n = " ".join(str(p.get(k) or "") for k in ("name","official_name","alt_name","name:en")).lower()
        norm = re.sub(r"[^a-z]", "", n)
        if ("roxasboulevard" in norm or "roxasblvd" in norm) and f.get("geometry",{}).get("type") in ("LineString","MultiLineString"):
            try: lines.append(transform(TO_M, shape(f["geometry"])))
            except Exception: pass
    if not lines:
        raise SystemExit("No road segments named Roxas Boulevard found; refusing to generate a misleading selection.")
    corridor = unary_union([line.buffer(70) for line in lines])
    selected, seen = [], set()
    for f in load_buildings():
        geom_data = f.get("geometry")
        if not geom_data or geom_data.get("type") not in ("Polygon","MultiPolygon"): continue
        try:
            geom_m = transform(TO_M, shape(geom_data))
            if not geom_m.intersects(corridor): continue
        except Exception:
            continue
        p = dict(f.get("properties") or {})
        identity = str(f.get("id") or p.get("osm_feature_id") or p.get("@id") or "")
        signature = identity or json.dumps(geom_data.get("coordinates"), separators=(",",":"))
        if signature in seen: continue
        seen.add(signature)
        p["height"] = height(p)
        p["render_color"] = color(p, len(selected))
        p["_enhanced_by"] = "Roxas Boulevard precomputed GeoJSON"
        selected.append({"type":"Feature", **({"id":f["id"]} if "id" in f else {}),
                         "geometry":geom_data, "properties":p})
    if not selected:
        raise SystemExit("No building footprints intersected the 70 m Roxas Boulevard corridor.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result = {"type":"FeatureCollection","name":"Roxas Boulevard enhanced buildings",
              "metadata":{"selection":"within 70 m of named Roxas Boulevard road geometry",
                          "feature_count":len(selected),"source_buildings":str(BUILDINGS.relative_to(ROOT)),
                          "source_roads":str(ROADS.relative_to(ROOT))},
              "features":selected}
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    print(f"Wrote {OUT}: {len(selected)} selected building features")

if __name__ == "__main__":
    main()
