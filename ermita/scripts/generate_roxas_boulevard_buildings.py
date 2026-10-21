#!/usr/bin/env python3
"""Build a standalone PBR GLB for buildings fronting Roxas Boulevard in Ermita.

Selection is spatially grounded: OSM building footprints within 70 projected metres
of mapped road segments explicitly named Roxas Boulevard (or a Roxas Blvd variant).
The output keeps a shared EPSG:3857 metre coordinate frame and records its origin.
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

import numpy as np
import trimesh
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings/ermita-building-footprints.geojson"
ROADS = ROOT / "complete_data/OSM/data/roads/ermita-road-network.geojson"
OUT_DIR = ROOT / "complete_data/OSM/data/buildings/roxas-boulevard"
OUT_GLB = OUT_DIR / "roxas bulivard buildings.glb"
ORIGIN = OUT_DIR / "roxas-bulivard-buildings-origin.json"
REPORT = OUT_DIR / "roxas-bulivard-buildings-report.json"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
FROM_METERS = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
BUFFER_M = 70.0

def tags_of(feature):
    props = feature.get("properties") or {}
    tags = props.get("tags")
    return {**props, **tags} if isinstance(tags, dict) else props

def polygon_parts(g):
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    if isinstance(g, GeometryCollection): return [p for x in g.geoms for p in polygon_parts(x)]
    return []

def positive_number(value, low, high):
    try:
        m = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(",", "."))
        n = float(m.group()) if m else None
        return n if n is not None and low <= n <= high else None
    except (ValueError, TypeError):
        return None

def height_of(tags):
    h = positive_number(tags.get("height"), 2, 500)
    if h is not None: return h
    levels = positive_number(tags.get("building:levels") or tags.get("levels"), 1, 150)
    return levels * 3.2 if levels is not None else 9.6

def normalized(value):
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")

def pbr_for(tags, index):
    material = normalized(tags.get("building:material") or tags.get("facade:material") or tags.get("material"))
    colour = normalized(tags.get("building:colour") or tags.get("building:color") or tags.get("colour") or tags.get("color"))
    btype = normalized(tags.get("building"))
    osm_id = str(tags.get("osm_feature_id") or "").lower()
    identity = normalized(" ".join(str(tags.get(k) or "") for k in
        ("name", "official_name", "brand", "building:architecture", "tourism", "amenity")))
    # Photo-informed architectural palettes for identified buildings in the corridor.
    # These affect the facade finish; window geometry is added separately below.
    known = None
    if osm_id in ("way/575422161", "way/575422163", "way/575422164"):
        known = ("Pearl of the Orient blue glass", [0.34, 0.48, 0.58, 1], 0.16, 0.28)
    elif osm_id == "way/90308376" or osm_id.startswith("way/82238680") or osm_id.startswith("way/82238681") or osm_id.startswith("way/82238682"):
        known = ("1322 Golden Empire blue-grey glass", [0.42, 0.52, 0.57, 1], 0.16, 0.30)
    if "1322 golden empire" in identity or "golden empire tower" in identity:
        known = ("Golden Empire blue-grey curtain wall", [0.42, 0.52, 0.57, 1], 0.16, 0.30)
    elif "grand riviera suites" in identity:
        known = ("Grand Riviera pale concrete and blue glazing", [0.76, 0.77, 0.73, 1], 0.05, 0.55)
    elif "eton baypark" in identity:
        known = ("Eton Baypark light facade", [0.78, 0.76, 0.68, 1], 0.04, 0.62)
    elif "maritime plaza" in identity:
        known = ("Maritime Plaza light commercial facade", [0.72, 0.70, 0.63, 1], 0.03, 0.68)
    elif "swagman hotel" in identity or "tropical mansion" in identity:
        known = ("Hotel warm painted facade", [0.72, 0.62, 0.48, 1], 0.02, 0.78)
    elif "victoria building" in identity:
        known = ("Victoria Building pale concrete", [0.73, 0.71, 0.65, 1], 0.02, 0.82)
    if known is not None and not colour and not material:
        return known
    # Prefer explicit source colour/material tags when present. For untagged buildings,
    # use restrained, varied architectural neutrals rather than a single city-wide tint.
    palette = [
        ("limestone warm", [0.72, 0.68, 0.59, 1], 0.0, 0.82),
        ("painted ivory", [0.79, 0.77, 0.70, 1], 0.0, 0.88),
        ("concrete grey", [0.57, 0.58, 0.55, 1], 0.0, 0.92),
        ("sandstone", [0.69, 0.57, 0.43, 1], 0.0, 0.84),
        ("muted terracotta", [0.56, 0.35, 0.27, 1], 0.0, 0.87),
        ("glass blue grey", [0.36, 0.48, 0.53, 1], 0.12, 0.28),
    ]
    chosen = None
    if any(x in material for x in ("glass", "glazing")) or any(x in colour for x in ("blue", "glass")):
        chosen = ("glass blue grey", [0.36, 0.48, 0.53, 1], 0.12, 0.28)
    elif any(x in material for x in ("stone", "limestone", "marble")) or "white" in colour or "ivory" in colour:
        chosen = ("stone/ivory", [0.78, 0.75, 0.66, 1], 0.0, 0.82)
    elif any(x in material for x in ("concrete", "cement", "plaster")) or "grey" in colour or "gray" in colour:
        chosen = ("concrete/plaster", [0.61, 0.60, 0.56, 1], 0.0, 0.91)
    elif any(x in material for x in ("brick", "terracotta")) or "red" in colour or "brown" in colour:
        chosen = ("brick/terracotta", [0.56, 0.36, 0.28, 1], 0.0, 0.88)
    elif "metal" in material or "steel" in material or "aluminium" in material or "aluminum" in material:
        chosen = ("metal panels", [0.48, 0.52, 0.52, 1], 0.65, 0.34)
    if chosen is None:
        chosen = palette[(index * 7 + len(btype)) % len(palette)]
        # Office/hotel buildings tend to have more glazing; use a low-metalness,
        # smoother cool facade only as a neutral fallback, not a claimed survey fact.
        if any(x in btype for x in ("office", "hotel", "commercial")) and index % 3 == 0:
            chosen = palette[5]
    label, base, metal, rough = chosen
    if colour:
        if "white" in colour: base = [0.82,0.81,0.76,1]
        elif "cream" in colour or "beige" in colour: base = [0.75,0.68,0.54,1]
        elif "gray" in colour or "grey" in colour: base = [0.55,0.57,0.56,1]
        elif "red" in colour: base = [0.58,0.28,0.23,1]
        elif "blue" in colour: base = [0.35,0.48,0.61,1]
        elif "brown" in colour: base = [0.43,0.31,0.23,1]
        elif "green" in colour: base = [0.36,0.48,0.34,1]
    return label, base, metal, rough

def facade_window_mesh(poly, height, tags, part_index):
    """Create restrained, edge-aligned window glazing for an existing footprint.
    This adds actual facade geometry to the existing massing; it never replaces footprints.
    """
    if poly.area < 80 or height < 5:
        return None
    levels = positive_number(tags.get("building:levels") or tags.get("levels"), 1, 150)
    floors = int(round(levels)) if levels else max(2, int(round(height / 3.2)))
    floors = max(2, min(floors, 18))
    floor_h = height / floors
    window_h = min(1.45, max(0.75, floor_h * 0.52))
    # Use a deterministic but restrained glazing/frame variation by OSM identity.
    seed = sum(ord(c) for c in str(tags.get("osm_feature_id") or tags.get("name") or part_index))
    glass_colors = [
        [0.10, 0.22, 0.29, 1.0], [0.16, 0.31, 0.39, 1.0],
        [0.25, 0.35, 0.38, 1.0], [0.12, 0.25, 0.34, 1.0]
    ]
    vertices, faces = [], []
    exterior = list(poly.exterior.coords)
    # OSM footprints are in projected metres; walls rise vertically from local Z=0.
    for edge_index, (a, b) in enumerate(zip(exterior[:-1], exterior[1:])):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 5.0:
            continue
        tx, ty = dx/length, dy/length
        # Exterior normal depends on ring winding.
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        count = max(1, min(8, int(length // 2.5)))
        usable = min(1.25, (length / count) * 0.48)
        if usable < 0.45:
            continue
        for floor in range(floors):
            zc = floor * floor_h + floor_h * 0.53
            if zc + window_h/2 >= height - 0.25:
                continue
            for j in range(count):
                along = length * (j + 0.5) / count
                # Small deterministic spacing variations prevent a perfectly repetitive toy look.
                ww = usable * (0.90 if (j + floor + seed) % 5 == 0 else 1.0)
                hh = window_h * (0.90 if (edge_index + floor + seed) % 7 == 0 else 1.0)
                cx = a[0] + tx*along + nx*0.045
                cy = a[1] + ty*along + ny*0.045
                # Oriented shallow box, with its broad face parallel to the wall.
                corners = []
                for u, v, z in [
                    (-ww/2,-0.025,zc-hh/2),(ww/2,-0.025,zc-hh/2),
                    (ww/2,0.025,zc-hh/2),(-ww/2,0.025,zc-hh/2),
                    (-ww/2,-0.025,zc+hh/2),(ww/2,-0.025,zc+hh/2),
                    (ww/2,0.025,zc+hh/2),(-ww/2,0.025,zc+hh/2)
                ]:
                    corners.append([cx + tx*u + nx*v, cy + ty*u + ny*v, z])
                base = len(vertices)
                vertices.extend(corners)
                faces.extend([
                    [base+0,base+1,base+2],[base+0,base+2,base+3],
                    [base+4,base+6,base+5],[base+4,base+7,base+6],
                    [base+0,base+4,base+5],[base+0,base+5,base+1],
                    [base+1,base+5,base+6],[base+1,base+6,base+2],
                    [base+2,base+6,base+7],[base+2,base+7,base+3],
                    [base+3,base+7,base+4],[base+3,base+4,base+0]
                ])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    glass = glass_colors[seed % len(glass_colors)]
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="photo_informed_glazing_variation",
        baseColorFactor=[int(255*c) for c in glass[:3]] + [255],
        metallicFactor=0.18, roughnessFactor=0.24, alphaMode="OPAQUE"
    ))
    return mesh


def main():
    for p in (BUILDINGS, ROADS):
        if not p.is_file() or p.stat().st_size < 20:
            raise SystemExit(f"Required source file missing or empty: {p}")
    building_data = json.loads(BUILDINGS.read_text(encoding="utf-8"))
    road_data = json.loads(ROADS.read_text(encoding="utf-8"))
    boulevard_parts = []
    matched_road_ids = []
    for feature in road_data.get("features", []):
        tags = tags_of(feature)
        names = " ".join(str(tags.get(k) or "") for k in ("name", "official_name", "alt_name", "name:en"))
        compact = re.sub(r"[^a-z]", "", names.lower())
        if "roxasboulevard" not in compact and "roxasblvd" not in compact:
            continue
        try:
            g = geom_transform(TO_METERS, shape(feature["geometry"]))
            if g.geom_type in ("LineString", "MultiLineString") and not g.is_empty:
                boulevard_parts.append(g)
                matched_road_ids.append(str(tags.get("osm_feature_id") or feature.get("id") or ""))
        except Exception as exc:
            print("Skipping invalid Roxas Boulevard segment:", exc)
    if not boulevard_parts:
        raise SystemExit("No road geometry explicitly named Roxas Boulevard was found; refusing to guess a street corridor.")
    from shapely.ops import unary_union
    road_union = unary_union(boulevard_parts)
    corridor = road_union.buffer(BUFFER_M)
    selected = []
    skipped = 0
    duplicate_footprints_removed = 0
    seen_footprints = set()
    for feature in building_data.get("features", []):
        if not feature.get("geometry"):
            continue
        try:
            g = geom_transform(TO_METERS, shape(feature["geometry"]))
            if g.geom_type not in ("Polygon", "MultiPolygon") or g.is_empty:
                continue
            # Include footprints within the 70 m corridor, but keep full footprint geometry.
            if not corridor.intersects(g):
                continue
            tags = tags_of(feature)
            fid = str(tags.get("osm_feature_id") or feature.get("id") or "")
            for poly in polygon_parts(g):
                if poly.is_empty or not poly.is_valid or poly.area < 8:
                    continue
                # The source export can repeat the same footprint many times. Keep one
                # copy per exact polygon geometry before making massing or facade details.
                footprint_key = poly.wkb
                if footprint_key in seen_footprints:
                    duplicate_footprints_removed += 1
                    continue
                seen_footprints.add(footprint_key)
                selected.append({"id": fid, "tags": tags, "poly": poly, "height": height_of(tags)})
        except Exception:
            skipped += 1
    if not selected:
        raise SystemExit("Roxas Boulevard corridor selected zero valid building footprints; refusing to write an empty GLB.")
    minx = min(x["poly"].bounds[0] for x in selected); miny = min(x["poly"].bounds[1] for x in selected)
    maxx = max(x["poly"].bounds[2] for x in selected); maxy = max(x["poly"].bounds[3] for x in selected)
    cx, cy = (minx+maxx)/2, (miny+maxy)/2
    lon, lat = FROM_METERS(cx, cy)
    scene = trimesh.Scene()
    material_stats = {}
    facade_detail_parts = 0
    facade_window_boxes = 0
    used_ids = set()
    for i, item in enumerate(selected):
        poly, tags, height = item["poly"], item["tags"], item["height"]
        # GLB local frame is centered on the corridor origin. Vertical base is local 0.
        local = trimesh.creation.extrude_polygon(
            geom_transform(lambda x, y, z=None: (x-cx, y-cy), poly), height, engine="earcut"
        )
        label, rgba, metal, rough = pbr_for(tags, i)
        material = trimesh.visual.material.PBRMaterial(
            name=label.replace(" ", "_"),
            baseColorFactor=[int(255*c) for c in rgba[:3]] + [255],
            metallicFactor=float(metal),
            roughnessFactor=float(rough),
            alphaMode="OPAQUE",
            doubleSided=False,
        )
        local.visual = trimesh.visual.TextureVisuals(material=material)
        # Stable descriptive node names aid inspection in Blender/3D viewers.
        node = (item["id"] or f"roxas-building-{i+1}").replace("/", "_")
        scene.add_geometry(local, node_name=f"{node}_mass_{i}", geom_name=f"{node}_mass_{i}")
        # Add visible, edge-aligned glazing to the existing building massing.
        # Geometry remains derived from the selected OSM footprint and height.
        glazing = facade_window_mesh(poly, height, tags, i)
        if glazing is not None:
            # Match the exact same centered local coordinate frame as the extruded mass.
            glazing.apply_translation([-cx, -cy, 0.0])
            glazing_node = f"{node}_glazing_{i}"
            scene.add_geometry(glazing, node_name=glazing_node, geom_name=glazing_node)
            facade_detail_parts += 1
            facade_window_boxes += len(glazing.faces) // 12
        if item["id"]: used_ids.add(item["id"])
        material_stats[label] = material_stats.get(label, 0) + 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_GLB.write_bytes(scene.export(file_type="glb"))
    origin = {
        "longitude": float(lon), "latitude": float(lat), "anchor_altitude_m": 0.0,
        "buildings_exported": len(selected), "osm_building_ids": sorted(used_ids),
        "buffer_m": BUFFER_M, "road_segments_used": len(matched_road_ids),
        "coordinate_system": "EPSG:3857 local metres centered at longitude/latitude; local Z starts at 0 m",
        "origin_method": "Bounding-box center of selected OSM building footprints, selected by intersection with 70 m buffer around mapped Roxas Boulevard road geometry."
    }
    ORIGIN.write_text(json.dumps(origin, indent=2)+"\n", encoding="utf-8")
    report = {
        "output": str(OUT_GLB.relative_to(ROOT)), "buildings_exported": len(selected),
        "unique_osm_building_ids": len(used_ids), "road_segments_used": len(matched_road_ids),
        "road_feature_ids": matched_road_ids, "selection_buffer_m": BUFFER_M,
        "material_counts": material_stats,
        "facade_detail_parts": facade_detail_parts,
        "facade_window_boxes": facade_window_boxes,
        "facade_detail_method": "Procedural edge-aligned glazing boxes on selected building footprints; source-tagged building colours/materials take priority, named landmark palettes are applied where identified.",
        "pbr": "glTF 2.0 metallic-roughness PBR materials; baseColorFactor, metallicFactor, roughnessFactor",
        "selection_method": "Full building footprint intersects a 70 m buffer around road features whose OSM name/official/alternate English name explicitly contains Roxas Boulevard.",
        "height_method": "OSM height, then building:levels × 3.2 m, then 9.6 m fallback.",
        "limitations": ["Existing OSM footprint extrusions are retained and augmented with edge-aligned glazing geometry and PBR glass materials; this is a procedural facade-detail pass, not a claim of per-building photogrammetric reconstruction.",
                       "Exact building-specific paint colours, ornamental elements, signage and facade proportions still require photo verification for each identified building; OSM alone does not encode those details.",
                       "Vertical ground elevations are not baked into this GLB; anchor altitude is 0 m and existing terrain/building layers remain unchanged."],
        "source": "OpenStreetMap contributors, ODbL 1.0",
        "skipped_invalid_features": skipped,
    }
    REPORT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
