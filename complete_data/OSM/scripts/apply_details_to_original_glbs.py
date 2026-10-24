#!/usr/bin/env python3
"""Apply generated roof/storefront geometry into the original PartsN.glb files.
If the merged GLB would approach GitHub's 100 MB file limit, split its scene into
PartsN.glb and PartsN-extra.glb while preserving world/local vertex positions.
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import trimesh

ROOT=Path(__file__).resolve().parents[3]
PARTS=ROOT/"complete_data/OSM/data/buildings/Ermita"
GEN=ROOT/"complete_data/OSM/scripts/generate_roof_storefront_overlays.py"
LIMIT=88*1024*1024
HARD_LIMIT=99*1024*1024

def load_scene(path):
    obj=trimesh.load(path,force="scene",process=False)
    if not isinstance(obj,trimesh.Scene) or not obj.geometry:
        raise RuntimeError(f"Invalid/empty GLB scene: {path}")
    return obj

def export_bytes(scene):
    data=scene.export(file_type="glb")
    if not isinstance(data,(bytes,bytearray)): raise RuntimeError("GLB exporter did not return bytes")
    return bytes(data)

def scene_world_geometries(scene):
    items=[]
    for node in list(scene.graph.nodes_geometry):
        transform, geom_name=scene.graph.get(node)
        geom=scene.geometry[geom_name].copy()
        geom.apply_transform(transform)
        items.append((str(node),geom))
    return items

def scene_from_items(items):
    result=trimesh.Scene()
    for i,(name,geom) in enumerate(items):
        result.add_geometry(geom,node_name=f"{name}_{i}")
    return result

def split_by_size(items, part):
    # Greedy binary split based on actual GLB byte size, not mesh count assumptions.
    pending=[items]; finished=[]
    while pending:
        group=pending.pop(0)
        data=export_bytes(scene_from_items(group))
        if len(data)<LIMIT:
            finished.append((group,data)); continue
        if len(group)<2:
            raise RuntimeError(f"Single geometry exceeds safe GLB size for part {part}")
        mid=len(group)//2
        pending.insert(0,group[mid:])
        pending.insert(0,group[:mid])
    return finished

def run(part):
    original=PARTS/f"Parts{part}.glb"
    overlay=PARTS/"enhanced"/f"part{part}-roof-storefront-details.glb"
    extra=PARTS/f"Parts{part}-extra.glb"
    if not original.is_file(): raise FileNotFoundError(original)
    if not overlay.is_file():
        subprocess.run([sys.executable,str(GEN),"--part",str(part)],cwd=ROOT,check=True)
    base=load_scene(original); details=load_scene(overlay)
    merged=trimesh.Scene()
    # Keep original node transforms and geometry, then add overlay nodes. No original vertex
    # positions are edited; export bakes scene graph transforms only when necessary.
    for node in list(base.graph.nodes_geometry):
        transform,geom_name=base.graph.get(node)
        merged.add_geometry(base.geometry[geom_name].copy(),node_name=f"original_{node}",transform=transform)
    for node in list(details.graph.nodes_geometry):
        transform,geom_name=details.graph.get(node)
        merged.add_geometry(details.geometry[geom_name].copy(),node_name=f"details_{node}",transform=transform)
    data=export_bytes(merged)
    outputs=[]
    if len(data)<LIMIT:
        outputs=[(original,data)]
        if extra.exists(): extra.unlink()
    else:
        items=scene_world_geometries(merged)
        groups=split_by_size(items,part)
        if len(groups)>2:
            raise RuntimeError(f"Part {part} needs {len(groups)} chunks; this workflow supports one extra chunk only")
        outputs.append((original,groups[0][1]))
        outputs.append((extra,groups[1][1]))
    # Validate all outputs before replacing any original in this part.
    for target,blob in outputs:
        if len(blob)>=HARD_LIMIT: raise RuntimeError(f"Refusing oversized GLB {target}: {len(blob)} bytes")
        with tempfile.NamedTemporaryFile(dir=target.parent,suffix=".glb.tmp",delete=False) as f:
            f.write(blob); temp=Path(f.name)
        try:
            chk=load_scene(temp)
            if not chk.geometry: raise RuntimeError(f"Validation found no meshes in {target}")
        finally:
            temp.unlink(missing_ok=True)
    # Atomic replacement after validation.
    for target,blob in outputs:
        temp=target.with_suffix(target.suffix+".tmp")
        temp.write_bytes(blob); os.replace(temp,target)
    report={"part":part,"original_file":str(original.relative_to(ROOT)),"merged_bytes":len(data),
            "outputs":[{"file":str(p.relative_to(ROOT)),"bytes":len(b),"meshes":len(load_scene(p).geometry)} for p,b in outputs],
            "integrated_overlay":str(overlay.relative_to(ROOT)),"policy":"details integrated into original GLB scene; coordinates retained"}
    report_path=PARTS/"enhanced"/f"part{part}-integrated-report.json"
    report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--part",type=int,choices=[1,2,3,4],required=True)
    run(ap.parse_args().part)
