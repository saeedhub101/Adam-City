#!/usr/bin/env python3
"""Blender batch exporter: Amman tiled GLBs from the repository's Jordan OSM GeoJSON only.
Run with: blender -b --python tools/build_amman_glb.py -- --data Jordan/layers --out BuildGLB/Amman
"""
import bpy, sys, gzip, json, math, os, subprocess, traceback
from pathlib import Path
from collections import defaultdict

def args():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    d={"data":"../Jordan/layers","out":"../BuildGLB/Amman","west":35.72,"east":36.08,"south":31.70,"north":32.12,"tile":0.01,"city":"Amman","prefix":"amman","repo_commit":True,"force":False,"infra_path":""}
    for i in range(0,len(a),2):
        k=a[i].lstrip("-"); v=a[i+1]
        d[k]=float(v) if k in ("west","east","south","north","tile") else (v.lower() in ("true","1","yes") if k in ("repo_commit","force") else v)
    return d

def read(path):
    with gzip.open(path,"rt",encoding="utf-8") as f:return json.load(f).get("features",[])
def tag(p,*keys):
    for k in keys:
        v=p.get(k)
        if v not in (None,"","no"):return str(v)
    return ""
def osm_identity(feature,properties):
    props=properties or {}
    value=props.get("@id")
    kind=props.get("@type") or props.get("type")
    if value not in (None,""):
        value=str(value)
        if "/" in value or not kind:return value
        return str(kind)+"/"+value
    value=feature.get("id") or props.get("osm_id") or props.get("way_id") or props.get("relation_id") or ""
    if value not in (None,"") and kind and "/" not in str(value):return str(kind)+"/"+str(value)
    return str(value)
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
def road_surface_material(properties,default):
    surface=tag(properties,"surface","tracktype").strip().lower()
    choices={
      "asphalt":((.16,.16,.15),.92),"concrete":((.48,.47,.44),.88),"paved":((.34,.34,.32),.88),
      "paving_stones":((.48,.43,.36),.9),"cobblestone":((.40,.37,.32),.95),
      "gravel":((.42,.39,.34),.98),"dirt":((.39,.31,.22),1.0),"earth":((.39,.31,.22),1.0),
      "ground":((.43,.36,.26),1.0),"unpaved":((.42,.36,.27),1.0),"sand":((.68,.56,.37),1.0)
    }
    if surface not in choices:return default
    color,rough=choices[surface]
    return mat("OSM road surface "+surface,color,rough)
def osm_material(p,role,fallback):
    raw=tag(p,role+":colour",role+":color").strip().lower()
    palette={"white":(0.88,0.85,0.78),"black":(0.12,0.12,0.11),"grey":(0.48,0.48,0.46),"gray":(0.48,0.48,0.46),
      "red":(0.62,0.16,0.12),"brown":(0.38,0.25,0.16),"beige":(0.72,0.64,0.48),"yellow":(0.78,0.64,0.32),
      "blue":(0.20,0.36,0.58),"green":(0.22,0.40,0.25),"sandstone":(0.70,0.57,0.39)}
    col=None
    if raw.startswith("#") and len(raw) in (4,7):
        try:
            h=raw[1:]
            if len(h)==3:h="".join(ch*2 for ch in h)
            col=tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
        except Exception:col=None
    if col is None:col=palette.get(raw)
    material=tag(p,role+":material",role+":surface").strip().lower()
    if col is None and material:
        if any(v in material for v in ("glass","metal","steel","aluminium")):col=(0.35,0.43,0.47)
        elif any(v in material for v in ("brick","clay","tile")):col=(0.48,0.27,0.18)
        elif any(v in material for v in ("concrete","cement")):col=(0.56,0.54,0.49)
        elif any(v in material for v in ("stone","limestone","sandstone")):col=(0.70,0.62,0.49)
    if col is None:return fallback
    rough=.28 if material and any(v in material for v in ("glass","metal","steel")) else .82
    metallic=.45 if material and any(v in material for v in ("metal","steel","aluminium")) else 0
    return mat("OSM "+role+" "+(material or raw),col,rough,metallic)
def flat_polygon(name,ring,origin,y,material):
    if len(ring)>1 and ring[0]==ring[-1]:ring=ring[:-1]
    if len(ring)<3:return None
    pts=[xy(p[0],p[1],*origin) for p in ring]
    tri=triangulate(pts)
    if not tri:return None
    verts=[(x,y,z) for x,z in pts]
    return mesh_obj(name,verts,tri,material)
def norm_photo_name(value):
    value=str(value or "").casefold()
    return " ".join("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in value).split())

def load_verified_photo_index():
    """Index downloaded, freely licensed photos only when the existing importer found an exact building-name phrase."""
    root=Path(__file__).resolve().parents[2]/"BuildGLB/tabarbour-real/photos"
    manifest=root/"wikimedia-photo-manifest.json"
    index={}
    if not manifest.is_file(): return index
    try: records=json.loads(manifest.read_text(encoding="utf-8")).get("items",[])
    except Exception as e:
        print("PHOTO_TEXTURE_MANIFEST_ERROR",repr(e)); return index
    for rec in records:
        if not rec.get("downloaded") or not rec.get("file"): continue
        lic=str(rec.get("license","")).strip().lower().replace("_"," ").replace("creative commons","cc")
        compact=lic.replace(" ","")
        if not (compact in ("cc0","publicdomain") or "public domain" in lic or compact.startswith(("ccby","ccby-sa","ccby-nc"))): continue
        if "nc" in compact or "nd" in compact: continue
        image_path=(Path.cwd()/rec["file"]).resolve()
        if not image_path.is_file(): continue
        # Require the importer’s name-phrase match and do not use nearby/unmatched images.
        for match in rec.get("matched_buildings",[]):
            if match.get("match_method")!="building_name_phrase_in_commons_title_or_description": continue
            if not match.get("osm_id") or not match.get("building_name"): continue
            index.setdefault(str(match["osm_id"]),[]).append({**rec,"_absolute_file":str(image_path)})
    print("BUILDING_SPECIFIC_LICENSED_PHOTOS",sum(len(v) for v in index.values()))
    return index

def image_material(photo,building_id):
    try:
        image=bpy.data.images.load(photo["_absolute_file"],check_existing=True)
        image.pack()
        material=bpy.data.materials.new("Photo facade "+str(building_id))
        material.use_nodes=True
        nodes=material.node_tree.nodes; links=material.node_tree.links
        bs=nodes.get("Principled BSDF")
        tex=nodes.new("ShaderNodeTexImage");tex.image=image;tex.interpolation="Linear"
        links.new(tex.outputs["Color"],bs.inputs["Base Color"])
        bs.inputs["Roughness"].default_value=.86
        material["photo_source"]=photo.get("commons_page","")
        material["photo_license"]=photo.get("license","")
        material["photo_artist"]=photo.get("artist","")
        material["photo_attribution"]=photo.get("credit","")
        return material
    except Exception as e:
        print("PHOTO_TEXTURE_LOAD_FAILED",str(building_id),repr(e))
        return None

def add_building(item,origin,wallm,roofm,glassm,trim,signm):
    ring=item["ring"][:-1] if len(item["ring"])>3 and item["ring"][0]==item["ring"][-1] else item["ring"]
    if len(ring)<3:return
    pts=[xy(p[0],p[1],*origin) for p in ring];h=item["height"];n=len(pts)
    if n>300:return
    tri=triangulate(pts)
    if not tri:return
    p=item.get("properties") or {}
    wallm=osm_material(p,"building",wallm);roofm=osm_material(p,"roof",roofm)
    # The base mass follows the actual OSM footprint and mapped height where available.
    verts=[(x,0,z) for x,z in pts]+[(x,h,z) for x,z in pts]
    faces=[]
    for a,b,c in tri:faces.extend([(a,c,b),(n+a,n+b,n+c)])
    for i in range(n):j=(i+1)%n;faces.append((i,j,n+j,n+i))
    ob=mesh_obj("Building_"+str(item["id"]),verts,faces,wallm)
    photo=item.get("photo_record")
    photo_mat=image_material(photo,item["id"]) if photo else None
    if photo_mat:
        # Apply the photo only to the longest exterior wall; all other faces retain the mapped/material fallback.
        ob.data.materials.append(photo_mat)
        edge_index=max(range(n),key=lambda i:math.hypot(pts[(i+1)%n][0]-pts[i][0],pts[(i+1)%n][1]-pts[i][1]))
        wall_poly_index=len(tri)*2+edge_index
        if wall_poly_index<len(ob.data.polygons):
            ob.data.polygons[wall_poly_index].material_index=len(ob.data.materials)-1
            uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name="FacadePhotoUV")
            for loop_index,uvco in zip(ob.data.polygons[wall_poly_index].loop_indices,((0,0),(1,0),(1,1),(0,1))):
                uv.data[loop_index].uv=uvco
            ob["facade_texture_source"]="matched Wikimedia Commons building-name photo projected onto longest facade; see attribution metadata"
            ob["photo_source_url"]=photo.get("commons_page","")
            ob["photo_license"]=photo.get("license","")
            ob["photo_artist"]=photo.get("artist","")
            ob["photo_credit"]=photo.get("credit","")
    ob["osm_id"]=str(item["id"]);ob["building_name"]=item["name"];ob["height_m"]=h;ob["height_source"]=item.get("height_source","procedural_default_not_surveyed")
    for k in ("building","building:use","amenity","shop","office","tourism","historic","addr:housenumber","addr:street","addr:postcode","addr:city",
              "name","name:en","ref","operator","brand","building:levels","levels","height","building:material","building:colour",
              "roof:shape","roof:material","roof:colour","roof:levels","roof:height","roof:orientation","start_date","heritage",
              "entrance","door","window","balcony","building:facade","facade:material","facade:colour"):
        if p.get(k) not in (None,""):ob["osm_"+k.replace(":","_")]=str(p[k])
    ob["osm_tags_json"]=json.dumps(p,ensure_ascii=False)[:16000]
    ob["facade_geometry_source"]="OSM footprint and tags; repeated architectural details are procedural where OSM has no detail geometry"
    ob["window_source"]="procedural_layout_from_mapped_height_and_levels; not individually surveyed"
    if not photo_mat: ob["facade_texture_source"]="No matched licensed building photo found; OSM material/colour tags used when present"
    ob["roof_geometry_source"]="OSM roof tags where present; fallback roof form explicitly inferred"

    # Roof form follows roof:shape/roof:height tags; otherwise a conservative flat roof.
    roof_shape=tag(p,"roof:shape").lower()
    roof_h=0.0
    try: roof_h=float(tag(p,"roof:height").lower().replace("meters","").replace("m","").strip())
    except Exception: roof_h=0.0
    roof_h=max(0.0,min(roof_h or (h*0.12 if roof_shape in ("gabled","hipped","pyramidal") else 0.0),12.0))
    if roof_shape in ("gabled","hipped","pyramidal") and roof_h>0.2:
        # Approximate a pitched roof using the real footprint's principal bounding-box axis.
        minx,maxx=min(q[0] for q in pts),max(q[0] for q in pts)
        minz,maxz=min(q[1] for q in pts),max(q[1] for q in pts)
        xspan=maxx-minx;zspan=maxz-minz
        ridge_x=(xspan>=zspan)
        mid=(minx+maxx)/2 if ridge_x else (minz+maxz)/2
        roofverts=[]
        for x,z in pts:
            d=abs(z-mid) if ridge_x else abs(x-mid)
            span=max((zspan if ridge_x else xspan)/2,0.1)
            y=h+roof_h*(1.0-min(1.0,d/span))
            roofverts.append((x,y,z))
        roof_faces=[tuple(t) for t in tri]
        mesh_obj("Pitched roof "+str(item["id"]),roofverts,roof_faces,roofm)
        ob["generated_roof_shape"]=roof_shape
    else:
        mesh_obj("Roof_"+str(item["id"]),[(x,h,z) for x,z in pts],[tuple(t) for t in tri],roofm)
        ob["generated_roof_shape"]="flat_or_unspecified"

    # Generate a regular window layout from measured/mapped floors and footprint edges.
    # It is labelled inferred rather than claiming that individual window locations were surveyed.
    floors_raw=tag(p,"building:levels","levels")
    try:floors=max(1,min(50,int(round(float(floors_raw)))))
    except Exception:floors=max(1,min(50,round(h/3.1)))
    floor_height=h/max(floors,1)
    window_h=min(1.45,max(.65,floor_height*.48))
    winverts=[];winfaces=[];frameverts=[];framefaces=[]
    for i in range(n):
        a=pts[i];b=pts[(i+1)%n];dx=b[0]-a[0];dz=b[1]-a[1];length=math.hypot(dx,dz)
        if length<3 or length>100:continue
        count=min(30,max(1,int(length/2.8)))
        nx=-dz/(length or 1)*.065;nz=dx/(length or 1)*.065
        for floor in range(floors):
            base_y=floor*floor_height+max(.8,floor_height*.28)
            if base_y+window_h>h-max(.25,roof_h):continue
            for k in range(count):
                t=(k+.5)/count;cx=a[0]+dx*t;cz=a[1]+dz*t
                ww=min(1.45,length/count*.52);hh=window_h
                v0=(cx-dx/length*ww/2+nx,base_y,cz-dz/length*ww/2+nz)
                v1=(cx+dx/length*ww/2+nx,base_y,cz+dz/length*ww/2+nz)
                v2=(v1[0],base_y+hh,v1[2]);v3=(v0[0],base_y+hh,v0[2])
                ix=len(winverts);winverts.extend([v0,v1,v2,v3]);winfaces.append((ix,ix+1,ix+2,ix+3))
                # Thin contrasting frame geometry makes windows legible at street-level scale.
                fw=.055
                for q0,q1 in ((v0,v1),(v1,v2),(v2,v3),(v3,v0)):
                    jx=len(frameverts);frameverts.extend([q0,q1,(q1[0]+nx*.15,q1[1],q1[2]+nz*.15),(q0[0]+nx*.15,q0[1],q0[2]+nz*.15)])
                    framefaces.append((jx,jx+1,jx+2,jx+3))
    if winfaces:mesh_obj("Facade windows "+str(item["id"]),winverts,winfaces,glassm)
    if framefaces:mesh_obj("Window frames "+str(item["id"]),frameverts,framefaces,trim)

    # Door/shopfront is placed on the longest footprint edge as a clearly marked inferred entrance.
    # If a mapped entrance/door tag exists, preserve that evidence in the building metadata above.
    edge=max(range(n),key=lambda i:math.hypot(pts[(i+1)%n][0]-pts[i][0],pts[(i+1)%n][1]-pts[i][1]))
    a=pts[edge];b=pts[(edge+1)%n];dx=b[0]-a[0];dz=b[1]-a[1];length=math.hypot(dx,dz)
    if length>=2.2:
        t=.5;cx=a[0]+dx*t;cz=a[1]+dz*t;nx=-dz/(length or 1)*.09;nz=dx/(length or 1)*.09
        dw=min(1.15,length*.22);dh=min(2.25,max(1.9,h*.32))
        dv=[(cx-dx/length*dw/2+nx,0.04,cz-dz/length*dw/2+nz),
            (cx+dx/length*dw/2+nx,0.04,cz+dz/length*dw/2+nz),
            (cx+dx/length*dw/2+nx,dh,cz+dz/length*dw/2+nz),
            (cx-dx/length*dw/2+nx,dh,cz-dz/length*dw/2+nz)]
        mesh_obj("Entrance door inferred "+str(item["id"]),dv,[(0,1,2,3)],signm)
        ob["entrance_geometry"]="inferred_on_longest_footprint_edge_not_mapped_door_location"

    # Balconies are generated only when OSM explicitly marks balcony=yes or balcony:*
    # tags, avoiding fictional balconies for buildings without evidence.
    balcony_evidence=(tag(p,"balcony").lower() in ("yes","true","covered","open") or
                      any(str(k).startswith("balcony:") and str(v).lower() not in ("no","false","0","")
                          for k,v in p.items()))
    if balcony_evidence and h>=3.2:
        for i in range(n):
            a=pts[i];b=pts[(i+1)%n];dx=b[0]-a[0];dz=b[1]-a[1];length=math.hypot(dx,dz)
            if length<5 or length>60:continue
            count=min(8,max(1,int(length/5.0)))
            nx=-dz/(length or 1)*.7;nz=dx/(length or 1)*.7
            for floor in range(1,floors):
                yy=floor*floor_height+.15
                for k in range(count):
                    t=(k+.5)/count;cx=a[0]+dx*t;cz=a[1]+dz*t;ww=min(2.4,length/count*.55)
                    vv=[(cx-dx/length*ww/2,yy,cz-dz/length*ww/2),
                        (cx+dx/length*ww/2,yy,cz+dz/length*ww/2),
                        (cx+dx/length*ww/2+nx,yy,cz+dz/length*ww/2+nz),
                        (cx-dx/length*ww/2+nx,yy,cz-dz/length*ww/2+nz)]
                    mesh_obj("Balcony slab "+str(item["id"]),vv,[(0,1,2,3)],roofm)
                    railh=.95
                    rv=[vv[0],vv[1],(vv[1][0],yy+railh,vv[1][2]),(vv[0][0],yy+railh,vv[0][2])]
                    mesh_obj("Balcony rail "+str(item["id"]),rv,[(0,1,2,3)],trim)
        ob["balcony_geometry_source"]="OSM balcony tags"
    # Roof access hut/equipment silhouette is added only to taller buildings and marked inferred.
    if h>=9:
        cx=sum(q[0] for q in pts)/n;cz=sum(q[1] for q in pts)/n
        rw=min(2.4,max(.8,(max(q[0] for q in pts)-min(q[0] for q in pts))*.18))
        rd=min(2.4,max(.8,(max(q[1] for q in pts)-min(q[1] for q in pts))*.18))
        rv=[(cx-rw/2,h,cz-rd/2),(cx+rw/2,h,cz-rd/2),(cx+rw/2,h,cz+rd/2),(cx-rw/2,h,cz+rd/2),
            (cx-rw/2,h+1.0,cz-rd/2),(cx+rw/2,h+1.0,cz-rd/2),(cx+rw/2,h+1.0,cz+rd/2),(cx-rw/2,h+1.0,cz+rd/2)]
        mesh_obj("Roof service block inferred "+str(item["id"]),rv,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],roofm)
        ob["roof_equipment_source"]="inferred_service_block_not_surveyed"

    number=tag(p,"addr:housenumber","ref")
    if number:
        a=pts[edge];add_text(number,"Building number "+number,(a[0],2,a[1]),.8,trim)
    name=tag(p,"name","name:en","brand")
    if name:
        a=pts[edge];add_text(name,"Building sign "+name,(a[0],min(3,h*.55),a[1]),.55,signm)

def road_mesh(line,origin,width,material,name,y=.015):
    pts=[xy(p[0],p[1],*origin) for p in line]
    verts=[];faces=[]
    for i,(x,z) in enumerate(pts):
        if i==0:dx,dz=pts[1][0]-x,pts[1][1]-z
        elif i==len(pts)-1:dx,dz=x-pts[i-1][0],z-pts[i-1][1]
        else:dx,dz=pts[i+1][0]-pts[i-1][0],pts[i+1][1]-pts[i-1][1]
        l=math.hypot(dx,dz) or 1;ox=-dz/l*width/2;oz=dx/l*width/2
        verts.extend([(x+ox,y,z+oz),(x-ox,y,z-oz)])
    for i in range(len(pts)-1):a=2*i;faces.append((a,a+1,a+3,a+2))
    return mesh_obj(name,verts,faces,material)
def main():
    cfg=args();data=Path(cfg["data"]).resolve();out=Path(cfg["out"]).resolve();out.mkdir(parents=True,exist_ok=True)
    west,east,south,north,tile=[cfg[k] for k in ("west","east","south","north","tile")]
    city=cfg.get("city","Amman");prefix=cfg.get("prefix",city.lower().replace(" ","-"))
    origin=( (west+east)/2,(south+north)/2 )
    buildings=read(data/"buildings.geojson.gz");streets=read(data/"streets.geojson.gz");names=read(data/"streetnames.geojson.gz") if (data/"streetnames.geojson.gz").exists() else []
    def read_optional(name):
        path=Path(cfg.get("infra_path","")) if name=="infrastructure" and cfg.get("infra_path") else data/(name+".geojson.gz")
        return read(path) if path.exists() else []
    waters=read_optional("water");landcovers=read_optional("landcover");places=read_optional("places");addresses=read_optional("addresses");infrastructure=read_optional("infrastructure")
    detail_features=read_optional("building_details")
    detail_by_id={}
    for df in detail_features:
        dp=df.get("properties") or {};did=osm_identity(df,dp)
        if did:detail_by_id[did]=dp
    photo_index=load_verified_photo_index() if prefix.lower()=="tabarbour" else {}
    tiles=defaultdict(lambda:{"buildings":[],"streets":[],"labels":[],"water":[],"landcover":[],"places":[],"addresses":[],"infra_lines":[],"infra_points":[],"infra_polygons":[]})
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
            fid=osm_identity(f,p)
            if fid in detail_by_id:
                merged=dict(detail_by_id[fid]);merged.update(p);p=merged
            raw_height=tag(p,"height","building:height")
            raw_levels=tag(p,"building:levels","levels")
            h=height(p)
            height_source="osm:height" if raw_height else "osm:building:levels" if raw_levels else "procedural_default_not_surveyed"
            photo_candidates=photo_index.get(str(fid),[])
            photo_record=photo_candidates[0] if len(photo_candidates)==1 else None
            if photo_record: print("MATCHED_FACADE_PHOTO",fid,photo_record.get("title"),flush=True)
            tiles[key(lon,lat)]["buildings"].append({"id":fid,"name":tag(p,"name","name:en"),"height":h,"height_source":height_source,"ring":ring,"properties":p,"photo_record":photo_record})
    for f in streets:
        p=f.get("properties") or {};g=f.get("geometry") or {};c=g.get("coordinates") or []
        lines=[c] if g.get("type")=="LineString" else c if g.get("type")=="MultiLineString" else []
        for line in lines:
            if len(line)<2:continue
            lon=sum(q[0] for q in line)/len(line);lat=sum(q[1] for q in line)/len(line)
            if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)]["streets"].append({"line":line,"name":tag(p,"name","name:en","ref"),"highway":tag(p,"highway"),"properties":p,"id":osm_identity(f,p)})
    for f in names:
        p=f.get("properties") or {};g=f.get("geometry") or {};c=g.get("coordinates") or []
        if g.get("type")=="Point" and len(c)>=2 and west<=c[0]<=east and south<=c[1]<=north:
            tiles[key(c[0],c[1])]["labels"].append({"name":tag(p,"name","name:en"),"point":c})
    def collect_polygons(features,keyname):
        for f in features:
            p=f.get("properties") or {};g=f.get("geometry") or {};coords=g.get("coordinates") or []
            polygons=coords if g.get("type")=="MultiPolygon" else [coords] if g.get("type")=="Polygon" else []
            for poly in polygons:
                if not poly or not poly[0]:continue
                ring=[[q[0],q[1]] for q in poly[0] if len(q)>1]
                if len(ring)<4:continue
                lon=sum(q[0] for q in ring)/len(ring);lat=sum(q[1] for q in ring)/len(ring)
                if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)][keyname].append({"ring":ring,"properties":p,"id":osm_identity(f,p)})
    collect_polygons(waters,"water");collect_polygons(landcovers,"landcover")
    for f in infrastructure:
        p=f.get("properties") or {};g=f.get("geometry") or {};gt=g.get("type");co=g.get("coordinates") or []
        fid=str(f.get("id") or p.get("@id") or p.get("osm_id") or "")
        if gt=="Point" and len(co)>=2:
            lon,lat=co[0],co[1]
            if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)]["infra_points"].append({"point":co,"properties":p,"id":fid})
        elif gt=="LineString":
            if len(co)>=2:
                lon=sum(q[0] for q in co)/len(co);lat=sum(q[1] for q in co)/len(co)
                if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)]["infra_lines"].append({"line":co,"properties":p,"id":fid})
        elif gt=="MultiLineString":
            for line in co:
                if len(line)>=2:
                    lon=sum(q[0] for q in line)/len(line);lat=sum(q[1] for q in line)/len(line)
                    if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)]["infra_lines"].append({"line":line,"properties":p,"id":fid})
        elif gt=="Polygon":
            if co and co[0]:
                ring=[[q[0],q[1]] for q in co[0] if len(q)>1]
                if len(ring)>=4:
                    lon=sum(q[0] for q in ring)/len(ring);lat=sum(q[1] for q in ring)/len(ring)
                    if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)]["infra_polygons"].append({"ring":ring,"properties":p,"id":fid})
        elif gt=="MultiPolygon":
            for poly in co:
                if poly and poly[0]:
                    ring=[[q[0],q[1]] for q in poly[0] if len(q)>1]
                    if len(ring)>=4:
                        lon=sum(q[0] for q in ring)/len(ring);lat=sum(q[1] for q in ring)/len(ring)
                        if west<=lon<=east and south<=lat<=north:tiles[key(lon,lat)]["infra_polygons"].append({"ring":ring,"properties":p,"id":fid})
    for f in places:
        p=f.get("properties") or {};g=f.get("geometry") or {};co=g.get("coordinates") or []
        if g.get("type")=="Point" and len(co)>=2 and west<=co[0]<=east and south<=co[1]<=north:
            tiles[key(co[0],co[1])]["places"].append({"point":co,"name":tag(p,"name","name:en"),"properties":p,"id":osm_identity(f,p)})
    for f in addresses:
        p=f.get("properties") or {};g=f.get("geometry") or {};co=g.get("coordinates") or []
        if g.get("type")=="Point" and len(co)>=2 and west<=co[0]<=east and south<=co[1]<=north:
            tiles[key(co[0],co[1])]["addresses"].append({"point":co,"name":tag(p,"addr:housenumber","name"),"properties":p,"id":osm_identity(f,p)})
    walls=mat("Unspecified building facade",(.72,.65,.52));roofm=mat("Unspecified roof material",(.48,.43,.36));glass=mat("Window glass",(.22,.38,.46),.24,.18);trim=mat("Facade trim",(.88,.82,.68));signm=mat("Shop sign backing",(.12,.20,.16),.65)
    asphalt=mat("Road asphalt",(.16,.16,.15));residential=mat("Road surface",(.27,.26,.24))
    waterm=mat("OSM water",(.12,.34,.52),.32,.05);greenm=mat("OSM landcover",(.28,.38,.20),.95)
    manifest_path=out/"manifest.json"
    manifest={"city":city,"bounds":{"west":west,"east":east,"south":south,"north":north},
              "origin":{"longitude":origin[0],"latitude":origin[1],"crs":"WGS84 input; local equirectangular meters; X=east, Z=north, Y=height"},
              "tile_degrees":tile,"tiles":[],"counts":{"buildings":0,"streets":0,"street_labels":0}}
    # Preserve checkpointed tiles across separate regional-cell invocations.
    if manifest_path.exists():
        try:
            previous=json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["tiles"]=previous.get("tiles",[])
            manifest["counts"]=previous.get("counts",manifest["counts"])
        except Exception as e:
            print("MANIFEST_READ_WARNING",repr(e))
    known={entry.get("file") for entry in manifest["tiles"]}
    for (tx,ty),items in sorted(tiles.items()):
        filename=f"{prefix}_{tx}_{ty}.glb";target=out/filename
        if target.exists() and target.stat().st_size>1024 and not cfg.get("force",False):
            print("RESUME_SKIP_EXISTING",target)
            if filename not in known:
                # Recover tile inventory after interrupted runs whose manifest was overwritten.
                manifest["tiles"].append({"tile":f"{tx}_{ty}","file":filename,"buildings":None,"streets":None,"labels":None,"bytes":target.stat().st_size,"counts_known":False})
                known.add(filename)
                manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
            continue
        try:
            bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
            bpy.context.scene.unit_settings.system="METRIC"
            for b in items["buildings"]:add_building(b,origin,walls,roofm,glass,trim,signm)
            for s in items["streets"]:
                hw=s["highway"].lower();w=12 if hw in ("motorway","trunk") else 8 if hw in ("primary","secondary") else 5 if hw=="tertiary" else 3.2 if hw in ("residential","unclassified") else 1.3
                p=s.get("properties") or {}
                road_y=-.8 if tag(p,"tunnel") not in ("","no") else .3 if tag(p,"bridge") not in ("","no") else .015
                road=road_mesh(s["line"],origin,w,road_surface_material(p,asphalt if w>2 else residential),"Road "+s["name"],road_y)
                if road:
                    for keyname in ("name","ref","highway","surface","lanes","maxspeed","oneway","bridge","tunnel","layer","access","service","junction","motor_vehicle","bicycle","foot","lit"):
                        if p.get(keyname) not in (None,""):road["osm_"+keyname]=str(p[keyname])
                    road["osm_tags_json"]=json.dumps(p,ensure_ascii=False)[:8000]
                if s["name"]:
                    p=s["line"][len(s["line"])//2];x,z=xy(p[0],p[1],*origin)
                    add_text(s["name"],"Street name "+s["name"],(x,.12,z),2.2,trim)
            for item in items["water"]:
                flat_polygon("Water "+str(item["id"]),item["ring"],origin,.025,waterm)
            for item in items["landcover"]:
                flat_polygon("Landcover "+str(item["id"]),item["ring"],origin,.005,greenm)
            for item in items["places"]:
                x,z=xy(item["point"][0],item["point"][1],*origin)
                ob=add_text(item["name"] or str(item["id"]),"Place "+str(item["id"]),(x,.2,z),2.4,trim)
                if ob:
                    ob["osm_id"]=str(item["id"]);ob["osm_tags_json"]=json.dumps(item["properties"],ensure_ascii=False)[:8000]
            # OSM infrastructure: railways, waterways, power lines, barriers, transit and traffic devices.
            for item in items["infra_lines"]:
                p=item["properties"]
                if tag(p,"highway"):continue
                rail=tag(p,"railway");waterway=tag(p,"waterway");power=tag(p,"power")
                bridge=tag(p,"bridge","man_made")=="bridge";tunnel=tag(p,"tunnel") not in ("","no")
                width=.9 if rail else .35 if power else 1.2 if waterway else .45
                material=mat("OSM railway",(.20,.20,.20)) if rail else waterm if waterway else mat("OSM power line",(.35,.35,.32)) if power else residential
                y=-.8 if tunnel else .3 if bridge else .04 if rail else .025
                ob=road_mesh(item["line"],origin,width,material,"Infrastructure "+str(item["id"]),y)
                if ob:
                    ob["osm_id"]=str(item["id"]);ob["osm_tags_json"]=json.dumps(p,ensure_ascii=False)[:8000]
            for item in items["infra_polygons"]:
                p=item["properties"];land=tag(p,"leisure","landuse","natural");water_tag=tag(p,"natural","waterway","water")
                material=waterm if water_tag in ("water","riverbank","wetland") else greenm if land else residential
                ob=flat_polygon("Infrastructure "+str(item["id"]),item["ring"],origin,.02,material)
                if ob:
                    ob["osm_id"]=str(item["id"]);ob["osm_tags_json"]=json.dumps(p,ensure_ascii=False)[:8000]
            for item in items["infra_points"]:
                p=item["properties"];x,z=xy(item["point"][0],item["point"][1],*origin)
                kind=tag(p,"highway","railway","public_transport","natural","power","man_made","amenity")
                h=.35 if kind in ("traffic_signals","stop","crossing") else 3.5 if kind=="tree" else 1.2
                w=.12 if kind=="traffic_signals" else .35
                if kind=="tree":
                    verts=[(x-.12,0,z-.12),(x+.12,0,z-.12),(x+.12,0,z+.12),(x-.12,0,z+.12),
                           (x-.12,1.35,z-.12),(x+.12,1.35,z-.12),(x+.12,1.35,z+.12),(x-.12,1.35,z+.12),
                           (x-.85,1.1,z-.85),(x+.85,1.1,z-.85),(x+.85,1.1,z+.85),(x-.85,1.1,z+.85),(x, h+1.5, z)]
                    faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0),
                           (8,9,12),(9,10,12),(10,11,12),(11,8,12),(8,11,10,9)]
                    material=mat("OSM tree foliage",(.15,.32,.12),.95)
                else:
                    verts=[(x-w,0,z-w),(x+w,0,z-w),(x+w,0,z+w),(x-w,0,z+w),(x-w,h,z-w),(x+w,h,z-w),(x+w,h,z+w),(x-w,h,z+w)]
                    faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
                    material=mat("OSM transport marker",(.76,.42,.10))
                ob=mesh_obj("OSM "+kind+" "+str(item["id"]),verts,faces,material)
                ob["osm_id"]=str(item["id"]);ob["osm_tags_json"]=json.dumps(p,ensure_ascii=False)[:8000]
            for item in items["addresses"]:
                # Address records stay as georeferenced metadata objects, not thousands of tiny text meshes.
                x,z=xy(item["point"][0],item["point"][1],*origin)
                ob=mesh_obj("Address "+str(item["id"]),[(x,.22,z),(x+.01,.22,z),(x,.23,z+.01)],[(0,1,2)],trim)
                if ob:
                    ob["osm_id"]=str(item["id"]);ob["address_label"]=item["name"]
                    ob["osm_tags_json"]=json.dumps(item["properties"],ensure_ascii=False)[:8000]
            for lab in items["labels"]:
                x,z=xy(lab["point"][0],lab["point"][1],*origin);add_text(lab["name"],"Street label "+lab["name"],(x,.15,z),2,trim)
            bpy.ops.export_scene.gltf(filepath=str(target),export_format="GLB",use_selection=False,export_apply=True)
            record={"tile":f"{tx}_{ty}","file":filename,"buildings":len(items["buildings"]),"streets":len(items["streets"]),"labels":len(items["labels"]),
                    "water_features":len(items["water"]),"landcover_features":len(items["landcover"]),"place_points":len(items["places"]),"address_points":len(items["addresses"]),
                    "infrastructure_lines":len(items["infra_lines"]),"infrastructure_points":len(items["infra_points"]),"infrastructure_polygons":len(items["infra_polygons"]),
                    "bytes":target.stat().st_size,"counts_known":True}
            existing=next((entry for entry in manifest["tiles"] if entry.get("file")==filename),None)
            if existing is None:
                manifest["tiles"].append(record)
                known.add(filename)
            else:
                existing.update(record)
            print("EXPORTED",target,len(items["buildings"]),len(items["streets"]))
            manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
            if cfg.get("repo_commit",True):
                try:
                    repo_root=Path(os.environ.get("GITHUB_WORKSPACE", subprocess.check_output(["git","rev-parse","--show-toplevel"],cwd=Path(__file__).resolve().parents[3],text=True).strip())).resolve()
                    rel=target.resolve().relative_to(repo_root)
                    subprocess.run(["git","add","--",str(rel),str(manifest_path.resolve().relative_to(repo_root.resolve()))],cwd=repo_root,check=True)
                    subprocess.run(["git","-c","user.name=github-actions[bot]","-c","user.email=41898282+github-actions[bot]@users.noreply.github.com","commit","-m",f"Add generated {city} GLB tile {tx}_{ty}"],cwd=repo_root,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    subprocess.run(["git","push","origin","HEAD:main"],cwd=repo_root,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    print("CHECKPOINT_PUSHED",rel)
                except Exception as e: print("CHECKPOINT_PUSH_FAILED",repr(e))
        except Exception as e:
            print("TILE_FAILED_CONTINUING",city,tx,ty,repr(e));traceback.print_exc()
            try: (out/"failures.jsonl").open("a",encoding="utf-8").write(json.dumps({"city":city,"tile":f"{tx}_{ty}","error":repr(e)})+"\\n")
            except Exception: pass

    manifest["counts"]={
        "buildings":sum(int(x.get("buildings") or 0) for x in manifest["tiles"]),
        "streets":sum(int(x.get("streets") or 0) for x in manifest["tiles"]),
        "street_labels":sum(int(x.get("labels") or 0) for x in manifest["tiles"]),
        "water_features":sum(int(x.get("water_features") or 0) for x in manifest["tiles"]),
        "landcover_features":sum(int(x.get("landcover_features") or 0) for x in manifest["tiles"]),
        "place_points":sum(int(x.get("place_points") or 0) for x in manifest["tiles"]),
        "address_points":sum(int(x.get("address_points") or 0) for x in manifest["tiles"]),
        "infrastructure_lines":sum(int(x.get("infrastructure_lines") or 0) for x in manifest["tiles"]),
        "infrastructure_points":sum(int(x.get("infrastructure_points") or 0) for x in manifest["tiles"]),
        "infrastructure_polygons":sum(int(x.get("infrastructure_polygons") or 0) for x in manifest["tiles"]),
    }
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print(city+" GLB COMPLETE",json.dumps(manifest["counts"]))
if __name__=="__main__":main()
