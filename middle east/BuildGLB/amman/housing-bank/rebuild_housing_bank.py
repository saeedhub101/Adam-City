#!/usr/bin/env python3
import bpy, math, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "middle east/BuildGLB/amman/amman_3590_3197_source.glb"
OUTPUT = ROOT / "middle east/BuildGLB/amman/amman_3590_3197.glb"
REPORT = ROOT / "middle east/BuildGLB/amman/housing-bank/REBUILD_REPORT.md"
LON0, LAT0 = 35.905, 31.975
LON, LAT = 35.907389, 31.971306
X = (LON-LON0)*111319.490793*math.cos(math.radians(LAT0))
Z = (LAT-LAT0)*111319.490793
HEIGHT = 98.0

def mat(name, color, rough=.75, metal=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*color,1); bs.inputs["Roughness"].default_value=rough; bs.inputs["Metallic"].default_value=metal
    return m

def box(name, loc, dims, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); o.data.materials.append(material)
    if bevel:
        mod=o.modifiers.new("Architectural edge bevel","BEVEL"); mod.width=bevel; mod.segments=2
        o.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
    o["reconstruction"]="Photo-referenced Housing Bank Complex"; return o

def build():
    concrete=mat("Housing Bank pale grey concrete",(.64,.65,.62),.82)
    edges=mat("Housing Bank projecting light slab edges",(.82,.82,.77),.74)
    glass=mat("Housing Bank dark ribbon glazing",(.045,.065,.072),.22,.12)
    shadow=mat("Housing Bank deep slab shadows",(.12,.14,.14),.65)
    stone=mat("Housing Bank podium stone",(.68,.65,.58),.84)
    metal=mat("Housing Bank roof equipment",(.43,.45,.44),.55,.18)
    box("HousingBank_Podium",(X,4,Z),(72,8,58),stone,.25)
    floors=21; fh=HEIGHT/floors
    for f in range(floors):
        y=8+f*fh; t=f/(floors-1); w=66-42*t; d=51-31*t
        box(f"HousingBank_F{f+1:02d}_GlassBand",(X,y+fh*.50,Z),(max(20,w-1.4),fh*.58,max(17,d-1.4)),glass,.06)
        box(f"HousingBank_F{f+1:02d}_ConcreteSpandrel",(X,y+fh*.18,Z),(max(21,w-1),fh*.20,max(18,d-1)),concrete,.05)
        box(f"HousingBank_F{f+1:02d}_ProjectingSlab",(X,y+fh*.88,Z),(w,.42,d),edges,.08)
        box(f"HousingBank_F{f+1:02d}_ShadowLine",(X,y+fh*.65,Z),(max(20,w-1.2),.09,max(17,d-1.2)),shadow)
        for j in range(1,8):
            xx=X-w/2+j*w/8
            box(f"HousingBank_F{f+1:02d}_Mullion_{j}",(xx,y+fh*.5,Z+d/2-.12),(.10,fh*.54,.12),metal)
    box("HousingBank_Rooftop_Crown",(X,8+HEIGHT+7.5,Z),(20,15,17),concrete,.2)
    box("HousingBank_Crown_Recess",(X,8+HEIGHT+8.5,Z+8.58),(7,4.2,.12),shadow)
    box("HousingBank_RoofServiceBlock",(X-3,8+HEIGHT+1.2,Z-2),(8,2.4,7),stone,.08)
    for i,(dx,dz,h) in enumerate([(-5,-3,4.5),(-1,-2,6.5),(3,1,5.5),(5,-1,3.5)]):
        box(f"HousingBank_AntennaBase_{i}",(X+dx,8+HEIGHT+15.1,Z+dz),(.45,.45,.45),metal)
        box(f"HousingBank_Antenna_{i}",(X+dx,8+HEIGHT+15.1+h/2,Z+dz),(.08,h,.08),metal)
    bpy.context.scene["target_building"]="Al-Iskan / Housing Bank Complex, Amman"
    bpy.context.scene["target_coordinates"]=f"{LAT},{LON}"
    bpy.context.scene["target_height_m"]=HEIGHT

def main():
    if not SOURCE.exists() or SOURCE.stat().st_size == 0:
        raise FileNotFoundError("Existing committed GLB tile was not copied to source path: "+str(SOURCE))
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    removed=[]
    from mathutils import Vector
    for o in list(bpy.context.scene.objects):
        if o.type!="MESH" or not (o.name.startswith("Building_") or o.name.startswith("Roof_") or o.name.startswith("Facade windows ") or o.name.startswith("Roof access hut ")): continue
        cs=[o.matrix_world @ Vector(c) for c in o.bound_box]
        cx=sum(v.x for v in cs)/8; cz=sum(v.z for v in cs)/8
        if math.hypot(cx-X,cz-Z)<=90:
            removed.append(o.name); bpy.data.objects.remove(o,do_unlink=True)
    if not removed:
        raise RuntimeError("No existing building mesh was identified near Housing Bank coordinates; refusing to export a duplicate tower or overwrite the original tile.")
    build()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT),export_format="GLB",use_selection=True,export_apply=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text("# Housing Bank Complex rebuild\n\nTarget coordinates: 31.971306, 35.907389\n\n"
      "Reconstructed 21-storey, 98 m stepped tower from published exterior photographs: projecting pale floor plates, dark continuous glazing bands, podium, crown and roof antennas. "
      "Non-target tile objects are preserved. This is a photo-referenced geometric reconstruction, not photogrammetry.\n\n"
      "Removed nearby source building meshes: "+", ".join(removed)+"\n",encoding="utf-8")
    print("HOUSING_BANK_REBUILD_COMPLETE",json.dumps(removed),str(OUTPUT))
if __name__=="__main__": main()
