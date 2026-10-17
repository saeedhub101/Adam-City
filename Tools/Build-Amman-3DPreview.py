#!/usr/bin/env python3
"""Generate a detailed central-Manila GLB and preview from real OSM footprints."""
import bpy, json, math, sys, hashlib, struct
from pathlib import Path
from mathutils import Vector

def getargs():
    a=sys.argv[sys.argv.index("--")+1:]
    if len(a)!=3: raise SystemExit("Usage: -- input.geojson output.glb preview.png")
    return [Path(x) for x in a]
def material(n,c,r=.8):
    m=bpy.data.materials.new(n); m.diffuse_color=(*c,1); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(*c,1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=r
    return m
def xy(c,lon0,lat0,cx,cy):
    return ((c[0]-lon0)*111320*math.cos(math.radians(lat0))-cx,(c[1]-lat0)*111132-cy)
def meshobj(name,v,f,mats,ids=None):
    if not v or not f: return
    me=bpy.data.meshes.new(name); me.from_pydata(v,[],f); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
    for m in mats: me.materials.append(m)
    if ids:
        for p,i in zip(me.polygons,ids): p.material_index=i
    return ob
def main():
    src,out,png=getargs(); d=json.loads(src.read_text(encoding="utf-8"))
    o=d.get("origin",{}); lon0=float(o.get("longitude",35.927)); lat0=float(o.get("latitude",31.952))
    coords=[]
    def walk(c):
        if isinstance(c,list) and c and isinstance(c[0],(int,float)) and len(c)>1: coords.append(c)
        elif isinstance(c,list):
            for x in c: walk(x)
    for f in d["features"]: walk((f.get("geometry") or {}).get("coordinates",[]))
    if not coords: raise SystemExit("No usable coordinates")
    raw=[((c[0]-lon0)*111320*math.cos(math.radians(lat0)),(c[1]-lat0)*111132) for c in coords]
    cx=(min(x for x,y in raw)+max(x for x,y in raw))/2; cy=(min(y for x,y in raw)+max(y for x,y in raw))/2
    def local(c): return xy(c,lon0,lat0,cx,cy)
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    facades=[material("Weathered tropical concrete",(.55,.54,.49)),material("Sun-faded plaster",(.72,.68,.58)),material("Aged painted concrete",(.48,.52,.49)),material("Light concrete",(.68,.67,.60)),material("Weathered masonry",(.39,.38,.34))]
    glass=material("Smoky blue-grey window glass",(.055,.13,.17),.22); frame=material("Dark metal window frames",(.16,.17,.16),.48)
    roofmat=material("Weathered flat roof concrete",(.36,.35,.31)); asphalt=material("Worn tropical asphalt",(.085,.09,.09),.96)
    groundmat=material("Manila urban ground",(.30,.30,.27),1)
    span=760.0
    bpy.ops.mesh.primitive_plane_add(size=span,location=(0,0,-.12)); bpy.context.object.name="Amman terrain base"; bpy.context.object.data.materials.append(groundmat)
    bv=[]; bf=[]; bi=[]; wv=[]; wf=[]; wi=[]; rv=[]; rf=[]
    nbuilding=nroad=nwindow=0
    for f in d["features"]:
        p=f.get("properties") or {}; g=f.get("geometry") or {}
        if p.get("kind")!="building" or g.get("type")!="Polygon": continue
        rings=g.get("coordinates") or []
        if not rings or len(rings[0])<4: continue
        poly=[local(c) for c in rings[0]]
        # Keep the dense central district within the playable arena; retain smaller informal and residential structures.
        if not poly or math.hypot(sum(x for x,y in poly)/len(poly),sum(y for x,y in poly)/len(poly)) > 378: continue
        if len(poly)>1 and math.dist(poly[0],poly[-1])<.03: poly=poly[:-1]
        if len(poly)<3: continue
        area=abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2)
        if area<3: continue
        try: floors=max(1,min(16,int(float(p.get("building:levels","")))))
        except: floors=2+int(hashlib.md5(str(p.get("osm_id","")).encode()).hexdigest()[:2],16)%4
        try: h=max(floors*2.65,min(55,float(str(p.get("height","")).replace(" m",""))))
        except: h=floors*2.85
        n=len(poly); base=len(bv); shade=int(hashlib.md5(str(p.get("osm_id","")).encode()).hexdigest()[:2],16)%len(facades)
        bv.extend([(x,y,0) for x,y in poly]); bv.extend([(x,y,h) for x,y in poly])
        for i in range(n): bf.append((base+i,base+(i+1)%n,base+n+(i+1)%n,base+n+i)); bi.append(shade)
        bf.append(tuple(base+n+i for i in range(n))); bi.append(5); nbuilding+=1
        for i in range(n):
            x1,y1=poly[i]; x2,y2=poly[(i+1)%n]; length=math.hypot(x2-x1,y2-y1)
            if length<5: continue
            ux=(x2-x1)/length; uy=(y2-y1)/length; nx=uy; ny=-ux; count=max(1,min(5,int(length//8.0)))
            floorh=h/floors
            for fl in range(0, floors, 2):
                z0=fl*floorh+floorh*.24; z1=fl*floorh+floorh*.70
                if z1-z0<.45: continue
                for j in range(count):
                    mid=(j+.5)*length/count; half=min(.65,length/count*.22); idx=len(wv)
                    for dist,z in [(mid-half,z0),(mid+half,z0),(mid+half,z1),(mid-half,z1)]:
                        wv.append((x1+ux*dist+nx*.035,y1+uy*dist+ny*.035,z))
                    wf.append((idx,idx+1,idx+2,idx+3)); wi.append(0); nwindow+=1

    widths={"motorway":12,"trunk":10,"primary":8,"secondary":7,"tertiary":6,"residential":5,"service":3.5,"footway":1.8,"path":1.5}
    for f in d["features"]:
        p=f.get("properties") or {}; g=f.get("geometry") or {}
        if p.get("kind")!="road" or g.get("type")!="LineString": continue
        pts=[local(c) for c in (g.get("coordinates") or [])]
        if len(pts)<2: continue
        width=widths.get(p.get("highway",""),4.2)
        for i in range(len(pts)-1):
            x1,y1=pts[i]; x2,y2=pts[i+1]; dx=x2-x1; dy=y2-y1; L=math.hypot(dx,dy)
            if L<.8 or math.hypot((x1+x2)*.5,(y1+y2)*.5)>380: continue
            nx=-dy/L*width/2; ny=dx/L*width/2; k=len(rv)
            rv.extend([(x1+nx,y1+ny,.01),(x1-nx,y1-ny,.01),(x2-nx,y2-ny,.01),(x2+nx,y2+ny,.01)])
            rf.append((k,k+1,k+2,k+3))
        nroad+=1
    meshobj("Real OSM building footprints with facade detail",bv,bf,facades+[roofmat],bi)
    meshobj("Facade window glass and frames",wv,wf,[glass,frame],wi)
    meshobj("Road ribbons from OSM centerlines",rv,rf,[asphalt])
    bpy.ops.object.light_add(type="SUN",location=(0,0,span*.8)); sun=bpy.context.object
    sun.data.energy=2.0; sun.rotation_euler=(math.radians(25),math.radians(-20),math.radians(-25))
    bpy.ops.object.light_add(type="AREA",location=(-span*.25,-span*.25,span*.55)); fill=bpy.context.object
    fill.data.energy=span*span*.015; fill.data.shape="DISK"; fill.data.size=span*.5
    # Frame the district from its actual center and building height range.
    zmax=max((v[2] for v in bv),default=30.0)
    target=Vector((0.0,0.0,zmax*.30))
    camloc=Vector((span*.62,-span*.78,max(span*.50,zmax*1.25)))
    bpy.ops.object.camera_add(location=camloc); cam=bpy.context.object
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type="ORTHO"; cam.data.ortho_scale=span*1.05
    # The whole Amman extract can span several kilometres; Blender defaults to a 1 km far clip,
    # which silently clipped the entire scene in headless renders. Scale clipping to the real scene.
    cam.data.clip_start=0.1; cam.data.clip_end=max(10000.0,span*4.0,zmax*4.0+cam.location.length)
    scene=bpy.context.scene; scene.camera=cam
    # Workbench is stable on headless runners; configure studio light and contrast.
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.studiolight_rotate_z=0.5
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="BOTH"
    scene.display.shading.curvature_ridge_factor=1.25
    scene.display.shading.curvature_valley_factor=1.0
    scene.display.shading.background_type="WORLD"
    scene.display.shading.background_color=(0.035,0.045,0.06)
    scene.render.resolution_x=1440; scene.render.resolution_y=900; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"; scene.render.filepath=str(png)
    scene.world.color=(.12,.12,.12)
    if bpy.app.version >= (4,0,0): scene.view_settings.view_transform="AgX"
    out.parent.mkdir(parents=True,exist_ok=True); png.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(out),export_format="GLB",export_apply=True,export_yup=True,export_materials="EXPORT")
    bpy.ops.render.render(write_still=True)
    # Separate zoomed view for reviewing facade and street-block detail.
    closeup=png.with_name(png.stem+"-Closeup"+png.suffix)
    cam.data.ortho_scale=span*.24
    cam.location=Vector((span*.18,-span*.22,max(span*.20,zmax*.70)))
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(closeup)
    bpy.ops.render.render(write_still=True)
    print(json.dumps({"buildings":nbuilding,"road_ways":nroad,"windows":nwindow,"features":len(d["features"]),"glb":str(out),"preview":str(png),"closeup":str(closeup)}))
    if nbuilding<80 or nroad<50 or nwindow<500: raise SystemExit("Quality gate failed: not enough building/road/window geometry")
    if out.stat().st_size > 95_000_000: raise SystemExit(f"Runtime GLB exceeds GitHub file limit budget: {out.stat().st_size:,} bytes")
if __name__=="__main__": main()
