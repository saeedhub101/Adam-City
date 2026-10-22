#!/usr/bin/env python3
"""Generate four spatial GLB parts from both GeoJSON sources shown by test.html button 4."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
import trimesh
from PIL import ImageColor
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ("footprints", ROOT / "complete_data/OSM/data/buildings/ermita-building-footprints.geojson", "#c8bca9"),
    ("roof_details", ROOT / "complete_data/OSM/data/buildings/ermita-building-roof-details.geojson", "#d6a477"),
]
OUT = ROOT / "complete_data/OSM/data/buildings/parts"
TO_M = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
FROM_M = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def tags_of(feature):
    props = feature.get("properties") or {}
    tags = props.get("tags")
    return {**props, **tags} if isinstance(tags, dict) else props

def polygons(geom):
    if isinstance(geom, Polygon): return [geom]
    if isinstance(geom, MultiPolygon): return list(geom.geoms)
    if isinstance(geom, GeometryCollection): return [p for child in geom.geoms for p in polygons(child)]
    return []

def number(value):
    try:
        m = re.search(r"-?\d+(?:[.,]\d+)?", str(value).strip())
        return float(m.group().replace(",", ".")) if m else None
    except (ValueError, TypeError):
        return None

def nested_or_flat(props, key):
    value = props.get(key)
    if value is None and isinstance(props.get("tags"), dict): value = props["tags"].get(key)
    return value

def render_height(props):
    # Same precedence and thresholds as test.html button 4.
    h = number(nested_or_flat(props, "height")) or 0
    levels = number(nested_or_flat(props, "building:levels"))
    if levels is None: levels = number(nested_or_flat(props, "levels"))
    if h > 0: return max(3.0, h)
    if levels is not None and levels > 0: return max(3.0, levels * 3.15)
    return 5.0

def render_base(props):
    return max(0.0, number(nested_or_flat(props, "min_height")) or 0.0)

def color_value(value, fallback):
    if not value: value = fallback
    try:
        rgb = ImageColor.getrgb(str(value).strip())[:3]
        return [v / 255.0 for v in rgb] + [1.0], str(value)
    except Exception:
        return [int(fallback[i:i+2], 16) / 255.0 for i in (1, 3, 5)] + [1.0], fallback

def render_color(props, fallback):
    value = props.get("render_color")
    if value is None: value = props.get("colour")
    if value is None: value = props.get("building:colour")
    if value is None: value = nested_or_flat(props, "building:colour")
    return color_value(value, fallback)

def source_id(feature, source_key, index):
    props = feature.get("properties") or {}
    tags = props.get("tags") if isinstance(props.get("tags"), dict) else {}
    for value in (props.get("osm_feature_id"), props.get("id"), tags.get("osm_feature_id"), tags.get("id")):
        if value is not None and str(value).strip(): return str(value)
    return f"{source_key}-feature-{index:06d}"

def main():
    rows, source_summary, hashes = [], [], {}
    invalid_repaired = 0
    for source_key, path, fallback in SOURCES:
        if not path.is_file(): raise FileNotFoundError(f"Required button-4 source missing: {path}")
        raw = path.read_bytes()
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        features = data.get("features") or []
        start_count, component_count = len(rows), 0
        for index, feature in enumerate(features):
            gj = feature.get("geometry")
            if not gj: continue
            geom = geom_transform(TO_M, shape(gj))
            if not geom.is_valid:
                geom = geom.buffer(0)
                invalid_repaired += 1
            parts = [p for p in polygons(geom) if not p.is_empty and p.area > 0]
            # Button 4 filters to polygon geometry; points and lines are not extruded.
            if not parts: continue
            props = feature.get("properties") or {}
            height, base = render_height(props), render_base(props)
            # Preserve source height/base metadata; avoid negative extrusion where base >= top.
            mesh_top = base + max(0.01, height) if base >= height else height
            rgba, color_raw = render_color(props, fallback)
            area = sum(p.area for p in parts)
            cx = sum(p.area * p.centroid.x for p in parts) / area
            cy = sum(p.area * p.centroid.y for p in parts) / area
            component_count += len(parts)
            rows.append({
                "source_key": source_key, "source_path": str(path.relative_to(ROOT)),
                "source_feature_index": index, "source_feature_id": source_id(feature, source_key, index),
                "source_geometry_type": gj.get("type"), "source_properties": props,
                "source_tags": props.get("tags", {}) if isinstance(props.get("tags"), dict) else {},
                "render_height_m": height, "render_base_m": base, "mesh_top_m": mesh_top,
                "color_raw": color_raw, "base_color_rgba_0_to_1": rgba,
                "base_color_rgba_0_to_255": [round(v * 255) for v in rgba[:3]] + [255],
                "metallic_factor": 0.0, "roughness_factor": 0.85,
                "polygons": parts, "cx": cx, "cy": cy, "area_m2": area, "fallback_color": fallback,
            })
        source_summary.append({
            "source": str(path.relative_to(ROOT)), "geojson_features_total": len(features),
            "polygon_features_exported": len(rows) - start_count,
            "polygon_components_exported": component_count,
            "sha256": hashes[str(path.relative_to(ROOT))],
        })
    if not rows: raise RuntimeError("Neither button-4 source contains exportable polygon features.")

    # Coordinate-based 2x2 partition keeps nearby buildings together.
    minx, maxx = min(r["cx"] for r in rows), max(r["cx"] for r in rows)
    miny, maxy = min(r["cy"] for r in rows), max(r["cy"] for r in rows)
    midx, midy = (minx + maxx) / 2, (miny + maxy) / 2
    groups = {i: [] for i in range(1, 5)}
    for r in rows:
        r["part"] = (2 if r["cx"] >= midx else 1) + (2 if r["cy"] >= midy else 0)
        groups[r["part"]].append(r)
    # If a highly irregular extent leaves a quadrant empty, bisect the largest spatial group.
    while any(not groups[i] for i in range(1, 5)):
        empty = next(i for i in range(1, 5) if not groups[i])
        old = max((i for i in range(1, 5) if len(groups[i]) >= 2), key=lambda i: len(groups[i]), default=None)
        if old is None: raise RuntimeError("Could not create four non-empty spatial parts.")
        current = groups[old]
        xs, ys = [r["cx"] for r in current], [r["cy"] for r in current]
        axis = "cx" if max(xs)-min(xs) >= max(ys)-min(ys) else "cy"
        current.sort(key=lambda r: (r[axis], r["source_key"], r["source_feature_index"]))
        cut = len(current)//2
        groups[old], groups[empty] = current[:cut], current[cut:]
        for r in groups[old]: r["part"] = old
        for r in groups[empty]: r["part"] = empty

    OUT.mkdir(parents=True, exist_ok=True)
    reports, index_rows, total_components = [], [], 0
    for part_no in range(1, 5):
        group = groups[part_no]
        if not group: raise RuntimeError(f"Part {part_no} is empty.")
        area_total = sum(r["area_m2"] for r in group)
        ox = sum(r["cx"] * r["area_m2"] for r in group) / area_total
        oy = sum(r["cy"] * r["area_m2"] for r in group) / area_total
        scene, inventory, components = trimesh.Scene(), [], 0
        for r in sorted(group, key=lambda x: (x["source_key"], x["source_feature_index"])):
            material = trimesh.visual.material.PBRMaterial(
                name=("button4_" + r["source_key"])[:64],
                baseColorFactor=r["base_color_rgba_0_to_255"],
                metallicFactor=r["metallic_factor"], roughnessFactor=r["roughness_factor"],
                alphaMode="OPAQUE", doubleSided=True)
            for comp_no, poly in enumerate(r["polygons"], 1):
                local_poly = geom_transform(lambda x, y, z=None: (x-ox, y-oy), poly)
                mesh = trimesh.creation.extrude_polygon(local_poly, r["mesh_top_m"]-r["render_base_m"], engine="earcut")
                mesh.apply_translation([0, 0, r["render_base_m"]])
                mesh.visual = trimesh.visual.TextureVisuals(material=material)
                name = f'{r["source_key"]}_{r["source_feature_index"]:06d}_poly_{comp_no:03d}'
                scene.add_geometry(mesh, geom_name=name, node_name=name, metadata={
                    "source_key": r["source_key"], "source_feature_id": r["source_feature_id"],
                    "source_feature_index": r["source_feature_index"], "polygon_component": comp_no,
                    "render_height_m": r["render_height_m"], "render_base_m": r["render_base_m"]})
                components += 1
            inv = {k: v for k, v in r.items() if k not in ("polygons", "cx", "cy", "area_m2", "part", "fallback_color")}
            inv["polygon_components_exported"] = len(r["polygons"])
            inv["centroid_epsg3857_m"] = {"x": r["cx"], "y": r["cy"]}
            inv["area_m2"] = r["area_m2"]
            inv["material"] = {
                "name": "button4_" + r["source_key"],
                "base_color_rgba_0_to_1": r["base_color_rgba_0_to_1"],
                "base_color_rgba_0_to_255": r["base_color_rgba_0_to_255"],
                "metallic_factor": r["metallic_factor"], "roughness_factor": r["roughness_factor"],
                "source_material_tag": nested_or_flat(r["source_properties"], "building:material") or nested_or_flat(r["source_properties"], "material"),
                "source_color_tag": nested_or_flat(r["source_properties"], "building:colour") or nested_or_flat(r["source_properties"], "colour"),
                "button4_color_property_resolved": r["color_raw"],
                "note": "Button 4 has no metallic/roughness controls; neutral PBR values are recorded alongside all original material/color tags."}
            inventory.append(inv)
            index_rows.append({"part": part_no, "source_key": r["source_key"], "source_path": r["source_path"],
                "source_feature_index": r["source_feature_index"], "source_feature_id": r["source_feature_id"],
                "polygon_components_exported": len(r["polygons"])})
        folder = OUT / f"part{part_no}"
        folder.mkdir(parents=True, exist_ok=True)
        glb_path = folder / f"part{part_no}.glb"
        scene.export(glb_path, file_type="glb")
        if not glb_path.is_file() or glb_path.stat().st_size < 1000: raise RuntimeError(f"GLB missing or too small: {glb_path}")
        lon, lat = FROM_M(ox, oy)
        origin = {"file": f"part{part_no}.glb", "part": part_no, "part_count": 4, "crs": "EPSG:3857",
            "origin_projected_m": {"x": ox, "y": oy}, "origin_wgs84": {"longitude": lon, "latitude": lat},
            "source_geojson_files": [str(p.relative_to(ROOT)) for _, p, _ in SOURCES],
            "source_feature_count": len(group), "polygon_components_exported": components, "mesh_count": components,
            "spatial_partition": "coordinate-based geographic quadrant; spatial bisection fallback if a quadrant is empty",
            "bounds_epsg3857_m": {"min_x": min(r["cx"] for r in group), "max_x": max(r["cx"] for r in group),
                                  "min_y": min(r["cy"] for r in group), "max_y": max(r["cy"] for r in group)}}
        (folder / f"part{part_no}-origin.json").write_text(json.dumps(origin, ensure_ascii=False, indent=2), encoding="utf-8")
        (folder / f"part{part_no}-inventory.json").write_text(json.dumps({"part": part_no, "part_count": 4, "features": inventory}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        total_components += components
        reports.append({"part": part_no, "folder": str(folder.relative_to(ROOT)), "glb": str(glb_path.relative_to(ROOT)),
            "bytes": glb_path.stat().st_size, "feature_count": len(group), "polygon_components": components,
            "mesh_count": components, "origin_wgs84": origin["origin_wgs84"], "bounds_epsg3857_m": origin["bounds_epsg3857_m"],
            "source_counts": {key: sum(1 for r in group if r["source_key"] == key) for key, _, _ in SOURCES}})
    unique = {(x["source_key"], x["source_feature_index"]) for x in index_rows}
    report = {"status": "validated", "page": "test.html", "button": "4. buildings — footprints and roof details",
        "height_and_color_contract": "Mirrors test.html button 4 height/base/color precedence and source-specific fallback colors.",
        "source_geojson_files": source_summary, "source_polygon_feature_count_exported": len(rows),
        "polygon_components_exported": total_components, "invalid_geometries_repaired": invalid_repaired,
        "part_count": 4, "source_feature_assignments": len(index_rows), "unique_source_assignments": len(unique),
        "all_exported_polygon_features_assigned_once": len(index_rows) == len(rows) and len(unique) == len(rows),
        "limitations": ["GLB matches the polygon geometry and extrusion contract for both button-4 GeoJSON sources; MapLibre vertical-gradient lighting is not a GLB geometry property.",
            "Button 4 has no metallic/roughness settings; GLB records neutral PBR values and preserves all source material/color tags.",
            "Non-polygon features are not extruded because button 4 filters to polygon geometry.",
            "Invalid geometry is repaired with buffer(0); original properties remain in the inventory."], "parts": reports}
    (OUT / "parts-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "parts-inventory-index.json").write_text(json.dumps(index_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text("# Button 4 — four spatial GLB parts\n\nGenerated from both GeoJSON sources drawn by button 4 in test.html. Each partN/partN.glb has an origin sidecar and complete feature inventory. Inventories preserve original properties/tags, resolved color, height, base height, polygon component count, area, centroid, and PBR material fields.\n\nRegenerate with python3 ermita/scripts/generate_button4_building_parts.py. See parts-report.json for input hashes and counts.\n", encoding="utf-8")
    if len(index_rows) != len(rows) or len(unique) != len(rows): raise RuntimeError("Validation failed: polygon source feature omitted or assigned more than once.")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
