#!/usr/bin/env python3
"""Blender batch exporter: Amman tiled GLBs from the repository's Jordan OSM GeoJSON only.
Run with: blender -b --python tools/build_amman_glb.py -- --data Jordan/layers --out BuildGLB/Amman
"""
import bpy, sys, gzip, json, math, os, subprocess, traceback
from pathlib import Path
from collections import defaultdict

def args():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    d={"data":"../Jordan/layers","out":"../BuildGLB/Amman","west":35.72,"east":36.08,"south":31.70,"north":32.12,"tile":0.01,"city":"Amman","prefix":"amman","repo_commit":True}
    for i in range(0,len(a),2):
        k=a[i].lstrip("-"); v=a[i+1]
        d[k]=float(v) if k in ("west","east","south","north","tile") else v
    return d

def read(path):
    with gzip.open(path,"rt",encoding="utf-8") as f:return json.load(f).get("features",[])
def tag(p,*keys):
    for k in keys:
        v=p.get(k)
        if v not in (None,"","no"):return str(v)
    return ""
def height(p):
    try:
        h=float(tag(p,"height","building:height").lower().replace("meters","").replace("m","").strip())
    except: h=0
    if h<=0:
        try:h=float(tag(p,"building:levels","levels"))*3.1
        except:h=0
    return max(3.2,min(h or 7.5,180))
def xy(lon,lat,lon0,lat0):
    return ((lon-lon0)*111319.490793*math.cos(math.radians(lat0)),(lat-lat0)*111319.490793)
def mat(name,color,rough=0.8,metal=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    if bs: bs.inputs["Base Color"].default_value=(*color,1);bs.inputs["Roughness"].default_value=rough;bs.inputs["Metallic"].default_value=metal
    return m
def mesh_obj(name,verts,faces,material):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(material);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
def polygon_area(poly):
    return sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2
def inside(p,a,b,c):
    def cr(u,v,w):return (v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0])
    x,y,z=cr(a,b,p),cr(b,c,p),cr(c,a,p)
    return (x>=0 and y>=0 and z>=0) or (x<=0 and y<=0 and z<=0)
def triangulate(poly):
    ids=list(range(len(poly)));out=[];sign=1 if polygon_area(poly)>0 else -1;guard=0
    while len(ids)>2 and guard<len(poly)*len(poly):
        guard+=1;cut=False
        for j in range(len(ids)):
            a,b,c=ids[j-1],ids[j],ids[(j+1)%len(ids)]
            cross=(poly[b][0]-poly[a][0])*(poly[c][1]-poly[b][1])-(poly[b][1]-poly[a][1])*(poly[c][0]-poly[b][0])
            if cross*sign<=1e-8:continue
            if any(inside(poly[k],poly[a],poly[b],poly[c]) for k in ids if k not in (a,b,c)):continue
            out.append((a,b,c));ids.pop(j);cut=True;break
        if not cut:break
    return out
def add_text(body,name,loc,size,material,rotation=(0,0,0)):
    cu=bpy.data.curves.new(name,"FONT");cu.body=body;cu.size=size;cu.extrude=0
    ob=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=rotation;cu.materials.append(material);return ob
def add_building(item,origin,wallm,roofm,glassm,trim,signm):
    ring=item["ring"][:-1] if len(item["ring"])>3 and item["ring"][0]==item["ring"][-1] else item["ring"]
    if len(ring)<3:return
    pts=[xy(p[0],p[1],*origin) for p in ring];h=item["height"];n=len(pts)
    if n>300:return
    tri=triangulate(pts)
    if not tri:return
    verts=[(x,0,z) for x,z in pts]+[(x,h,z) for x,z in pts]
    faces=[]
    for a,b,c in tri:faces.extend([(a,c,b),(n+a,n+b,n+c)])
    for i in range(n):j=(i+1)%n;faces.append((i,j,n+j,n+i))
    ob=mesh_obj("Building_"+str(item["id"]),verts,faces,wallm)
    ob["osm_id"]=str(item["id"]);ob["building_name"]=item["name"];ob["height_m"]=h
    # Roof cap with small parapet lip on flat roofs.
    roof=mesh_obj("Roof_"+str(item["id"]),[(x,h,z) for x,z in pts],[tuple(t) for t in tri],roofm)
    # Batch all facade windows into one mesh per building to keep city exports scalable.
    floors=max(1,min(50,round(h/3.1)));window_h=min(1.25,max(.65,h/(floors+1)*.48))
    winverts=[];winfaces=[]
    for i in range(n):
        a=pts[i];b=pts[(i+1)%n];dx=b[0]-a[0];dz=b[1]-a[1];length=math.hypot(dx,dz)
        if length<3 or length>100:continue
        count=min(24,max(1,int(length/3.0)));nx=-dz/(length or 1)*.055;nz=dx/(length or 1)*.055
        for floor in range(floors):
            y=1.0+floor*min(3.1,h/floors)
            if y+window_h>h-.35:continue
            for k in range(count):
                t=(k+.5)/count;cx=a[0]+dx*t;cz=a[1]+dz*t
                ww=min(1.35,length/count*.48);base=len(winverts)
                winverts.extend([(cx-dx/length*ww/2+nx,y,cz-dz/length*ww/2+nz),(cx+dx/length*ww/2+nx,y,cz+dz/length*ww/2+nz),(cx+dx/length*ww/2+nx,y+window_h,cz+dz/length*ww/2+nz),(cx-dx/length*ww/2+nx,y+window_h,cz-dz/length*ww/2+nz)])
                winfaces.append((base,base+1,base+2,base+3))
    if winfaces:mesh_obj("Facade windows "+str(item["id"]),winverts,winfaces,glassm)
    # Roof access hut / service block and low parapet give flat roofs a more believable silhouette.
    if h>=6:
        cx=sum(p[0] for p in pts)/n;cz=sum(p[1] for p in pts)/n
        rw=min(2.4,max(.8,(max(p[0] for p in pts)-min(p[0] for p in pts))*.22))
        rd=min(2.4,max(.8,(max(p[1] for p in pts)-min(p[1] for p in pts))*.22))
        rv=[(cx-rw/2,h,cz-rd/2),(cx+rw/2,h,cz-rd/2),(cx+rw/2,h,cz+rd/2),(cx-rw/2,h,cz+rd/2),(cx-rw/2,h+1.2,cz-rd/2),(cx+rw/2,h+1.2,cz-rd/2),(cx+rw/2,h+1.2,cz+rd/2),(cx-rw/2,h+1.2,cz+rd/2)]
        mesh_obj("Roof access hut "+str(item["id"]),rv,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],roofm)
    # Address/building number marker on first edge, facing outward.
    number=tag(item.get("properties",{}),"addr:housenumber","ref") if item.get("properties") else ""
    if not number:number=str(item.get("number",""))
    if number:
        p=pts[0];add_text(number,"Building number "+number,(p[0],2,p[1]),.8,trim)
    name=item.get("name","")
    if name:
        p=pts[0];add_text(name,"Building sign "+name,(p[0],min(3,h*.55),p[1]),.55,signm)

def road_mesh(line,origin,width,material,name):
    pts=[xy(p[0],p[1],*origin) for p in line]
    verts=[];faces=[]
    for i,(x,z) in enumerate(pts):
        if i==0:dx,dz=pts[1][0]-x,pts[1][1]-z
        elif i==len(pts)-1:dx,dz=x-pts[i-1][0],z-pts[i-1][1]
        else:dx,dz=pts[i+1][0]-pts[i-1][0],pts[i+1][1]-pts[i-1][1]
        l=math.hypot(dx,dz) or 1;ox=-dz/l*width/2;oz=dx/l*width/2
        verts.extend([(x+ox,.015,z+oz),(x-ox,.015,z-oz)])
    for i in range(len(pts)-1):a=2*i;faces.append((a,a+1,a+3,a+2))
    return mesh_obj(name,verts,faces,material)
def main():
    cfg=args();data=Path(cfg["data"]).resolve();out=Path(cfg["out"]).resolve();out.mkdir(parents=True,exist_ok=True)
    west,east,south,north,tile=[cfg[k] for k in ("west","east","south","north","tile")]
    city=cfg.get("city","Amman");prefix=cfg.get("prefix",city.lower().replace(" ","-"))
    origin=( (west+east)/2,(south+north)/2 )
    buildings=read(data/"buildings.geojson.gz");streets=read(data/"streets.geojson.gz");names=read(data/"streetnames.geojson.gz") if (data/"streetnames.geojson.gz").exists() else []
    tiles=defaultdict(lambda:{"buildings":[],"streets":[],"labels":[]})
    def key(lon,lat):return (math.floor(lon/tile),math.floor(lat/tile))
    for f in buildings:
        p=f.get("properties") or {};g=f.get("geometry") or {};c=g.get("coordinates") or []
        polys=c if g.get("type")=="MultiPolygon" else [c] if g.get("type")=="Polygon" else []
        for poly in polys:
            if not poly or not poly[0]:continue
            ring=[[q[0],q[1]] for q in poly[0] if len(q)>1]
            if len(ring)<4:continue
            lon=sum(q[0] for q in ring)/len(ring);lat=sum(q[1] for q in ring)/len(ring)
            if not(west<=lon<=east and south<=lat<=north):continue
            h=height(p);tiles[key(lon,lat)]["buildings"].append({"id":f.get("id",""),"name":tag(p,"name","name:en"),"height":h,"ring":ring,"properties":p})
    for f in streets:
        p=f.get("properties") or {};g=f.get("geometry") or {};c=g.get("coordinates") or []
        lines=[c] if g.get("type")=="LineString" else c if g.get("type")=="MultiLineString" else []
        for line in lines:
            if len(line)<2:continue
            lon=sum(q[0] for q in line)/len(line);lat=sum(q[1] for q in line)/len(line)
            if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)]["streets"].append({"line":line,"name":tag(p,"name","name:en","ref"),"highway":tag(p,"highway")})
    for f in names:
        p=f.get("properties") or {};g=f.get("geometry") or {};c=g.get("coordinates") or []
        if g.get("type")=="Point" and len(c)>=2 and west<=c[0]<=east and south<=c[1]<=north:
            tiles[key(c[0],c[1])]["labels"].append({"name":tag(p,"name","name:en"),"point":c})
    walls=mat("Amman limestone facade",(.72,.65,.52));roofm=mat("Concrete and stone roofs",(.48,.43,.36));glass=mat("Blue grey window glass",(.22,.38,.46),.24,.18);trim=mat("Facade trim",(.88,.82,.68));signm=mat("Shop sign backing",(.12,.20,.16),.65)
    asphalt=mat("Asphalt",(.16,.16,.15));residential=mat("Residential road",(.27,.26,.24))
    manifest={"city":city,"bounds":{"west":west,"east":east,"south":south,"north":north},"tile_degrees":tile,"tiles":[],"counts":{"buildings":0,"streets":0,"street_labels":0}}
    for (tx,ty),items in sorted(tiles.items()):
        filename=f"{prefix}_{tx}_{ty}.glb";target=out/filename
        if target.exists() and target.stat().st_size>1024: print("RESUME_SKIP_EXISTING",target);continue
        try:
            bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
            bpy.context.scene.unit_settings.system="METRIC"
            for b in items["buildings"]:add_building(b,origin,walls,roofm,glass,trim,signm)
            for s in items["streets"]:
                hw=s["highway"].lower();w=12 if hw in ("motorway","trunk") else 8 if hw in ("primary","secondary") else 5 if hw=="tertiary" else 3.2 if hw in ("residential","unclassified") else 1.3
                road_mesh(s["line"],origin,w,asphalt if w>2 else residential,"Road "+s["name"])
                if s["name"]:
                    p=s["line"][len(s["line"])//2];x,z=xy(p[0],p[1],*origin)
                    add_text(s["name"],"Street name "+s["name"],(x,.12,z),2.2,trim)
            for lab in items["labels"]:
                x,z=xy(lab["point"][0],lab["point"][1],*origin);add_text(lab["name"],"Street label "+lab["name"],(x,.15,z),2,trim)
            bpy.ops.export_scene.gltf(filepath=str(target),export_format="GLB",use_selection=False,export_apply=True)
            manifest["tiles"].append({"tile":f"{tx}_{ty}","file":filename,"buildings":len(items["buildings"]),"streets":len(items["streets"]),"labels":len(items["labels"]),"bytes":target.stat().st_size})
            manifest["counts"]["buildings"]+=len(items["buildings"]);manifest["counts"]["streets"]+=len(items["streets"]);manifest["counts"]["street_labels"]+=len(items["labels"])
            print("EXPORTED",target,len(items["buildings"]),len(items["streets"]))
            (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
            if cfg.get("repo_commit",True):
                try:
                    repo_root=Path(os.environ.get("GITHUB_WORKSPACE", subprocess.check_output(["git","rev-parse","--show-toplevel"],cwd=Path(__file__).resolve().parents[4],text=True).strip())).resolve()
                    rel=target.resolve().relative_to(repo_root)
                    subprocess.run(["git","add","--",str(rel),str((out/"manifest.json").resolve().relative_to(repo_root.resolve()))],cwd=repo_root,check=True)
                    subprocess.run(["git","-c","user.name=github-actions[bot]","-c","user.email=41898282+github-actions[bot]@users.noreply.github.com","commit","-m",f"Add generated {city} GLB tile {tx}_{ty}"],cwd=repo_root,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    subprocess.run(["git","push","origin","HEAD:main"],cwd=repo_root,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    print("CHECKPOINT_PUSHED",rel)
                except Exception as e: print("CHECKPOINT_PUSH_FAILED",repr(e))
        except Exception as e:
            print("TILE_FAILED_CONTINUING",city,tx,ty,repr(e));traceback.print_exc()
            try: (out/"failures.jsonl").open("a",encoding="utf-8").write(json.dumps({"city":city,"tile":f"{tx}_{ty}","error":repr(e)})+"\\n")
            except Exception: pass

    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print(city+" GLB COMPLETE",json.dumps(manifest["counts"]))
if __name__=="__main__":main()
