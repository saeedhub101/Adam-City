#!/usr/bin/env python3
"""Build a reusable 7-Eleven inventory from the saved Malate/Ermita map and POI cache."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MAP_PATH = Path("maps/malate-map.json")
PLACES_PATH = Path("maps/malate-places.json")
OUT_PATH = Path("maps/malate-7eleven-stores.json")
PATTERN = re.compile(r"7\s*[-‐‑–—]?\s*eleven|7eleven|7\s*[- ]?\s*11", re.I)

if not MAP_PATH.exists() or MAP_PATH.stat().st_size < 10:
    raise SystemExit("Saved map snapshot missing or too small; refusing to overwrite store inventory.")
try:
    map_data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    place_data = json.loads(PLACES_PATH.read_text(encoding="utf-8")) if PLACES_PATH.exists() else {"places": []}
except Exception as exc:
    raise SystemExit(f"Could not parse saved map/places JSON; refusing to overwrite store inventory: {exc}")
elements = map_data.get("elements")
if not isinstance(elements, list) or not elements:
    raise SystemExit("Saved map has no elements; refusing to publish an empty store inventory.")

def matches(tags):
    if not isinstance(tags, dict):
        return False
    brand_text = " ".join(str(tags.get(k, "")) for k in ("name", "name:en", "brand", "brand:en", "operator", "official_name"))
    return bool(PATTERN.search(brand_text))

found = {}
for el in elements:
    tags = el.get("tags", {})
    if not matches(tags):
        continue
    typ, oid = el.get("type"), el.get("id")
    if typ is None or oid is None:
        continue
    center = el.get("center")
    if not center and isinstance(el.get("lat"), (int, float)) and isinstance(el.get("lon"), (int, float)):
        center = {"lat": el["lat"], "lon": el["lon"]}
    if not center and el.get("geometry"):
        points = [p for p in el["geometry"] if isinstance(p, dict) and isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lon"), (int, float))]
        if points:
            center = {"lat": sum(p["lat"] for p in points) / len(points), "lon": sum(p["lon"] for p in points) / len(points)}
    found[(typ, oid)] = {
        "osm_type": typ, "osm_id": oid, "source": "malate-map.json",
        "name": tags.get("name") or tags.get("name:en") or tags.get("brand") or "7-Eleven",
        "kind": "building" if tags.get("building") or tags.get("building:part") else tags.get("shop") or tags.get("amenity") or "store",
        "is_building": bool(typ == "way" and (tags.get("building") or tags.get("building:part"))),
        "lat": round(center["lat"], 7) if center else None, "lon": round(center["lon"], 7) if center else None,
        "tags": {k: v for k, v in tags.items() if k in ("name", "name:en", "brand", "brand:en", "operator", "shop", "amenity", "building", "addr:housenumber", "addr:street", "addr:city", "website")}
    }
for p in place_data.get("places", []):
    if not matches(p.get("tags", {})) and not PATTERN.search(str(p.get("name", ""))):
        continue
    typ, oid = p.get("osm_type"), p.get("osm_id")
    if typ is None or oid is None:
        continue
    key = (typ, oid)
    if key not in found:
        found[key] = {
            "osm_type": typ, "osm_id": oid, "source": "malate-places.json",
            "name": p.get("name") or "7-Eleven", "kind": p.get("kind") or "store",
            "is_building": False, "lat": p.get("lat"), "lon": p.get("lon"),
            "tags": {k: v for k, v in (p.get("tags") or {}).items() if k in ("name", "name:en", "brand", "brand:en", "operator", "shop", "amenity", "building", "addr:housenumber", "addr:street", "addr:city", "website")}
        }
stores = sorted(found.values(), key=lambda x: (x["osm_type"], int(x["osm_id"])))
previous = {}
if OUT_PATH.exists():
    try:
        old = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        previous = {(x.get("osm_type"), x.get("osm_id")): x for x in old.get("stores", [])}
    except Exception as exc:
        raise SystemExit(f"Existing 7-Eleven inventory is invalid; refusing to overwrite it: {exc}")
# Preserve previously discovered locations if a later snapshot is incomplete.
by_key = dict(previous)
by_key.update({(x["osm_type"], x["osm_id"]): x for x in stores})
stores = sorted(by_key.values(), key=lambda x: (x["osm_type"], int(x["osm_id"])))
out = {
    "region": "Malate + Ermita, Manila, Philippines",
    "source": "Cumulative inventory matched from saved OpenStreetMap snapshot and POI cache; © OpenStreetMap contributors",
    "map_generated_utc": map_data.get("_cache", {}).get("generated_utc") or map_data.get("generated_utc"),
    "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "count": len(stores),
    "newly_discovered_this_run": len([x for x in stores if (x["osm_type"], x["osm_id"]) not in previous]),
    "building_osm_way_ids": sorted({x["osm_id"] for x in stores if x.get("is_building") and x["osm_type"] == "way"}),
    "stores": stores,
    "coverage_note": "Only mapped features explicitly tagged with a 7-Eleven-like name, brand, or operator are included. This is not a complete real-world branch list."
}
OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(OUT_PATH), "count": len(stores), "newly_discovered_this_run": out["newly_discovered_this_run"], "building_osm_way_ids": out["building_osm_way_ids"], "names": [x["name"] for x in stores]}, ensure_ascii=False, indent=2))
