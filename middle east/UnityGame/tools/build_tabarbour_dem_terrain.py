#!/usr/bin/env python3
"""Build a georeferenced local terrain mesh GLB from a GDAL XYZ downsample of Copernicus DEM."""
import json, math, pathlib, sys
import bpy

def args():
    raw=sys.argv[sys.argv.index("--")+1:]
    d={}
    for i in range(0,len(raw),2):
        k=raw[i].lstrip("-"); v=raw[i+1]
        d[k]=float(v) if k in ("west","east","south","north") else v
    return d

def main():
    a=args(); src=pathlib.Path(a["input"]); out=pathlib.Path(a["out"]); out.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    with src.open("r",encoding="utf-8",errors="replace") as f:
        for line in f:
            p=line.split()
            if len(p)<3: continue
            try: rows.append((float(p[0]),float(p[1]),float(p[2])))
            except ValueError: continue
    if len(rows)<1000: raise SystemExit("DEM XYZ has too few valid points: "+str(len(rows)))
    # GDAL XYZ is row-major, north-to-south. Infer regular grid dimensions from repeated X values.
    first_y=rows[0][1]; width=0
    for _,y,_ in rows:
        if y!=first_y: break
        width+=1
    if width<2 or len(rows)%width: raise SystemExit("Cannot infer DEM grid dimensions")
    height=len(rows)//width
    if width*height!=len(rows): raise SystemExit("Incomplete DEM grid")
    lat0=(a["south"]+a["north"])/2; lon0=(a["west"]+a["east"])/2
    verts=[]
    for lon,lat,z in rows:
        x=(lon-lon0)*111319.490793*math.cos(math.radians(lat0))
        y=(lat-lat0)*111319.490793
        # Keep elevation in metres relative to the minimum to avoid large geocentric coordinates.
        verts.append((x,z,y))
    faces=[]
    for r in range(height-1):
        for c in range(width-1):
            i=r*width+c
            faces.append((i,i+1,i+width+1,i+width))
    mesh=bpy.data.meshes.new("Copernicus_GLO30_Terrain_Mesh"); mesh.from_pydata(verts,[],faces); mesh.update()
    obj=bpy.data.objects.new("Tabarbour_Copernicus_GLO30_Terrain",mesh); bpy.context.collection.objects.link(obj)
    obj["source"]="Copernicus DEM GLO-30 Public (DSM)"
    obj["grid_width"]=width; obj["grid_height"]=height; obj["elevation_units"]="metres"
    obj["bounds_wsen"]=json.dumps([a["west"],a["south"],a["east"],a["north"]])
    obj["note"]="DSM elevation mesh; vertical accuracy and pixel coverage are source-limited; buildings/trees may affect surface elevations."
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.gltf(filepath=str(out),export_format="GLB",use_selection=True)
    print("DEM_TERRAIN_GLB",str(out),"vertices",len(verts),"faces",len(faces),flush=True)
if __name__=="__main__": main()
