#!/usr/bin/env python3
"""Audit saved Malate/Ermita building tags without changing the map snapshot."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MAP_PATH = Path("maps/malate-map.json")
OUT_PATH = Path("maps/malate-building-audit.json")

if not MAP_PATH.exists() or MAP_PATH.stat().st_size < 10:
    raise SystemExit("Saved map snapshot is missing or unexpectedly small; refusing to publish an audit.")
try:
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"Saved map JSON could not be parsed; refusing to publish an audit: {exc}")
elements = data.get("elements")
if not isinstance(elements, list) or not elements:
    raise SystemExit("Saved map has no elements; refusing to publish an empty audit.")

ways = [e for e in elements if e.get("type") == "way" and isinstance(e.get("tags"), dict)]
buildings = [e for e in ways if e["tags"].get("building")]
parts = [e for e in ways if e["tags"].get("building:part")]
all_building_features = [e for e in ways if e["tags"].get("building") or e["tags"].get("building:part")]
if not buildings:
    raise SystemExit("No building ways found; refusing to publish an empty building audit.")

def present(el, *keys):
    tags = el.get("tags", {})
    return any(str(tags.get(k, "")).strip() for k in keys)

tag_groups = {
    "height": ("height",),
    "levels": ("building:levels", "levels"),
    "name": ("name", "name:en", "official_name"),
    "roof_shape": ("roof:shape",),
    "facade": ("building:facade:material", "facade:material", "building:material", "material"),
    "facade_colour": ("building:facade:colour", "building:colour", "colour"),
    "roof_colour": ("roof:colour", "building:roof:colour"),
    "roof_material": ("roof:material", "building:roof:material"),
    "architecture": ("building:architecture",),
    "building_colour": ("building:colour", "building:colour:colour", "colour"),
    "address": ("addr:housenumber", "addr:street"),
    "building_use": ("building:use", "building:function", "shop", "amenity", "office", "tourism"),
}
coverage = {}
for label, keys in tag_groups.items():
    count = sum(present(e, *keys) for e in buildings)
    coverage[label] = {
        "count": count,
        "percent": round(100 * count / len(buildings), 2),
        "keys_checked": list(keys),
    }

types = Counter(str(e["tags"].get("building", "unspecified")) for e in buildings)
def in_renderer_bounds(el):
    geometry = el.get("geometry")
    if not isinstance(geometry, list) or len(geometry) < 4:
        return False
    for point in geometry:
        if not isinstance(point, dict) or "lat" not in point or "lon" not in point:
            return False
        x = (float(point["lon"]) - 120.9851) * 107200
        z = -(float(point["lat"]) - 14.5767) * 111100
        if abs(x) > 3500 or abs(z) > 3500:
            return False
    return True

rendered_buildings = [e for e in buildings if in_renderer_bounds(e)]
rendered_parts = [e for e in parts if in_renderer_bounds(e)]
named_buildings = [
    {"osm_way_id": e.get("id"), "name": e["tags"].get("name") or e["tags"].get("name:en"),
     "building": e["tags"].get("building"),
     "height": e["tags"].get("height"),
     "levels": e["tags"].get("building:levels") or e["tags"].get("levels")}
    for e in buildings if present(e, "name", "name:en")
]
# Persist the exact source features behind the facade-material coverage count.
# This is derived only from the checked-in map snapshot, so later workflows can
# reuse the saved output instead of requiring a fresh OSM import.
material_keys = ("building:facade:material", "facade:material", "building:material", "material")
facade_material_buildings = []
for e in buildings:
    tags = e.get("tags", {})
    material_tags = {key: str(tags[key]) for key in material_keys
                     if str(tags.get(key, "")).strip()}
    if not material_tags:
        continue
    geometry = e.get("geometry") or []
    valid_points = [p for p in geometry if isinstance(p, dict) and "lat" in p and "lon" in p]
    center = None
    if valid_points:
        center = {
            "lat": round(sum(float(p["lat"]) for p in valid_points) / len(valid_points), 7),
            "lon": round(sum(float(p["lon"]) for p in valid_points) / len(valid_points), 7),
        }
    facade_material_buildings.append({
        "osm_way_id": e.get("id"),
        "name": tags.get("name") or tags.get("name:en") or tags.get("official_name"),
        "building": tags.get("building"),
        "material_tags": material_tags,
        "center": center,
        "osm_url": f"https://www.openstreetmap.org/way/{e.get('id')}" if e.get("id") else None,
    })

MATERIALS_PATH = Path("maps/malate-facade-materials.json")
materials_data = {
    "region": data.get("region") or "Malate + Ermita, Manila, Philippines",
    "source": "Derived from the checked-in maps/malate-map.json snapshot; © OpenStreetMap contributors",
    "map_generated_utc": data.get("_cache", {}).get("generated_utc") or data.get("generated_utc"),
    "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "count": len(facade_material_buildings),
    "tag_keys_checked": list(material_keys),
    "buildings": facade_material_buildings,
}
MATERIALS_PATH.write_text(json.dumps(materials_data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")

report = {
    "region": data.get("region") or "Malate + Ermita, Manila, Philippines",
    "source": "© OpenStreetMap contributors; audit computed from the checked-in map snapshot",
    "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "map_generated_utc": data.get("_cache", {}).get("generated_utc") or data.get("generated_utc"),
    "counts": {
        "map_elements": len(elements),
        "ways_with_geometry": sum(bool(e.get("geometry")) for e in ways),
        "building_ways": len(buildings),
        "building_part_ways": len(parts),
        "building_features_including_parts": len(all_building_features),
        "building_ways_with_geometry": sum(bool(e.get("geometry")) for e in buildings),
        "building_ways_within_renderer_bounds": len(rendered_buildings),
        "building_parts_within_renderer_bounds": len(rendered_parts),
        "building_features_within_renderer_bounds": len(rendered_buildings) + len(rendered_parts),
    },
    "coverage": coverage,
    "facade_material_buildings_file": str(MATERIALS_PATH),
    "facade_material_buildings_count": len(facade_material_buildings),
    "facade_material_buildings": facade_material_buildings,
    "renderer_bounds_coverage": {
        label: {
            "count": sum(present(e, *keys) for e in rendered_buildings),
            "percent": round(100 * sum(present(e, *keys) for e in rendered_buildings) / len(rendered_buildings), 2) if rendered_buildings else 0,
            "keys_checked": list(keys),
        }
        for label, keys in tag_groups.items()
    },
    "building_type_counts": dict(sorted(types.items(), key=lambda item: (-item[1], item[0]))),
    "named_buildings_sample": named_buildings[:250],
    "named_buildings_total": len(named_buildings),
    "interpretation": "Missing tags are not proof that a building has no such feature. Use the counts to prioritize verified building-by-building research; do not infer exact facades from footprints alone.",
}
OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(OUT_PATH), "materials_output": str(MATERIALS_PATH), "facade_material_buildings_count": len(facade_material_buildings), "counts": report["counts"], "coverage": coverage}, indent=2))
