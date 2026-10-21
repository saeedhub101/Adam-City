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
from PIL import Image
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import transform as geom_transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
BUILDINGS = ROOT / "complete_data/OSM/data/buildings/ermita-building-footprints.geojson"
DETAILS = ROOT / "complete_data/OSM/data/buildings/ermita-building-details.geojson"
ROADS = ROOT / "complete_data/OSM/data/roads/ermita-road-network.geojson"
OUT_DIR = ROOT / "complete_data/OSM/data/buildings/roxas-boulevard"
OUT_GLB = OUT_DIR / "roxas bulivard buildings.glb"
ORIGIN = OUT_DIR / "roxas-bulivard-buildings-origin.json"
REPORT = OUT_DIR / "roxas-bulivard-buildings-report.json"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
FROM_METERS = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
BUFFER_M = 70.0
PAINTED_CMU_TEXTURE = ROOT / "ermita/assets/textures/Painted-CMU-Block-Architextures.jpeg"
_PAINTED_CMU_IMAGE = None
_TEXTURE_MATERIAL_CACHE = {}

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
    # Correct known, demonstrably inconsistent OSM height tags for landmark towers.
    # These overrides are based on the named building / verified published building data.
    fid = str(tags.get("osm_feature_id") or "")
    if fid in ("way/575422161", "way/822386816"):  # Pearl of the Orient Tower: approx. 168 m
        return 168.0
    if fid == "way/575422162":  # Grand Riviera Suites: verified 57 floors, 230 m
        return 230.0
    if fid == "way/90308376":  # 1322 Golden Empire Tower; source height conflicts with 55 levels
        return 203.0
    if fid == "way/87754850":  # Bayview Park Hotel: verified 14-floor hotel
        return 46.0
    if fid == "way/314226123":  # National Library: six-storey building, 34 m
        return 34.0
    if fid == "way/314226156":  # National Planetarium: 16 m dome
        return 16.0
    h = positive_number(tags.get("height"), 2, 500)
    levels = positive_number(tags.get("building:levels") or tags.get("levels"), 1, 150)
    # Reject obviously incompatible height/level pairs instead of creating a tower only 38 m tall.
    if h is not None and levels is not None:
        if levels >= 8 and h < levels * 2.0:
            return levels * 3.2
        # Reject implausibly tall values for low-rise buildings (e.g. a 4-floor hotel tagged 54 m).
        if levels <= 8 and h > levels * 6.0:
            return levels * 3.2
    if h is not None: return h
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
    pearl_ids = {"way/575422161", "way/822386813", "way/822386814", "way/822386816"}
    golden_empire_ids = {"way/90308376", "way/822386807", "way/822386809", "way/822386811"}
    eton_ids = {"way/575422164", "way/89760235", "way/822386824"}
    if osm_id in pearl_ids:
        known = ("Pearl of the Orient blue glass", [0.28, 0.43, 0.56, 1], 0.16, 0.28)
    elif osm_id in golden_empire_ids:
        known = ("1322 Golden Empire reflective gold glass", [0.52, 0.42, 0.25, 1], 0.24, 0.22)
    elif osm_id in eton_ids:
        known = ("Eton Baypark light facade", [0.78, 0.76, 0.70, 1], 0.04, 0.62)
    if osm_id == "way/575422164":
        # Official Eton Properties imagery shows a red-and-grey 29-storey tower,
        # not a uniform cream block.
        known = ("Eton Baypark red grey tower facade", [0.69, 0.67, 0.64, 1], 0.04, 0.58)
    if osm_id == "way/136842220":
        # The verified Luneta Hotel photo shows a pale yellow historic facade and dark ironwork.
        known = ("Luneta Hotel pale historic facade", [0.78, 0.72, 0.54, 1], 0.01, 0.82)
    if osm_id == "way/87754850":
        # Hotel photo references show the characteristic orange cladding and dark window grid.
        known = ("Bayview Park Hotel orange facade", [0.76, 0.31, 0.14, 1], 0.01, 0.76)
    if osm_id == "way/314226123":
        known = ("National Library pale concrete and tinted glazing", [0.80, 0.81, 0.78, 1], 0.02, 0.78)
    if osm_id == "way/314226156":
        known = ("National Planetarium white dome concrete", [0.83, 0.83, 0.79, 1], 0.01, 0.84)
    if osm_id == "way/89770558":
        # Photo shows dark grey/blue cladding, tinted glazing and a strong red entrance canopy.
        known = ("Red Planet Manila Bay dark cladding", [0.22, 0.24, 0.26, 1], 0.03, 0.62)
    if "1322 golden empire" in identity or "golden empire tower" in identity:
        known = ("Golden Empire reflective gold glass", [0.52, 0.42, 0.25, 1], 0.24, 0.22)
    elif "grand riviera suites" in identity:
        known = ("Grand Riviera pale concrete and blue glazing", [0.76, 0.77, 0.73, 1], 0.05, 0.55)
    elif "eton baypark" in identity:
        known = ("Eton Baypark light facade", [0.78, 0.76, 0.68, 1], 0.04, 0.62)
    elif "sunny bay suites" in identity:
        known = ("Sunny Bay Suites cream facade and charcoal glazing", [0.78, 0.72, 0.60, 1], 0.02, 0.72)
    elif "maritime plaza" in identity:
        known = ("Maritime Plaza light commercial facade", [0.72, 0.70, 0.63, 1], 0.03, 0.68)
    elif "swagman hotel" in identity or "tropical mansion" in identity:
        known = ("Hotel warm painted facade", [0.72, 0.62, 0.48, 1], 0.02, 0.78)
    elif "victoria building" in identity:
        known = ("Victoria Building pale concrete", [0.73, 0.71, 0.65, 1], 0.02, 0.82)
    # Curated landmark appearance takes priority over conflicting/inaccurate generic OSM material tags.
    if known is not None:
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
        # Keep every polygon part of the same OSM building visually consistent.
        # Do not assign colours by loop index: that made one real building change
        # colour between adjacent parts.
        # Keep every fragment from the same OpenFreeMap source feature visually consistent,
        # even when that feature has no matching OSM way ID.
        named_style_key = normalized(" ".join(str(tags.get(k) or "") for k in ("name", "official_name", "brand")))
        style_key = osm_id or named_style_key or str(tags.get("_facade_style_key") or index)
        style_seed = sum(ord(c) for c in style_key) + len(btype)
        chosen = palette[style_seed % len(palette)]
        # Office/hotel buildings tend to have more glazing; only use this as a
        # conservative fallback when source tags do not specify a material.
        if any(x in btype for x in ("office", "hotel", "commercial")) and style_seed % 3 == 0:
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

def facade_texture_mesh(poly, height, tags, label, rgba, metallic, roughness):
    """Tile the inspected painted-CMU albedo over generic opaque facades; keep landmarks/glass distinct."""
    global _PAINTED_CMU_IMAGE
    fid = str(tags.get("osm_feature_id") or "")
    no_texture_ids = {
        "way/575422161", "way/822386813", "way/822386814", "way/822386816",
        "way/575422162", "way/90308376", "way/822386807", "way/822386809", "way/822386811",
        "way/575422164", "way/89760235", "way/822386824", "way/267171200",
        "way/136842220", "way/314226156", "way/89770558",
    }
    if fid in no_texture_ids or height < 4.5 or poly.area < 80:
        return None
    low_label = str(label).lower()
    # Keep curtain-wall/glass buildings smooth; National Library has both concrete fins and glass,
    # so its opaque wall bays are allowed to receive the subtle concrete texture.
    if ("glass" in low_label or "glazing" in low_label) and fid != "way/314226123":
        return None
    if _PAINTED_CMU_IMAGE is None:
        if not PAINTED_CMU_TEXTURE.is_file():
            raise FileNotFoundError(f"Required facade texture is missing: {PAINTED_CMU_TEXTURE}")
        _PAINTED_CMU_IMAGE = Image.open(PAINTED_CMU_TEXTURE).convert("RGB")
    key = (str(label), tuple(round(float(c), 3) for c in rgba[:3]),
           round(float(metallic), 3), round(float(roughness), 3))
    material = _TEXTURE_MATERIAL_CACHE.get(key)
    if material is None:
        material = trimesh.visual.material.PBRMaterial(
            name=(str(label).replace(" ", "_") + "_painted_CMU_texture"),
            baseColorFactor=[int(255*float(c)) for c in rgba[:3]] + [255],
            baseColorTexture=_PAINTED_CMU_IMAGE,
            metallicFactor=float(metallic),
            roughnessFactor=max(0.72, float(roughness)),
            alphaMode="OPAQUE",
            doubleSided=True,
        )
        _TEXTURE_MATERIAL_CACHE[key] = material
    vertices, faces, uvs = [], [], []
    tile_m = 2.4  # approximately four block courses per 2.4 m repeat in the inspected albedo.
    for a, b in zip(list(poly.exterior.coords)[:-1], list(poly.exterior.coords)[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 3.0:
            continue
        tx, ty = dx/length, dy/length
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        offset = 0.028
        base = len(vertices)
        vertices.extend([
            [a[0]+nx*offset, a[1]+ny*offset, 0.04],
            [b[0]+nx*offset, b[1]+ny*offset, 0.04],
            [b[0]+nx*offset, b[1]+ny*offset, height-0.04],
            [a[0]+nx*offset, a[1]+ny*offset, height-0.04],
        ])
        uvs.extend([
            [0.0, 0.0], [length/tile_m, 0.0],
            [length/tile_m, height/tile_m], [0.0, height/tile_m],
        ])
        faces.extend([[base, base+1, base+2], [base, base+2, base+3]])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(uv=np.asarray(uvs), material=material)
    return mesh


def facade_historic_window_mesh(poly, height, part_index):
    """Build arched dark window panels and iron balcony rails for the photographed Luneta Hotel facade."""
    floors = 6
    floor_h = height / floors
    vertices, faces = [], []
    exterior = list(poly.exterior.coords)
    for edge_index, (a, b) in enumerate(zip(exterior[:-1], exterior[1:])):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 5:
            continue
        tx, ty = dx/length, dy/length
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        count = max(2, min(7, int(length // 2.8)))
        width = min(1.15, length/count*0.48)
        for floor in range(floors):
            bottom = floor*floor_h + 0.58
            rect_h = min(1.10, floor_h*0.42)
            arch_r = width*0.5
            for j in range(count):
                along = length*(j+0.5)/count
                cx, cy = a[0]+tx*along, a[1]+ty*along
                # Arched panel outline: vertical jambs and a semicircular crown.
                boundary = [
                    (-width/2, bottom), (width/2, bottom),
                    (width/2, bottom+rect_h)
                ]
                for k in range(1, 8):
                    theta = math.pi*k/8
                    boundary.append((arch_r*math.cos(theta), bottom+rect_h+arch_r*math.sin(theta)))
                boundary.append((-width/2, bottom+rect_h))
                center_u = sum(p[0] for p in boundary)/len(boundary)
                center_z = sum(p[1] for p in boundary)/len(boundary)
                base = len(vertices)
                for u, z in boundary:
                    vertices.append([cx+tx*u+nx*0.06, cy+ty*u+ny*0.06, z])
                vertices.append([cx+tx*center_u+nx*0.06, cy+ty*center_u+ny*0.06, center_z])
                center_idx = base+len(boundary)
                for k in range(len(boundary)):
                    faces.append([center_idx, base+k, base+(k+1)%len(boundary)])
                # Wrought-iron balcony rail below the window: top rail and four uprights.
                if floor > 0:
                    rail_z = floor*floor_h + 0.78
                    rail_y = 0.42
                    rail_width = width*0.92
                    # Top rail as a thin horizontal strip in the facade plane.
                    rail_base = len(vertices)
                    vertices.extend([
                        [cx-tx*rail_width/2+nx*rail_y, cy-ty*rail_width/2+ny*rail_y, rail_z+0.62],
                        [cx+tx*rail_width/2+nx*rail_y, cy+ty*rail_width/2+ny*rail_y, rail_z+0.62],
                        [cx+tx*rail_width/2+nx*rail_y, cy+ty*rail_width/2+ny*rail_y, rail_z+0.68],
                        [cx-tx*rail_width/2+nx*rail_y, cy-ty*rail_width/2+ny*rail_y, rail_z+0.68],
                    ])
                    faces.extend([[rail_base,rail_base+1,rail_base+2],[rail_base,rail_base+2,rail_base+3]])
                    for post in (-0.5, -0.17, 0.17, 0.5):
                        pu = rail_width*post
                        post_base = len(vertices)
                        px, py = cx+tx*pu+nx*rail_y, cy+ty*pu+ny*rail_y
                        vertices.extend([
                            [px-tx*0.018,py-ty*0.018,rail_z+0.08],
                            [px+tx*0.018,py+ty*0.018,rail_z+0.08],
                            [px+tx*0.018,py+ty*0.018,rail_z+0.66],
                            [px-tx*0.018,py-ty*0.018,rail_z+0.66],
                        ])
                        faces.extend([[post_base,post_base+1,post_base+2],[post_base,post_base+2,post_base+3]])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="Luneta_Hotel_arched_glazing_and_wrought_iron",
        baseColorFactor=[42, 49, 48, 255], metallicFactor=0.28, roughnessFactor=0.48,
        alphaMode="OPAQUE"
    ))
    return mesh


def facade_window_mesh(poly, height, tags, part_index):
    """Create edge-aligned facade glazing; use photo-derived arches for the historic Luneta Hotel."""
    if str(tags.get("osm_feature_id") or "") == "way/136842220" and height >= 15:
        return facade_historic_window_mesh(poly, height, part_index)
    if poly.area < 250 or height < 12:
        return None
    fid = str(tags.get("osm_feature_id") or "")
    landmark_floors = {
        "way/575422161": 42, "way/822386813": 40, "way/822386814": 40, "way/822386816": 42,
        "way/575422162": 57,
        "way/90308376": 55, "way/822386807": 55, "way/822386809": 54, "way/822386811": 56,
        "way/575422164": 29, "way/89760235": 8, "way/822386824": 11,
        "way/87754850": 14, "way/314226123": 6,
    }
    levels = positive_number(tags.get("building:levels") or tags.get("levels"), 1, 150)
    floors = landmark_floors.get(fid, int(round(levels)) if levels else max(2, int(round(height / 3.2))))
    # Render the full visible floor rhythm, not just the first 12 floors of a high-rise.
    floors = max(2, min(floors, 60))
    floor_h = height / floors
    window_h = min(1.45, max(0.75, floor_h * 0.52))
    # Use a deterministic but restrained glazing/frame variation by OSM identity.
    seed = sum(ord(c) for c in str(tags.get("osm_feature_id") or tags.get("name") or tags.get("official_name") or tags.get("_facade_style_key") or part_index))
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
        count = max(1, min(12, int(length // 3.0)))
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
    fid = str(tags.get("osm_feature_id") or "")
    if fid in {"way/90308376", "way/822386807", "way/822386809", "way/822386811"}:
        glass = [0.43, 0.34, 0.19, 1.0]  # gold/green reflective curtain wall
    elif fid in {"way/575422161", "way/822386813", "way/822386814", "way/822386816"}:
        glass = [0.12, 0.25, 0.38, 1.0]  # blue glass
    else:
        glass = glass_colors[seed % len(glass_colors)]
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="landmark_tinted_glazing" if fid in {"way/90308376", "way/822386807", "way/822386809", "way/822386811", "way/575422161", "way/822386813", "way/822386814", "way/822386816"} else "photo_informed_glazing_variation",
        baseColorFactor=[int(255*c) for c in glass[:3]] + [255],
        metallicFactor=0.24 if fid in {"way/90308376", "way/822386807", "way/822386809", "way/822386811"} else 0.18,
        roughnessFactor=0.22 if fid in {"way/90308376", "way/822386807", "way/822386809", "way/822386811"} else 0.24,
        alphaMode="OPAQUE"
    ))
    return mesh


def facade_accent_mesh(poly, height, tags, part_index):
    """Add facade bands only where a named/identified building has a visible photo reference.

    Visual checks used:
    - Pearl of the Orient: blue-grey upper tower and a distinctly pink horizontal podium.
      https://www.tectonium.com/pearl-of-the-orient-tower/
    - 1322 Golden Empire: warm reflective gold glazing with strong horizontal floor bands.
      https://gfparchitects.com/project/1322-golden-empire-tower/
    - Grand Riviera Suites: blue glazing, pale projecting floor slabs and pink/red framing.
      https://cf.bstatic.com/xdata/images/hotel/max1024x768/428049742.jpg
    The images are visual references only; no unlicensed photo pixels are baked into the GLB.
    """
    fid = str(tags.get("osm_feature_id") or "")
    pearl_ids = {"way/575422161", "way/822386813", "way/822386814", "way/822386816"}
    golden_empire_ids = {"way/90308376", "way/822386807", "way/822386809", "way/822386811"}
    grand_riviera_ids = {"way/575422162"}
    sunny_bay_ids = {"way/267171200"}
    if fid in pearl_ids and height >= 30:
        floors = 42 if fid in {"way/575422161", "way/822386816"} else 40
        offset, thickness = 0.085, 0.12
        color = [211, 130, 153, 255]
        material_name = "Pearl_of_the_Orient_pink_podium_bands"
        metallic, roughness = 0.02, 0.68
    elif fid in golden_empire_ids and height >= 30:
        floors = 55
        offset, thickness = 0.12, 0.15
        color = [199, 179, 132, 255]
        material_name = "Golden_Empire_warm_gold_floor_spandrels"
        metallic, roughness = 0.16, 0.34
    elif fid in grand_riviera_ids and height >= 30:
        floors = 57
        offset, thickness = 0.20, 0.22
        color = [215, 198, 164, 255]
        material_name = "Grand_Riviera_pale_projecting_floor_bands"
        metallic, roughness = 0.03, 0.54
    elif fid == "way/575422164" and height >= 70:
        # Eton Properties' official project image shows a 29-floor red/grey tower
        # with strong repeated horizontal slab lines.
        floors = 29
        offset, thickness = 0.12, 0.13
        color = [194, 190, 183, 255]
        material_name = "Eton_Baypark_grey_floor_spandrels"
        metallic, roughness = 0.03, 0.58
    elif fid == "way/136842220" and height >= 15:
        # Luneta Hotel photo: pale yellow walls with projecting historic cornices.
        floors = 6
        offset, thickness = 0.16, 0.16
        color = [229, 216, 174, 255]
        material_name = "Luneta_Hotel_pale_cornice_bands"
        metallic, roughness = 0.01, 0.82
    elif fid == "way/87754850" and height >= 35:
        # Bayview Park Hotel: orange Art Moderne facade with dark horizontal floor divisions.
        floors = 14
        offset, thickness = 0.11, 0.075
        color = [101, 72, 57, 255]
        material_name = "Bayview_Park_Hotel_dark_floor_reveals"
        metallic, roughness = 0.01, 0.78
    elif fid == "way/314226123" and height >= 25:
        # National Library: broad pale horizontal concrete bands between tall window bays.
        floors = 6
        offset, thickness = 0.13, 0.18
        color = [216, 218, 213, 255]
        material_name = "National_Library_pale_concrete_spandrels"
        metallic, roughness = 0.01, 0.80
    elif fid in sunny_bay_ids and height >= 20:
        floors = 13
        offset, thickness = 0.24, 0.16
        color = [224, 213, 190, 255]
        material_name = "Sunny_Bay_Suites_cream_balcony_slabs"
        metallic, roughness = 0.02, 0.72
    else:
        return None
    floor_h = height / floors
    vertices, faces = [], []
    exterior = list(poly.exterior.coords)
    for a, b in zip(exterior[:-1], exterior[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 4:
            continue
        tx, ty = dx/length, dy/length
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        for floor in range(1, floors):
            # Photo shows Pearl's pink spandrels concentrated on its lower podium;
            # the upper tower is predominantly blue-grey with pale horizontal bands.
            if fid in pearl_ids and floor > 12:
                continue
            z = floor * floor_h
            points = [
                [a[0]+nx*offset, a[1]+ny*offset, z-thickness/2],
                [b[0]+nx*offset, b[1]+ny*offset, z-thickness/2],
                [b[0]+nx*offset, b[1]+ny*offset, z+thickness/2],
                [a[0]+nx*offset, a[1]+ny*offset, z+thickness/2],
            ]
            base = len(vertices)
            vertices.extend(points)
            faces.extend([[base, base+1, base+2], [base, base+2, base+3]])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name=material_name, baseColorFactor=color,
        metallicFactor=metallic, roughnessFactor=roughness, alphaMode="OPAQUE"
    ))
    return mesh


def facade_podium_mesh(poly, height, tags):
    """Overlay the Pearl of the Orient's photographed pink lower podium, behind glazing."""
    fid = str(tags.get("osm_feature_id") or "")
    pearl_ids = {"way/575422161", "way/822386813", "way/822386814", "way/822386816"}
    if fid not in pearl_ids or height < 30:
        return None
    floors = 42 if fid in {"way/575422161", "way/822386816"} else 40
    podium_top = height * (12.0 / floors)
    vertices, faces = [], []
    for a, b in zip(list(poly.exterior.coords)[:-1], list(poly.exterior.coords)[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 4:
            continue
        if poly.exterior.is_ccw:
            nx, ny = dy/length, -dx/length
        else:
            nx, ny = -dy/length, dx/length
        base = len(vertices)
        vertices.extend([
            [a[0]+nx*0.026, a[1]+ny*0.026, 0.08],
            [b[0]+nx*0.026, b[1]+ny*0.026, 0.08],
            [b[0]+nx*0.026, b[1]+ny*0.026, podium_top],
            [a[0]+nx*0.026, a[1]+ny*0.026, podium_top],
        ])
        faces.extend([[base, base+1, base+2], [base, base+2, base+3]])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="Pearl_of_the_Orient_pink_podium_wall",
        baseColorFactor=[176, 107, 120, 255], metallicFactor=0.01, roughnessFactor=0.72,
        alphaMode="OPAQUE"
    ))
    return mesh


def facade_upper_band_mesh(poly, height, tags):
    """Add Pearl's pale horizontal spandrels above its pink podium, as seen in facade photos."""
    fid = str(tags.get("osm_feature_id") or "")
    pearl_ids = {"way/575422161", "way/822386813", "way/822386814", "way/822386816"}
    if fid not in pearl_ids or height < 30:
        return None
    floors = 42 if fid in {"way/575422161", "way/822386816"} else 40
    floor_h = height / floors
    vertices, faces = [], []
    for a, b in zip(list(poly.exterior.coords)[:-1], list(poly.exterior.coords)[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 4:
            continue
        tx, ty = dx/length, dy/length
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        for floor in range(13, floors):
            z = floor * floor_h
            base = len(vertices)
            vertices.extend([
                [a[0]+nx*0.09, a[1]+ny*0.09, z-0.065],
                [b[0]+nx*0.09, b[1]+ny*0.09, z-0.065],
                [b[0]+nx*0.09, b[1]+ny*0.09, z+0.065],
                [a[0]+nx*0.09, a[1]+ny*0.09, z+0.065],
            ])
            faces.extend([[base, base+1, base+2], [base, base+2, base+3]])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="Pearl_of_the_Orient_pale_upper_spandrels",
        baseColorFactor=[193, 203, 207, 255], metallicFactor=0.08, roughnessFactor=0.42,
        alphaMode="OPAQUE"
    ))
    return mesh


def facade_vertical_fin_mesh(poly, height, tags):
    """Photo-informed vertical fins for Eton Baypark and the National Library."""
    fid = str(tags.get("osm_feature_id") or "")
    if fid == "way/575422164" and height >= 70:
        fractions = (0.18, 0.42, 0.66, 0.90)
        half_width, offset = 0.23, 0.105
        color = [157, 76, 67, 255]
        name, roughness = "Eton_Baypark_terracotta_vertical_fins", 0.70
    elif fid == "way/314226123" and height >= 25:
        # The reference facade has strong white concrete fins dividing large tinted bays.
        fractions = (0.10, 0.30, 0.50, 0.70, 0.90)
        half_width, offset = 0.16, 0.10
        color = [226, 228, 223, 255]
        name, roughness = "National_Library_white_concrete_vertical_fins", 0.78
    else:
        return None
    vertices, faces = [], []
    for a, b in zip(list(poly.exterior.coords)[:-1], list(poly.exterior.coords)[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 9:
            continue
        tx, ty = dx/length, dy/length
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        for fraction in fractions:
            cx, cy = a[0]+dx*fraction, a[1]+dy*fraction
            half = min(half_width, length*0.025)
            base = len(vertices)
            vertices.extend([
                [cx-tx*half+nx*offset, cy-ty*half+ny*offset, 0.25],
                [cx+tx*half+nx*offset, cy+ty*half+ny*offset, 0.25],
                [cx+tx*half+nx*offset, cy+ty*half+ny*offset, height-0.25],
                [cx-tx*half+nx*offset, cy-ty*half+ny*offset, height-0.25],
            ])
            faces.extend([[base, base+1, base+2], [base, base+2, base+3]])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name=name, baseColorFactor=color, metallicFactor=0.02, roughnessFactor=roughness,
        alphaMode="OPAQUE", doubleSided=True
    ))
    return mesh


def facade_planetarium_dome_mesh(poly, total_height, tags):
    """Create the documented 16 m National Planetarium hemisphere, not a rectangular block."""
    if str(tags.get("osm_feature_id") or "") != "way/314226156" or total_height < 14:
        return None
    radius = 8.0
    base_z = total_height - radius
    cx, cy = poly.centroid.x, poly.centroid.y
    segments, rings = 48, 12
    vertices, faces = [], []
    for ring in range(rings):
        phi = (math.pi/2) * (ring/rings)
        rr = radius*math.cos(phi)
        z = base_z + radius*math.sin(phi)
        for seg in range(segments):
            angle = 2*math.pi*seg/segments
            vertices.append([cx+rr*math.cos(angle), cy+rr*math.sin(angle), z])
    top_index = len(vertices)
    vertices.append([cx, cy, base_z+radius])
    for ring in range(rings-1):
        start, nxt = ring*segments, (ring+1)*segments
        for seg in range(segments):
            a, b = start+seg, start+(seg+1)%segments
            c, d = nxt+(seg+1)%segments, nxt+seg
            faces.extend([[a,b,c],[a,c,d]])
    last = (rings-1)*segments
    for seg in range(segments):
        faces.append([last+seg,last+(seg+1)%segments,top_index])
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="National_Planetarium_white_dome",
        baseColorFactor=[226, 227, 222, 255], metallicFactor=0.01, roughnessFactor=0.82,
        alphaMode="OPAQUE", doubleSided=True
    ))
    return mesh


def facade_red_planet_canopy_mesh(poly, height, tags):
    """Photo-derived red entrance canopy on Red Planet Manila Bay's street frontage."""
    if str(tags.get("osm_feature_id") or "") != "way/89770558" or height < 12:
        return None
    vertices, faces = [], []
    minx = poly.bounds[0]
    zc, thickness, offset = min(3.25, height*0.28), 0.62, 0.19
    for a, b in zip(list(poly.exterior.coords)[:-1], list(poly.exterior.coords)[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 4:
            continue
        tx, ty = dx/length, dy/length
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        midpoint_x = (a[0]+b[0])/2
        # The reference image shows the bright red sign/canopy facing the street.
        if midpoint_x > minx + 1.5:
            continue
        nx, ny = -1.0, 0.0
        base = len(vertices)
        vertices.extend([
            [a[0]+nx*offset,a[1]+ny*offset,zc-thickness/2],
            [b[0]+nx*offset,b[1]+ny*offset,zc-thickness/2],
            [b[0]+nx*offset,b[1]+ny*offset,zc+thickness/2],
            [a[0]+nx*offset,a[1]+ny*offset,zc+thickness/2],
        ])
        faces.extend([[base,base+1,base+2],[base,base+2,base+3]])
    if not faces:
        return None
    mesh=trimesh.Trimesh(vertices=np.asarray(vertices),faces=np.asarray(faces),process=False)
    mesh.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name="Red_Planet_Hotels_red_canopy",
        baseColorFactor=[219, 22, 39, 255], metallicFactor=0.02, roughnessFactor=0.48,
        alphaMode="OPAQUE", doubleSided=True
    ))
    return mesh


def facade_base_mesh(poly, height, tags, part_index):
    """Add photo-derived street-level podium finishes on Sunny Bay and Bayview Park Hotel."""
    fid = str(tags.get("osm_feature_id") or "")
    if fid == "way/267171200" and height >= 20:
        base_height = min(3.2, height * 0.12)
        base_color, material_name = [44, 47, 49, 255], "Sunny_Bay_Suites_charcoal_tile_entrance"
    elif fid == "way/87754850" and height >= 35:
        base_height = min(5.5, height * 0.14)
        base_color, material_name = [139, 132, 121, 255], "Bayview_Park_Hotel_stone_glass_podium"
    elif fid == "way/89770558" and height >= 12:
        base_height = min(2.8, height * 0.18)
        base_color, material_name = [31, 34, 37, 255], "Red_Planet_dark_glass_street_base"
    else:
        return None
    vertices, faces = [], []
    minx = poly.bounds[0]
    for a, b in zip(list(poly.exterior.coords)[:-1], list(poly.exterior.coords)[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length < 3:
            continue
        tx, ty = dx/length, dy/length
        if poly.exterior.is_ccw:
            nx, ny = ty, -tx
        else:
            nx, ny = -ty, tx
        midpoint_x = (a[0] + b[0]) / 2
        # The building faces Roxas Boulevard/Manila Bay to the west (negative X normal).
        if fid in {"way/87754850", "way/89770558"}:
            # These two photo references show their principal entrance on the west street edge.
            if midpoint_x > minx + 1.5:
                continue
            nx, ny = -1.0, 0.0
        elif nx > -0.5 or midpoint_x > minx + 1.5:
            continue
        points = [
            [a[0]+nx*0.10, a[1]+ny*0.10, 0.08],
            [b[0]+nx*0.10, b[1]+ny*0.10, 0.08],
            [b[0]+nx*0.10, b[1]+ny*0.10, base_height],
            [a[0]+nx*0.10, a[1]+ny*0.10, base_height],
        ]
        base = len(vertices)
        vertices.extend(points)
        faces.extend([[base, base+1, base+2], [base, base+2, base+3]])
    if not faces:
        return None
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name=material_name, baseColorFactor=base_color, metallicFactor=0.02, roughnessFactor=0.78,
        alphaMode="OPAQUE", doubleSided=True
    ))
    return mesh

def main():
    for p in (BUILDINGS, DETAILS, ROADS):
        if not p.is_file() or p.stat().st_size < 20:
            raise SystemExit(f"Required source file missing or empty: {p}")
    building_data = json.loads(BUILDINGS.read_text(encoding="utf-8"))
    detail_data = json.loads(DETAILS.read_text(encoding="utf-8"))
    road_data = json.loads(ROADS.read_text(encoding="utf-8"))
    # Build a spatial index over the richer OSM building-detail dataset. The footprint
    # export contains many geometry pieces without IDs; spatially rejoin them to real OSM
    # identities/tags before applying materials, heights, and landmark facade rules.
    detail_records = []
    for feature in detail_data.get("features", []):
        if not feature.get("geometry"):
            continue
        try:
            geom = geom_transform(TO_METERS, shape(feature["geometry"]))
            tags = tags_of(feature)
            if geom.geom_type not in ("Polygon", "MultiPolygon") or geom.is_empty:
                continue
            if not (tags.get("building") or tags.get("name") or tags.get("osm_feature_id")):
                continue
            detail_records.append({"poly": geom, "tags": tags,
                                   "id": str(tags.get("osm_feature_id") or feature.get("id") or "")})
        except Exception:
            continue
    detail_geoms = [x["poly"] for x in detail_records]
    detail_tree = STRtree(detail_geoms) if detail_geoms else None
    detail_geom_index = {id(g): i for i, g in enumerate(detail_geoms)}
    detail_wkb_index = {}
    for i, g in enumerate(detail_geoms):
        detail_wkb_index.setdefault(g.wkb, i)
    detail_match_count = 0
    detail_named_match_count = 0
    detail_matched_ids = set()
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
            base_tags = tags_of(feature)
            base_fid = str(base_tags.get("osm_feature_id") or feature.get("id") or "")
            for poly in polygon_parts(g):
                if poly.is_empty or not poly.is_valid or poly.area < 8:
                    continue
                # Reset identity and tags for EACH polygon component. A MultiPolygon may
                # contain many disconnected buildings; never leak a match from one part
                # into the next component of the same source feature.
                tags = dict(base_tags)
                fid = base_fid
                # The source export can repeat the same footprint many times. Keep one
                # copy per exact polygon geometry before making massing or facade details.
                footprint_key = poly.wkb
                if footprint_key in seen_footprints:
                    duplicate_footprints_removed += 1
                    continue
                seen_footprints.add(footprint_key)
                # Match ID-less footprint fragments against the detailed OSM polygons.
                # Require meaningful overlap with both shapes to avoid assigning a nearby
                # building's identity to a merely adjacent footprint.
                if not fid and detail_tree is not None:
                    best_record, best_score = None, 0.0
                    for hit in detail_tree.query(poly):
                        if isinstance(hit, (int, np.integer)):
                            record = detail_records[int(hit)]
                        else:
                            idx = detail_geom_index.get(id(hit), detail_wkb_index.get(hit.wkb))
                            if idx is None:
                                continue
                            record = detail_records[idx]
                        candidate = record["poly"]
                        try:
                            inter_area = poly.intersection(candidate).area
                        except Exception:
                            continue
                        if inter_area <= 0:
                            continue
                        poly_overlap = inter_area / max(poly.area, 1e-9)
                        detail_overlap = inter_area / max(candidate.area, 1e-9)
                        if poly_overlap < 0.35 or detail_overlap < 0.05:
                            continue
                        score = poly_overlap + detail_overlap
                        if score > best_score:
                            best_record, best_score = record, score
                    if best_record is not None:
                        tags = {**tags, **best_record["tags"]}
                        fid = best_record["id"]
                        detail_match_count += 1
                        if tags.get("name") or tags.get("official_name"):
                            detail_named_match_count += 1
                        if fid:
                            detail_matched_ids.add(fid)
                selected.append({"id": fid, "tags": tags, "poly": poly, "height": height_of(tags),
                                 "detail_matched": bool(fid and not str(tags_of(feature).get("osm_feature_id") or feature.get("id") or ""))})
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
    building_inventory = {}
    facade_detail_parts = 0
    facade_window_boxes = 0
    facade_accent_parts = 0
    facade_base_parts = 0
    facade_historic_mesh_parts = 0
    facade_texture_parts = 0
    facade_planetarium_dome_parts = 0
    facade_red_planet_canopy_parts = 0
    facade_special_mass_overrides = 0
    used_ids = set()
    for i, item in enumerate(selected):
        poly, height = item["poly"], item["height"]
        tags = dict(item["tags"])
        # Anonymous OpenFreeMap components are grouped into large MultiPolygons. Derive a
        # deterministic key from each component's own geometry rather than the shared tile
        # feature ID, so unrelated buildings do not all inherit one facade colour.
        centroid = poly.centroid
        tags["_facade_style_key"] = f"{centroid.x:.1f}:{centroid.y:.1f}:{poly.area:.1f}"
        # The National Planetarium is a low hall with a 16 m dome; model its hall at
        # 8 m and the separately modeled hemisphere from 8 m to the verified 16 m top.
        fid = str(tags.get("osm_feature_id") or "")
        mass_height = 8.0 if fid == "way/314226156" else height
        if fid == "way/314226156":
            facade_special_mass_overrides += 1
        # GLB local frame is centered on the corridor origin. Vertical base is local 0.
        local = trimesh.creation.extrude_polygon(
            geom_transform(lambda x, y, z=None: (x-cx, y-cy), poly), mass_height, engine="earcut"
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
        # Add a tiled albedo shell to opaque generic facades, while keeping identified glass
        # towers and photographed landmark profiles on their own materials.
        textured_facade = facade_texture_mesh(poly, mass_height, tags, label, rgba, metal, rough)
        if textured_facade is not None:
            textured_facade.apply_translation([-cx, -cy, 0.0])
            texture_node = f"{node}_textured_facade_{i}"
            scene.add_geometry(textured_facade, node_name=texture_node, geom_name=texture_node)
            facade_texture_parts += 1
        # Add visible, edge-aligned glazing to the existing building massing.
        # Geometry remains derived from the selected OSM footprint and height.
        glazing = facade_window_mesh(poly, mass_height, tags, i)
        if glazing is not None:
            # Match the exact same centered local coordinate frame as the extruded mass.
            glazing.apply_translation([-cx, -cy, 0.0])
            glazing_node = f"{node}_glazing_{i}"
            scene.add_geometry(glazing, node_name=glazing_node, geom_name=glazing_node)
            facade_detail_parts += 1
            if str(tags.get("osm_feature_id") or "") == "way/136842220":
                facade_historic_mesh_parts += 1
            else:
                facade_window_boxes += len(glazing.faces) // 12
        accents = facade_accent_mesh(poly, mass_height, tags, i)
        if accents is not None:
            accents.apply_translation([-cx, -cy, 0.0])
            accent_node = f"{node}_facade_accents_{i}"
            scene.add_geometry(accents, node_name=accent_node, geom_name=accent_node)
            facade_accent_parts += 1
        base_mesh = facade_base_mesh(poly, mass_height, tags, i)
        if base_mesh is not None:
            base_mesh.apply_translation([-cx, -cy, 0.0])
            base_node = f"{node}_facade_base_{i}"
            scene.add_geometry(base_mesh, node_name=base_node, geom_name=base_node)
            facade_base_parts += 1
        # Photo-derived landmark-specific podium and floor-band geometry.
        for special_mesh, special_name in (
            (facade_podium_mesh(poly, height, tags), "photo_podium"),
            (facade_upper_band_mesh(poly, height, tags), "photo_upper_bands"),
            (facade_vertical_fin_mesh(poly, mass_height, tags), "photo_vertical_fins"),
            (facade_planetarium_dome_mesh(poly, height, tags), "photo_planetarium_dome"),
            (facade_red_planet_canopy_mesh(poly, height, tags), "photo_red_planet_canopy"),
        ):
            if special_mesh is not None:
                special_mesh.apply_translation([-cx, -cy, 0.0])
                special_node = f"{node}_{special_name}_{i}"
                scene.add_geometry(special_mesh, node_name=special_node, geom_name=special_node)
                facade_accent_parts += 1
                if special_name == "photo_planetarium_dome":
                    facade_planetarium_dome_parts += 1
                if special_name == "photo_red_planet_canopy":
                    facade_red_planet_canopy_parts += 1
        if item["id"]:
            used_ids.add(item["id"])
            entry = building_inventory.setdefault(item["id"], {
                "name": tags.get("name") or tags.get("official_name") or "",
                "building": tags.get("building") or "",
                "levels_tag": tags.get("building:levels") or tags.get("levels") or "",
                "height_tag_m": tags.get("height") or "",
                "height_used_m": float(height),
                "material_tag": tags.get("building:material") or tags.get("facade:material") or tags.get("material") or "",
                "colour_tag": tags.get("building:colour") or tags.get("building:color") or tags.get("colour") or tags.get("color") or "",
                "footprint_parts": 0,
                "material_assigned": label,
            })
            entry["footprint_parts"] += 1
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
        "building_inventory": building_inventory,
        "detail_polygon_count": len(detail_records),
        "detail_matched_footprint_parts": detail_match_count,
        "detail_matched_named_parts": detail_named_match_count,
        "detail_matched_unique_osm_ids": len(detail_matched_ids),
        "facade_detail_parts": facade_detail_parts,
        "facade_window_boxes": facade_window_boxes,
        "facade_historic_photo_mesh_parts": facade_historic_mesh_parts,
        "facade_textured_shell_parts": facade_texture_parts,
        "facade_texture_method": "Inspected Painted-CMU-Block albedo tiled at approximately 2.4 m per repeat on generic opaque facade shells; landmark glass and custom profiles are excluded.",
        "facade_planetarium_dome_parts": facade_planetarium_dome_parts,
        "facade_red_planet_canopy_parts": facade_red_planet_canopy_parts,
        "facade_special_mass_overrides": facade_special_mass_overrides,
        "facade_accent_parts": facade_accent_parts,
        "facade_base_parts": facade_base_parts,
        "facade_detail_method": "Procedural edge-aligned glazing for tall buildings; photo-informed spandrel/podium geometry for Pearl of the Orient, 1322 Golden Empire Tower, Grand Riviera Suites, Eton Baypark, Sunny Bay Suites, Bayview Park Hotel, and Red Planet Manila Bay; National Library uses pale concrete bands and vertical fins; Luneta Hotel uses arched dark glazing and wrought-iron balcony rails; National Planetarium uses a separate 16 m hemispherical dome above its low hall. Other buildings retain geometry-derived glazing and conservative PBR materials pending individual photographic verification.",
        "visual_reference_checks": [
            {"building": "Pearl of the Orient Tower", "url": "https://www.tectonium.com/pearl-of-the-orient-tower/", "observed": "blue-grey upper tower, repetitive pale horizontal bands, distinct pink horizontal podium"},
            {"building": "1322 Golden Empire Tower", "url": "https://gfparchitects.com/project/1322-golden-empire-tower/", "observed": "warm gold reflective glazing and strong repeated horizontal floor divisions"},
            {"building": "Grand Riviera Suites", "url": "https://cf.bstatic.com/xdata/images/hotel/max1024x768/428049742.jpg", "observed": "blue glazing, pale projecting floor slabs, pink/red framing concentrated on lower facade"},
            {"building": "Eton Baypark Manila", "url": "https://eton.com.ph/wp-content/uploads/2020/02/EBM1-1200x675.jpg", "observed": "29-storey red-and-grey tower with vertical terracotta strips and repeated floor divisions"},
            {"building": "Luneta Hotel", "url": "https://upload.wikimedia.org/wikipedia/commons/6/65/Ph-mm-manila-ermita-kalaw_ave.-luneta_hotel_%282014%29.JPG", "observed": "pale yellow historic facade, arched openings and dark wrought-iron balconies"},
            {"building": "Bayview Park Hotel Manila", "url": "https://images.trvl-media.com/hotels/1000000/530000/522400/522347/81dac4c5_z.jpg", "observed": "orange Art Moderne facade, repeated window grid, dark floor reveals and stone/glass street-level podium"},
            {"building": "National Library of the Philippines", "url": "https://commons.wikimedia.org/wiki/File:National_Library_of_the_Philippines_in_February_2026_1.jpg", "observed": "six-storey pale concrete facade with large tinted glazing and strong vertical fins"},
            {"building": "National Planetarium", "url": "https://commons.wikimedia.org/wiki/File:02609jfManila_Ermita_Planetarium_Rizal_Park_Padre_Burgos_Streets_Buildings_Landmarksfvf_18.jpg", "observed": "low rectangular hall with a prominent 16 m white hemispherical dome and curved entrance canopy"},
            {"building": "Red Planet Manila Bay", "url": "https://res.klook.com/klook-hotel/image/upload/travelapi/20000000/19730000/19720900/19720865/a1174614_z.jpg", "observed": "dark grey/blue facade, tinted windows, bright red horizontal entrance canopy and dark glazed street-level base"}
        ],
        "pbr": "glTF 2.0 metallic-roughness PBR materials; baseColorFactor, metallicFactor, roughnessFactor",
        "selection_method": "Full building footprint intersects a 70 m buffer around road features whose OSM name/official/alternate English name explicitly contains Roxas Boulevard.",
        "height_method": "Verified landmark overrides first; otherwise validate OSM height against floor count, then building:levels × 3.2 m, then 9.6 m fallback.",
        "limitations": ["This pass corrects known tower height-tag conflicts and generates facade glazing through the full tagged floor count; it does not yet constitute exact photogrammetric reconstruction.",
                       "Per-building facade proportions, balconies, crown shapes, ornament, signs, and exact colour/texture still require individual reference-photo matching and validation.",
                       "Vertical ground elevations are not baked into this GLB; anchor altitude is 0 m and existing terrain/building layers remain unchanged."],
        "source": "OpenStreetMap contributors, ODbL 1.0",
        "skipped_invalid_features": skipped,
    }
    REPORT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
