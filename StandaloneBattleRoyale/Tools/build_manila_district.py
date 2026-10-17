#!/usr/bin/env python3
"""Build a small real-world Manila district GLB from OpenStreetMap footprints and roads."""
from __future__ import annotations
import json, math, os, sys, time
from pathlib import Path
import requests
import trimesh
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import Polygon, LineString
from shapely.ops import triangulate

# Central Manila: Intramuros / Ermita / southern Binondo edge. Deliberately bounded
# to keep the first playable district manageable.
S, W, N, E = 14.575, 120.965, 14.600, 120.990
OUT = Path("StandaloneBattleRoyale/Content/Maps/Manila-Central-District.glb")
OUT.parent.mkdir(parents=True, exist_ok=True)
QUERY = f"""[out:json][timeout:180];
(
 way[building]({S},{W},{N},{E});
 way[highway]({S},{W},{N},{E});
);
out body; >; out skel qt;"""
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
]
def fetch():
    """Fetch OSM data with bounded retries; public Overpass servers are occasionally overloaded."""
    last = None
    session = requests.Session()
    headers = {
        "User-Agent": "AdamRoyal-Research-Map/1.2 (OSM attribution in project README)",
        "Accept": "application/json",
    }
    for round_no in range(2):
        for endpoint in ENDPOINTS:
            # POST first to avoid huge query strings; retry with GET for servers that reject POST.
            for method in ("post", "get"):
                try:
                    if method == "post":
                        response = session.post(endpoint, data={"data": QUERY}, timeout=(12, 75), headers=headers)
                    else:
                        response = session.get(endpoint, params={"data": QUERY}, timeout=(12, 75), headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("elements"):
                        print(f"Downloaded OSM source from {endpoint} ({method.upper()}, pass {round_no + 1})")
                        return data
                    last = RuntimeError(f"{endpoint} returned no elements")
                except Exception as exc:
                    last = exc
                    print(f"OSM endpoint attempt failed: {endpoint} {method.upper()} pass {round_no + 1}: {exc}")
                    time.sleep(1.5 * (round_no + 1))
        if round_no == 0:
            print("All OSM endpoints failed once; waiting before a second pass.")
            time.sleep(8)
    raise RuntimeError(f"Could not download OSM district from any Overpass endpoint after retries: {last}")

def make_facade_texture(path: Path, style: int) -> Image.Image:
    """Create distinct tileable facade atlases as a fallback when no matched street photo exists."""
    import random
    random.seed(7319 + style * 97)
    size = 512
    palettes = [
        ((177, 166, 147), (48, 65, 76)), # aged concrete / blue glass
        ((205, 192, 164), (56, 69, 76)), # warm plaster / dark glass
        ((143, 145, 141), (52, 68, 77)), # grey concrete / glass
        ((183, 160, 132), (70, 76, 76)), # weathered masonry / glass
    ]
    wall, glass = palettes[style % len(palettes)]
    im = Image.new("RGB", (size, size), wall)
    px = im.load()
    for y in range(size):
        for x in range(size):
            n = random.randint(-10, 10)
            px[x,y] = tuple(max(0,min(255,c+n)) for c in wall)
    d = ImageDraw.Draw(im)
    # Repeated facade modules: concrete bands, deep window reveals, frames and sills.
    row_h = 82 if style % 2 == 0 else 68
    for y in range(16, size, row_h):
        d.line((0,y-7,size,y-7), fill=tuple(max(0,c-28) for c in wall), width=4)
        for x in range(12, size, 58):
            ww, hh = random.randint(27,35), random.randint(row_h-30,row_h-20)
            d.rectangle((x-4,y-4,x+ww+4,y+hh+4), fill=tuple(max(0,c-35) for c in wall))
            tint = random.choice([glass, (35,48,58), (77,87,89), (91,99,96)])
            d.rectangle((x,y,x+ww,y+hh), fill=tint)
            d.line((x+4,y+2,x+4,y+hh-2), fill=(155,165,163), width=2)
            d.line((x+ww//2,y,x+ww//2,y+hh), fill=(30,38,42), width=3)
            d.line((x,y+hh//2,x+ww,y+hh//2), fill=(30,38,42), width=2)
            d.line((x-4,y+hh+5,x+ww+4,y+hh+5), fill=tuple(min(255,c+24) for c in wall), width=4)
    im = im.filter(ImageFilter.GaussianBlur(0.25))
    im.save(path, quality=92)
    return im

def main():
    data = fetch()
    nodes = {e["id"]:(e["lon"],e["lat"]) for e in data["elements"] if e["type"]=="node"}
    ways = [e for e in data["elements"] if e["type"]=="way"]
    # Local metric coordinates, centered on the requested real-world district.
    lat0, lon0 = (S+N)/2, (W+E)/2
    def xy(node_id):
        lon,lat = nodes[node_id]
        return ((lon-lon0)*111320*math.cos(math.radians(lat0)), (lat-lat0)*110540)
    scene = trimesh.Scene()
    texture_paths = []
    facade_materials = []
    for style in range(4):
        tex_path = Path(f"StandaloneBattleRoyale/Content/Maps/Manila-Facade-Texture-{style+1}.jpg")
        tex_path.parent.mkdir(parents=True, exist_ok=True)
        image = make_facade_texture(tex_path, style)
        texture_paths.append(tex_path)
        facade_materials.append(trimesh.visual.material.PBRMaterial(
            name=f"ManilaFacadeStyle{style+1}",
            baseColorTexture=image,
            metallicFactor=0.06,
            roughnessFactor=0.82,
        ))
    building_count = road_count = 0
    for way in ways:
        ids = way.get("nodes", [])
        if len(ids) < 2 or any(i not in nodes for i in ids):
            continue
        pts = [xy(i) for i in ids]
        tags = way.get("tags", {})
        if "building" in tags and len(pts) >= 4 and ids[0] == ids[-1]:
            try:
                poly = Polygon(pts).buffer(0)
                if poly.is_empty or poly.area < 12:
                    continue
                levels = tags.get("building:levels")
                try: height = float(levels)*3.1 if levels else float(tags.get("height","").replace(" m",""))
                except (ValueError, TypeError): height = 9.3
                height = min(max(height, 3.2), 85)
                # Triangulate footprint, then extrude each polygon as a solid mesh.
                parts = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
                for part in parts:
                    if part.area < 8: continue
                    mesh = trimesh.creation.extrude_polygon(part, height)
                    mesh.apply_translation([0,0,0])
                    # Select a facade family from OSM building/use tags to avoid one city-wide look.
                    building_kind = str(tags.get("building", "")).lower()
                    material_index = (2 if any(k in building_kind for k in ("commercial","office","retail")) else
                                      1 if any(k in building_kind for k in ("house","residential","apartments")) else
                                      3 if any(k in building_kind for k in ("industrial","warehouse")) else
                                      building_count % 4)
                    vertices = mesh.vertices
                    uv = np.column_stack((vertices[:, 0] / 4.0, vertices[:, 2] / 3.0))
                    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=facade_materials[material_index])
                    scene.add_geometry(mesh, node_name=f"building_{building_count}")
                    building_count += 1
            except Exception:
                continue
        elif "highway" in tags and len(pts) >= 2:
            try:
                line = LineString(pts).simplify(1.2)
                if line.length < 8: continue
                width = 8.0 if tags["highway"] in ("primary","secondary","trunk","tertiary") else 4.5
                road = line.buffer(width/2, cap_style="flat", join_style="mitre")
                if road.is_empty: continue
                mesh = trimesh.creation.extrude_polygon(road, 0.12)
                mesh.visual.face_colors = [48, 51, 56, 255]
                scene.add_geometry(mesh, node_name=f"road_{road_count}")
                road_count += 1
            except Exception:
                continue
    if building_count < 30 or road_count < 15:
        raise RuntimeError(f"OSM geometry below quality gate: buildings={building_count}, roads={road_count}")
    # Ground plane gives a readable continuous playable base.
    ground = trimesh.creation.box(extents=[3000, 3000, 0.2])
    ground.apply_translation([0,0,-0.16])
    ground.visual.face_colors = [83, 103, 75, 255]
    scene.add_geometry(ground, node_name="district_ground")
    scene.export(str(OUT), file_type="glb")
    check = trimesh.load(str(OUT), force="scene")
    if len(check.geometry) < 2 or OUT.stat().st_size < 100_000:
        raise RuntimeError("Exported GLB failed structural/size validation")
    report = {
        "source":"OpenStreetMap contributors",
        "attribution":"© OpenStreetMap contributors",
        "license":"ODbL 1.0",
        "bounds":{"south":S,"west":W,"north":N,"east":E},
        "buildings":building_count,"roads":road_count,
        "mesh_objects":len(check.geometry),"glb_bytes":OUT.stat().st_size,
        "facade_textures":[p.name for p in texture_paths],
        "note":"Real OSM footprints and road alignments; fallback facade textures are procedural, not matched photographs. Exact building signage requires geolocated street-level imagery."
    }
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
if __name__ == "__main__":
    main()
