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
    """Partition triangle-centroids geographically using compact NumPy arrays."""
    cx=[];cy=[];mi_all=[];fi_all=[]
    for mesh_index,(_,mesh) in enumerate(meshes):
        centers=np.asarray(mesh.triangles_center)
        if not len(centers): continue
        cx.append(centers[:,0]);cy.append(centers[:,1])
        mi_all.append(np.full(len(centers),mesh_index,dtype=np.int32))
        fi_all.append(np.arange(len(centers),dtype=np.int32))
    if not cx: raise RuntimeError(f"Part {part} has no triangles")
    xs=np.concatenate(cx);ys=np.concatenate(cy);mis=np.concatenate(mi_all);fis=np.concatenate(fi_all)
    pending=[np.arange(len(xs),dtype=np.int32)];regions=[]
    while pending:
        ids=pending.pop(0)
        unique_meshes=np.unique(mis[ids])
        meshes_for_region=[]
        for mesh_index in unique_meshes:
            selected=ids[mis[ids]==mesh_index]
            sub=submesh_faces(meshes[int(mesh_index)][1],fis[selected].astype(np.int64,copy=False))
            if sub is not None: meshes_for_region.append((meshes[int(mesh_index)][0],sub))
        blob=pack_region(meshes_for_region,len(regions)+len(pending)+1)
        if len(blob)<=LIMIT:
            regions.append((ids,meshes_for_region,blob));continue
        if len(ids)<2: raise RuntimeError(f"One triangle exceeds GLB size limit in part {part}")
        xspan=float(xs[ids].max()-xs[ids].min());yspan=float(ys[ids].max()-ys[ids].min())
        axis=ys if yspan>=xspan else xs
        values=axis[ids];median=float(np.median(values))
        left=ids[values<=median];right=ids[values>median]
        if not len(left) or not len(right):
            order=np.argsort(values);mid=len(order)//2
            left=ids[order[:mid]];right=ids[order[mid:]]
        # Each triangle index is placed in exactly one region; split axis follows local north/south
        # or east/west extent and recursively subdivides until every GLB is safely below 78 MiB.
        pending.insert(0,right);pending.insert(0,left)
    total=sum(len(region[0]) for region in regions)
    if total!=len(xs): raise RuntimeError(f"Spatial split lost triangles: {total} != {len(xs)}")
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
