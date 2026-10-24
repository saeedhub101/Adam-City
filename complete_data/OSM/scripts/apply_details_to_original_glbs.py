#!/usr/bin/env python3
"""Merge detail geometry and spatially split each building part into bounded GLBs."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[3]
PARTS=ROOT/"complete_data/OSM/data/buildings/Ermita"
GEN=ROOT/"complete_data/OSM/scripts/generate_roof_storefront_overlays.py"
LIMIT=78*1024*1024
HARD_LIMIT=95*1024*1024

def load_scene(path):
    obj=trimesh.load(path,force="scene",process=False)
    if not isinstance(obj,trimesh.Scene) or not obj.geometry:
        raise RuntimeError(f"Invalid/empty GLB scene: {path}")
    return obj

def export_bytes(scene):
    data=scene.export(file_type="glb")
    if not isinstance(data,(bytes,bytearray)): raise RuntimeError("GLB exporter did not return bytes")
    return bytes(data)

def world_meshes(scene,prefix):
    meshes=[]
    for node in list(scene.graph.nodes_geometry):
        transform,geom_name=scene.graph.get(node)
        geom=scene.geometry[geom_name].copy()
        geom.apply_transform(transform)
        if isinstance(geom,trimesh.Trimesh) and len(geom.faces):
            meshes.append((f"{prefix}_{node}",geom))
    return meshes

def submesh_faces(mesh,face_ids):
    if len(face_ids)==0: return None
    # trimesh submesh preserves per-face material/UV visuals when supported.
    try:
        result=mesh.submesh([face_ids],append=True,repair=False)
        if isinstance(result,list): result=result[0] if result else None
        if isinstance(result,trimesh.Trimesh) and len(result.faces): return result
    except Exception:
        pass
    return trimesh.Trimesh(vertices=mesh.vertices.copy(),faces=mesh.faces[face_ids].copy(),
                           visual=mesh.visual,process=False)

def pack_region(meshes,region_id):
    scene=trimesh.Scene()
    for idx,(name,mesh) in enumerate(meshes):
        scene.add_geometry(mesh,node_name=f"{name}_{region_id}_{idx}")
    return export_bytes(scene)

def spatial_split(meshes,part):
    """Partition by triangle centroid in projected local X/Y; every source triangle goes once."""
    faces=[]
    for mesh_index,(name,mesh) in enumerate(meshes):
        tri=mesh.triangles_center
        for face_index,center in enumerate(tri):
            faces.append((float(center[0]),float(center[1]),mesh_index,face_index))
    if not faces: raise RuntimeError(f"Part {part} has no triangles")
    pending=[faces]; regions=[]
    while pending:
        group=pending.pop(0)
        grouped={}
        for _,_,mi,fi in group: grouped.setdefault(mi,[]).append(fi)
        meshes_for_region=[]
        for mi,face_ids in grouped.items():
            sub=submesh_faces(meshes[mi][1],np.asarray(face_ids,dtype=np.int64))
            if sub is not None: meshes_for_region.append((meshes[mi][0],sub))
        blob=pack_region(meshes_for_region,len(regions)+len(pending)+1)
        if len(blob)<=LIMIT:
            regions.append((group,meshes_for_region,blob)); continue
        if len(group)<2: raise RuntimeError(f"One triangle exceeds GLB size limit in part {part}")
        xs=np.fromiter((f[0] for f in group),dtype=float)
        ys=np.fromiter((f[1] for f in group),dtype=float)
        # Alternate north/south and east/west using the wider geographic spread.
        axis=1 if np.ptp(ys)>=np.ptp(xs) else 0
        values=ys if axis==1 else xs
        median=float(np.median(values))
        left=[f for f in group if (f[1] if axis==1 else f[0])<=median]
        right=[f for f in group if (f[1] if axis==1 else f[0])>median]
        if not left or not right:
            order=np.argsort(values); midpoint=len(order)//2
            left=[group[int(i)] for i in order[:midpoint]]
            right=[group[int(i)] for i in order[midpoint:]]
        pending.insert(0,right);pending.insert(0,left)
    return regions

def run(part):
    original=PARTS/f"Parts{part}.glb"
    overlay=PARTS/"enhanced"/f"part{part}-roof-storefront-details.glb"
    report_path=PARTS/"enhanced"/f"part{part}-integrated-report.json"
    manifest_path=PARTS/"enhanced"/f"part{part}-regions.json"
    if not original.is_file(): raise FileNotFoundError(original)
    # Resume only if report, all region files, and the first GLB validate.
    if report_path.is_file() and manifest_path.is_file():
        try:
            manifest=json.loads(manifest_path.read_text())
            paths=[PARTS/entry["file"] for entry in manifest["regions"]]
            if paths and all(p.is_file() and p.stat().st_size<HARD_LIMIT for p in paths):
                for p in paths: load_scene(p)
                print(f"part{part}: RESUME skip; validated spatial regions already exist")
                return
        except Exception: pass
    if not overlay.is_file():
        subprocess.run([sys.executable,str(GEN),"--part",str(part)],cwd=ROOT,check=True)
    base=load_scene(original); details=load_scene(overlay)
    meshes=world_meshes(base,f"building{part}")+world_meshes(details,f"detail{part}")
    # Existing window GLB is intentionally handled separately: spatial split must happen first.
    regions=spatial_split(meshes,part)
    if len(regions)<1: raise RuntimeError("Spatial partition returned no regions")
    outputs=[]
    # First geographic region replaces PartsN.glb only after every output validates.
    targets=[original]+[PARTS/f"Parts{part}-region-{i+1:02d}.glb" for i in range(1,len(regions))]
    for idx,((faces,region_meshes,blob),target) in enumerate(zip(regions,targets),1):
        if len(blob)>=HARD_LIMIT: raise RuntimeError(f"Unsafe GLB size {len(blob)} for {target}")
        with tempfile.NamedTemporaryFile(dir=PARTS,suffix=".glb",delete=False) as tmp:
            tmp.write(blob);tmp_path=Path(tmp.name)
        try:
            chk=load_scene(tmp_path)
            if not chk.geometry: raise RuntimeError(f"Empty validation result: {target}")
        finally: tmp_path.unlink(missing_ok=True)
        outputs.append((target,blob,region_meshes))
    # Atomic writes after all regions have passed validation.
    for target,blob,_ in outputs:
        tmp=target.with_suffix(target.suffix+".tmp");tmp.write_bytes(blob);os.replace(tmp,target)
    # Remove stale region chunks from an earlier attempt only after successful replacement.
    keep={p.name for p,_,_ in outputs}
    for stale in PARTS.glob(f"Parts{part}-region-*.glb"):
        if stale.name not in keep: stale.unlink()
    manifest={"part":part,"split_axis":"geographic triangle-centroid partitions (alternating north/south and east/west)",
      "source_triangle_count":sum(len(m.faces) for _,m in meshes),
      "regions":[{"file":str(target.relative_to(PARTS)),"bytes":len(blob),
        "meshes":len(load_scene(target).geometry),
        "triangle_count":sum(len(m.faces) for _,m in region_meshes),
        "bounds_local_m":{"min_x":float(min(m.bounds[0,0] for _,m in region_meshes)),
          "max_x":float(max(m.bounds[1,0] for _,m in region_meshes)),
          "min_y":float(min(m.bounds[0,1] for _,m in region_meshes)),
          "max_y":float(max(m.bounds[1,1] for _,m in region_meshes))}}
        for target,blob,region_meshes in outputs]}
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    report={"part":part,"regions_manifest":str(manifest_path.relative_to(ROOT)),
      "original_file_now_contains_region_1":str(original.relative_to(ROOT)),
      "source_triangle_count":manifest["source_triangle_count"],
      "output_regions":[{"file":str(p.relative_to(ROOT)),"bytes":len(b)} for p,b,_ in outputs],
      "details_integrated":str(overlay.relative_to(ROOT)),
      "windows":"not yet integrated; requires separate spatial partition pass"}
    report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--part",type=int,choices=[1,2,3,4],required=True)
    run(ap.parse_args().part)
