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

def make_road_texture(path: Path) -> Image.Image:
    """Create a reusable, physically varied asphalt texture; lane markings are modeled separately."""
    import random
    random.seed(42017)
    size = 512
    im = Image.new("RGB", (size, size))
    px = im.load()
    for y in range(size):
        for x in range(size):
            grain = random.randint(-13, 13)
            repair = -18 if random.random() < 0.012 else 0
            base = 55 + grain + repair
            px[x, y] = (max(0, base - 3), max(0, base - 2), max(0, base))
    d = ImageDraw.Draw(im)
    for _ in range(1100):
        x, y = random.randrange(size), random.randrange(size)
        shade = random.choice([(39, 40, 41), (69, 68, 65), (76, 74, 70), (48, 49, 48)])
        r = random.choice((1, 1, 2))
        d.ellipse((x-r, y-r, x+r, y+r), fill=shade)
    im = im.filter(ImageFilter.GaussianBlur(0.35))
    im.save(path, quality=94)
    return im


def compact_scene(scene: trimesh.Scene) -> trimesh.Scene:
    """Merge thousands of OSM meshes into material/color batches for real-time rendering.

    Important: Scene.geometry keys are not guaranteed to equal node_name values. Group
    untextured road markings by their actual face color, not by geometry key, otherwise
    every individual dash remains a separate mesh in the exported GLB.
    """
    groups = {}
    materials = {}
    color_groups = {}
    for geometry_name, mesh in scene.geometry.items():
        visual = mesh.visual
        material = getattr(visual, "material", None)
        if isinstance(visual, trimesh.visual.TextureVisuals) and material is not None:
            key = "texture:" + (getattr(material, "name", "") or "unnamed")
            groups.setdefault(key, []).append(mesh)
            materials[key] = material
            continue

        face_colors = getattr(visual, "face_colors", None)
        if face_colors is not None and len(face_colors):
            colors = np.asarray(face_colors, dtype=np.uint8)
            color = tuple(int(v) for v in colors[0])
            if len(colors) == 1 or np.all(colors == colors[0]):
                key = "color:" + "_".join(map(str, color))
                groups.setdefault(key, []).append(mesh)
                color_groups[key] = color
                continue

        vertex_colors = getattr(visual, "vertex_colors", None)
        if vertex_colors is not None and len(vertex_colors):
            colors = np.asarray(vertex_colors, dtype=np.uint8)
            if len(colors) == 1 or np.all(colors == colors[0]):
                color = tuple(int(v) for v in colors[0])
                key = "color:" + "_".join(map(str, color))
                groups.setdefault(key, []).append(mesh)
                color_groups[key] = color
                continue

        groups.setdefault("unclassified:" + geometry_name, []).append(mesh)

    compact = trimesh.Scene()
    for key, meshes in groups.items():
        vertex_chunks = []
        face_chunks = []
        uv_chunks = []
        face_color_chunks = []
        vertex_offset = 0
        has_uv = key in materials
        has_color = key in color_groups
        for mesh in meshes:
            vertex_chunks.append(np.asarray(mesh.vertices))
            face_chunks.append(np.asarray(mesh.faces) + vertex_offset)
            vertex_offset += len(mesh.vertices)
            if has_uv:
                uv = getattr(mesh.visual, "uv", None)
                if uv is None or len(uv) != len(mesh.vertices):
                    raise RuntimeError(f"Textured mesh {key} has missing/incompatible UV coordinates")
                uv_chunks.append(np.asarray(uv))
            elif has_color:
                face_color_chunks.append(
                    np.tile(np.asarray(color_groups[key], dtype=np.uint8), (len(mesh.faces), 1))
                )
        merged = trimesh.Trimesh(
            vertices=np.concatenate(vertex_chunks, axis=0),
            faces=np.concatenate(face_chunks, axis=0),
            process=False,
        )
        if has_uv:
            merged.visual = trimesh.visual.TextureVisuals(
                uv=np.concatenate(uv_chunks, axis=0),
                material=materials[key],
            )
        elif has_color:
            merged.visual.face_colors = np.concatenate(face_color_chunks, axis=0)
        compact.add_geometry(merged, geom_name=key, node_name=key)
    print(f"Compacted map mesh batches: {len(scene.geometry)} -> {len(compact.geometry)}")
    if len(compact.geometry) > 50:
        raise RuntimeError(
            f"Map compaction failed: {len(compact.geometry)} mesh batches remain; "
            "expected 50 or fewer."
        )
    return compact

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
    road_texture_path = Path("StandaloneBattleRoyale/Content/Maps/Manila-Road-Asphalt.jpg")
    road_texture_path.parent.mkdir(parents=True, exist_ok=True)
    road_texture = make_road_texture(road_texture_path)
    road_material = trimesh.visual.material.PBRMaterial(
        name="ManilaAsphalt",
        baseColorTexture=road_texture,
        metallicFactor=0.0,
        roughnessFactor=0.96,
    )
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
                road_kind = str(tags.get("highway", "residential")).lower()
                default_width = 10.5 if road_kind in ("primary", "trunk") else 8.0 if road_kind in ("secondary", "tertiary") else 6.0 if road_kind in ("residential", "unclassified") else 3.2
                try:
                    width = float(str(tags.get("width", default_width)).replace(" m", "").strip())
                    if width <= 0 or width > 40: width = default_width
                except (TypeError, ValueError):
                    width = default_width
                road = line.buffer(width/2, cap_style="flat", join_style="mitre")
                if road.is_empty: continue
                mesh = trimesh.creation.extrude_polygon(road, 0.12)
                vertices = mesh.vertices
                mesh.visual = trimesh.visual.TextureVisuals(
                    uv=np.column_stack((vertices[:, 0] / 4.0, vertices[:, 1] / 4.0)),
                    material=road_material,
                )
                scene.add_geometry(mesh, node_name=f"road_{road_count}")
                if road_kind in ("primary", "secondary", "tertiary", "trunk"):
                    try:
                        dash_len, gap_len = 5.0, 4.0
                        distance = 0.0
                        while distance < line.length:
                            a = line.interpolate(distance)
                            b = line.interpolate(min(distance + dash_len, line.length))
                            dash = LineString([(a.x, a.y), (b.x, b.y)]).buffer(0.075, cap_style="flat")
                            if not dash.is_empty:
                                mark = trimesh.creation.extrude_polygon(dash, 0.025)
                                mark.apply_translation([0, 0, 0.13])
                                mark.visual.face_colors = [205, 194, 145, 255]
                                scene.add_geometry(mark, node_name=f"road_mark_{road_count}_{int(distance)}")
                            distance += dash_len + gap_len
                    except Exception:
                        pass
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
    scene = compact_scene(scene)
    if len(scene.geometry) > 50:
        raise RuntimeError(f"Mesh compaction failed: {len(scene.geometry)} batches remain")
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
        "road_texture":road_texture_path.name,
        "note":"Real OSM footprints and road alignments; facade atlases and asphalt are procedural, and center markings are approximations. Exact facade appearance, road paint, curbs, signs, and street furniture require correctly geolocated imagery or verified mapped tags."
    }
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
def optimize_existing() -> None:
    """Compact the already committed GLB offline; avoid a redundant Overpass download."""
    if not OUT.exists():
        raise FileNotFoundError(f"Cannot optimize missing cached map: {OUT}")
    report_path = OUT.with_suffix(".json")
    if not report_path.exists():
        raise FileNotFoundError(f"Cannot optimize without map report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    original_scene = trimesh.load(str(OUT), force="scene")
    before = len(original_scene.geometry)
    compact = compact_scene(original_scene)
    if len(compact.geometry) > 50:
        raise RuntimeError(f"Offline compaction failed: {len(compact.geometry)} mesh batches remain")
    compact.export(str(OUT), file_type="glb")
    checked = trimesh.load(str(OUT), force="scene")
    if len(checked.geometry) < 2 or OUT.stat().st_size < 100_000:
        raise RuntimeError("Optimized cached Manila GLB failed structural/size validation")
    report["mesh_objects"] = len(checked.geometry)
    report["glb_bytes"] = OUT.stat().st_size
    report["optimization"] = {
        "mode": "offline cached-GLB compaction",
        "mesh_objects_before": before,
        "mesh_objects_after": len(checked.geometry),
    }
    report["note"] = str(report.get("note", "")) + " Existing OSM geometry was compacted offline; no network download was needed."
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if "--optimize-existing" in sys.argv:
        optimize_existing()
    else:
        main()
