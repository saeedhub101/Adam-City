#!/usr/bin/env python3
"""Build an isolated, image-only facade decal on the mapped 7-Eleven building on Pedro Gil Street.

The logo is a transparent image texture on a thin vertical quad placed 8 cm off the
nearest exterior footprint edge. It is an independent GLB overlay, not a replacement
for OSM building geometry, the existing Robenson GLB, or the windows GLB.
"""
from __future__ import annotations
import io, json, math, re
from pathlib import Path

import cairosvg
import requests
import trimesh
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "ermita/maps/generated/ermita-building-details.geojson"
STORES_FILE = ROOT / "complete_data/OSM/Markets/ermita-branded-stores.geojson"
ORIGIN_FILE = ROOT / "complete_data/OSM/Markets/commercial-facades-origin.json"
OUT_DIR = ROOT / "complete_data/OSM/Buildings/Markets/facidals"
OUT_GLB = OUT_DIR / "pedro-gil-7eleven-decal.glb"
OUT_REPORT = ROOT / "complete_data/OSM/Markets/pedro-gil-7eleven-decal-report.json"
ASSET_DIR = ROOT / "complete_data/OSM/Markets/assets"
OUT_PNG = ASSET_DIR / "7-eleven-pedro-gil-decal.png"
LOGO_URL = "https://www.7-eleven.com/assets/img/header/7e-logo-color.svg"
TARGET_POI_ID = "node/12342809738"
HEADERS = {"User-Agent": "Adam-City/1.0 (open-data 3D facade research; https://github.com/saeedhub101/Adam-City)"}
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
UNPROJECT = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def get_tags(feature):
    p = feature.get("properties") or {}
    t = p.get("tags")
    return t if isinstance(t, dict) else p

def feature_id(feature):
    p = feature.get("properties") or {}
    return str(p.get("osm_feature_id") or feature.get("id") or "")

def polygon_parts(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    return []

def nearest_edge(poly, point):
    """Return nearest usable boundary edge, preserving its orientation angle."""
    coords = list(poly.exterior.coords)
    choices = []
    for a, b in zip(coords[:-1], coords[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 2.0:
            continue
        den = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((point.x-a[0])*dx + (point.y-a[1])*dy) / den))
        qx, qy = a[0] + t*dx, a[1] + t*dy
        choices.append((math.hypot(point.x-qx, point.y-qy), a, b, length, math.atan2(dy, dx)))
    if not choices:
        return None
    return min(choices, key=lambda row: row[0])

def outward_normal(poly, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    nx, ny = dy/length, -dx/length
    midpoint = Point((a[0]+b[0])/2, (a[1]+b[1])/2)
    if poly.contains(Point(midpoint.x + nx*0.4, midpoint.y + ny*0.4)):
        nx, ny = -nx, -ny
    return nx, ny

def load_logo():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    response = requests.get(LOGO_URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    svg = response.content
    if b"<svg" not in svg[:1000].lower():
        raise RuntimeError("The official 7-Eleven image endpoint did not return an SVG logo")
    cairosvg.svg2png(bytestring=svg, write_to=str(OUT_PNG), output_width=900, output_height=1200)
    return Image.open(OUT_PNG).convert("RGBA")

def main():
    for path in (MAP_FILE, STORES_FILE, ORIGIN_FILE):
        if not path.is_file():
            raise FileNotFoundError(path)
    buildings = json.loads(MAP_FILE.read_text(encoding="utf-8")).get("features", [])
    stores = json.loads(STORES_FILE.read_text(encoding="utf-8")).get("features", [])
    poi = next((f for f in stores if feature_id(f) == TARGET_POI_ID), None)
    if poi is None:
        raise RuntimeError(f"Target mapped store {TARGET_POI_ID} is absent; refusing to guess a replacement")
    poi_geom = poi.get("geometry") or {}
    if poi_geom.get("type") != "Point":
        raise RuntimeError("Target store is not a point geometry")
    pt = geom_transform(PROJECT, Point(poi_geom["coordinates"]))
    candidates = []
    for f in buildings:
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        try:
            projected = geom_transform(PROJECT, shape(g))
            if not projected.is_valid or projected.is_empty:
                continue
            parts = polygon_parts(projected)
            if not parts:
                continue
            poly = max(parts, key=lambda p: p.area)
            dist = projected.distance(pt)
            if dist <= 28:
                candidates.append((dist, f, projected, poly))
        except Exception:
            continue
    if not candidates:
        raise RuntimeError("No building footprint within 28 m of the Pedro Gil 7-Eleven POI; refusing to guess")
    candidates.sort(key=lambda row: row[0])
    distance, building, building_geom, poly = candidates[0]
    edge = nearest_edge(poly, pt)
    if edge is None:
        raise RuntimeError("Matched building has no usable facade edge")
    edge_distance, a, b, edge_length, angle = edge
    nx, ny = outward_normal(poly, a, b)
    origin = json.loads(ORIGIN_FILE.read_text(encoding="utf-8"))
    ox, oy = PROJECT(float(origin["longitude"]), float(origin["latitude"]))
    # A logo-only decal with transparent padding: no frame, billboard, or backing box.
    image = load_logo()
    ratio = image.width / max(1, image.height)
    height = 1.65
    width = min(2.1, height * ratio)
    z_center = 2.45
    offset = 0.08
    cx = (a[0]+b[0])/2 + nx*offset
    cy = (a[1]+b[1])/2 + ny*offset
    ux, uy = (b[0]-a[0])/edge_length, (b[1]-a[1])/edge_length
    # Local EPSG:3857 metres relative to the same exact origin as robenson.glb.
    vertices = [
        [cx-ux*width/2-ox, cy-uy*width/2-oy, z_center-height/2],
        [cx+ux*width/2-ox, cy+uy*width/2-oy, z_center-height/2],
        [cx+ux*width/2-ox, cy+uy*width/2-oy, z_center+height/2],
        [cx-ux*width/2-ox, cy-uy*width/2-oy, z_center+height/2],
    ]
    material = trimesh.visual.material.PBRMaterial(
        name="7-Eleven transparent image decal",
        baseColorFactor=[255, 255, 255, 255],
        baseColorTexture=image,
        metallicFactor=0.0,
        roughnessFactor=0.85,
        alphaMode="BLEND",
        doubleSided=True,
    )
    mesh = trimesh.Trimesh(vertices=vertices, faces=[[0,1,2],[0,2,3]], process=False)
    mesh.visual = trimesh.visual.TextureVisuals(
        uv=[[0,1],[1,1],[1,0],[0,0]],
        material=material,
    )
    mesh.metadata["decal_type"] = "transparent logo image on vertical facade plane"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scene = trimesh.Scene()
    scene.add_geometry(mesh, node_name="Pedro Gil 7-Eleven facade decal")
    OUT_GLB.write_bytes(scene.export(file_type="glb"))
    props = building.get("properties") or {}
    report = {
        "target_store_osm_id": TARGET_POI_ID,
        "target_store_name": (poi.get("properties") or {}).get("name", "7-Eleven"),
        "target_store_street": (poi.get("properties") or {}).get("street", "Pedro Gil Street"),
        "matched_building_osm_id": feature_id(building),
        "matched_building_name": get_tags(building).get("name"),
        "poi_to_building_distance_m": round(distance, 2),
        "poi_to_selected_facade_edge_m": round(edge_distance, 2),
        "facade_edge_length_m": round(edge_length, 2),
        "decal_width_m": round(width, 2),
        "decal_height_m": round(height, 2),
        "decal_center_height_m": z_center,
        "facade_offset_m": offset,
        "origin_file": str(ORIGIN_FILE.relative_to(ROOT)),
        "image_asset": str(OUT_PNG.relative_to(ROOT)),
        "image_source": LOGO_URL,
        "source_note": "Official 7-Eleven logo converted to a transparent PNG and applied as a flat image decal. This is a signage-placement experiment, not a surveyed facade reconstruction.",
        "glb_path": str(OUT_GLB.relative_to(ROOT)),
        "glb_bytes": OUT_GLB.stat().st_size,
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if OUT_GLB.stat().st_size < 1000:
        raise RuntimeError("Generated decal GLB is unexpectedly small")

if __name__ == "__main__":
    main()
