#!/usr/bin/env python3
"""Create two individual building GLBs with a detailed Amman limestone texture.

The source GLB is a mapped-data model, not a photogrammetric scan. This script
preserves each selected building's source geometry and position, adds a generated
limestone-block albedo texture, and exports each building with its associated
roof/windows meshes. The texture is a realistic procedural material, not a
photograph of the exact property.
"""
import bpy, os, re, random, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "middle east/BuildGLB/amman/amman_3590_3200.glb"
OUT = ROOT / "middle east/BuildGLB/amman/realistic/buildings"
OUT.mkdir(parents=True, exist_ok=True)
TEX = OUT / "amman_limestone_albedo.png"
REPORT = OUT / "README.md"

def make_stone_texture(path, size=1024, seed=3200):
    """Create a seamless-looking limestone block albedo texture using Blender pixels."""
    random.seed(seed)
    # Stone blocks: slightly irregular horizontal courses and alternating vertical joints.
    course_h = 86
    joints = []
    y = 0
    while y < size:
        h = course_h + random.randint(-8, 8)
        offset = random.randint(-70, 70)
        joints.append((y, h, offset))
        y += h
    pixels = [0.0] * (size * size * 4)
    for py in range(size):
        course = next((c for c in reversed(joints) if c[0] <= py), joints[0])
        y0, h, offset = course
        local_y = py - y0
        block_w = 176
        for px in range(size):
            xx = (px + offset) % block_w
            # Fine grain plus subtle broad color variation.
            mortar = (local_y < 3 or xx < 3)
            grain = random.random() - 0.5
            broad = math.sin(px * 0.017 + py * 0.009) * 0.018 + math.sin(py * 0.043) * 0.009
            if mortar:
                rgb = (0.43, 0.395, 0.34)
            else:
                shade = random.uniform(-0.035, 0.035) + broad + grain * 0.025
                rgb = (0.72 + shade, 0.655 + shade, 0.535 + shade * 0.85)
                # Very subtle natural pores / flecks.
                if random.random() < 0.003:
                    rgb = (rgb[0] - 0.08, rgb[1] - 0.075, rgb[2] - 0.06)
            i = (py * size + px) * 4
            pixels[i:i+4] = [max(0, min(1, c)) for c in (*rgb, 1.0)]
    image = bpy.data.images.new("Amman Limestone Photorealistic-Style Albedo", width=size, height=size, alpha=False)
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image

def id_for(name):
    m = re.match(r"Building_(.+?)(?:\.\d+)?$", name)
    return m.group(1) if m else None

def matching_objects(building_id):
    # Blender may append .001 to duplicated object names; match stable name prefixes.
    prefixes = (f"Building_{building_id}", f"Roof_{building_id}",
                f"Facade windows {building_id}", f"Roof access hut {building_id}")
    return [o for o in bpy.context.scene.objects
            if any(o.name == p or o.name.startswith(p + ".") for p in prefixes)]

def assign_texture(obj, image):
    mat = bpy.data.materials.new("Amman limestone — textured stone blocks")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    tex.label = "Generated limestone block albedo"
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.86
    bsdf.inputs["Metallic"].default_value = 0.0
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    # Project the stone texture across the wall faces without moving geometry.
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.015)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)

def main():
    raise RuntimeError(
        "Refusing to export fabricated 'realistic' buildings: this script generates a "
        "procedural limestone texture, not a photograph of the selected buildings. "
        "Use middle east/UnityGame/tools/audit_local_photo_building_matches.py to find "
        "repository-local photo candidates; only add a photo texture after the exact "
        "building and facade orientation have been verified."
    )
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source GLB not found: {SOURCE}")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    candidates = sorted([o for o in bpy.context.scene.objects if o.type == "MESH" and id_for(o.name)],
                        key=lambda o: o.name)
    if len(candidates) < 2:
        raise RuntimeError(f"Expected at least two building meshes, found {len(candidates)}")
    image = make_stone_texture(TEX)
    chosen = candidates[:2]
    report = [
        "# Two individually textured buildings — tile amman_3590_3200",
        "",
        "These are isolated building exports, not street-tile exports. Source coordinates and mesh geometry are preserved.",
        "",
        "**Texture provenance:** generated procedural Amman-style limestone block albedo; it is not a photo of these exact buildings. Exact-photo matching requires verified photographs of each building.",
        "",
        "## Outputs",
        ""
    ]
    for index, building in enumerate(chosen, 1):
        bid = id_for(building.name)
        group = matching_objects(bid)
        if not group:
            raise RuntimeError(f"No geometry group found for building id {bid}")
        assign_texture(building, image)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in group:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = building
        dest = OUT / f"tabarbour_building_{index}_{bid}_textured.glb"
        bpy.ops.export_scene.gltf(filepath=str(dest), export_format="GLB",
                                  use_selection=True, export_apply=False,
                                  export_image_format="AUTO")
        report.append(f"- `{dest.name}` — source object `{building.name}`; exported meshes: {len(group)}.")
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("TEXTURED_BUILDINGS_COMPLETE")
    print("\n".join(report))

if __name__ == "__main__":
    main()
