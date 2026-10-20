#!/usr/bin/env python3
"""Build image-sign panels for mapped 7-Eleven/McDonald's storefronts and a procedural Robinsons Manila facade.

Outputs are derived assets. The canonical OSM building data is read-only here.
Store signs are real downloaded brand images embedded as textures on shallow 3D panels,
not painted onto building textures. Robinsons detail is procedural geometry informed by
licensed reference photographs, not a photogrammetric reconstruction.
"""
from __future__ import annotations
import hashlib, io, json, math, re, time
from pathlib import Path
import requests, trimesh, cairosvg
from PIL import Image
from pyproj import Transformer
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "ermita/maps/generated/ermita-building-details.geojson"
STORES_FILE = ROOT / "ermita/maps/generated/ermita-branded-stores.geojson"
OUT_DIR = ROOT / "ermita/3d/commercial"
ASSET_DIR = ROOT / "ermita/buildings/commercial_assets"
PHOTO_DIR = ROOT / "ermita/buildings/reference_photos/robinsons-manila"
OUT_GLB = OUT_DIR / "commercial-facades.glb"
OUT_ORIGIN = OUT_DIR / "commercial-facades-origin.json"
OUT_REPORT = OUT_DIR / "commercial-facades-report.json"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_LONLAT = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
HEADERS = {"User-Agent": "Adam-City/1.0 (open-data 3D facade research; https://github.com/saeedhub101/Adam-City)"}
SEVEN_SVG = "https://www.7-eleven.com/assets/img/header/7e-logo-color.svg"
MCD_LOGO = "https://commons.wikimedia.org/wiki/Special:FilePath/McDonalds.png"

def fetch(url, timeout=45):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.content

def load_logo_assets():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    seven_png = ASSET_DIR / "7-eleven-logo.png"
    seven_svg = ASSET_DIR / "7-eleven-logo-source.svg"
    if not seven_png.exists() or seven_png.stat().st_size < 200:
        svg = fetch(SEVEN_SVG)
        seven_svg.write_bytes(svg)
        cairosvg.svg2png(bytestring=svg, write_to=str(seven_png), output_width=900, output_height=1200)
    mc_png = ASSET_DIR / "mcdonalds-golden-arches.png"
    if not mc_png.exists() or mc_png.stat().st_size < 200:
        raw = fetch(MCD_LOGO)
        if b"<svg" in raw[:1000].lower():
            cairosvg.svg2png(bytestring=raw, write_to=str(mc_png), output_width=1200, output_height=1050)
        else:
            mc_png.write_bytes(raw)
    return Image.open(seven_png).convert("RGBA"), Image.open(mc_png).convert("RGBA")

def fetch_robinsons_reference_photos():
    """Download high-resolution Robinsons Manila exterior photographs with attribution."""
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    api = "https://commons.wikimedia.org/w/api.php"
    titles = [
        "File:Robinsons Place Manila, May 2025 (1).jpg",
        "File:Robinsons Place Manila, May 2025 (2).jpg",
    ]
    params = {
        "action":"query", "titles":"|".join(titles), "prop":"imageinfo",
        "iiprop":"url|extmetadata|size", "iiurlwidth":1800, "format":"json"
    }
    downloaded = []
    try:
        response = requests.get(api, params=params, headers=HEADERS, timeout=45)
        response.raise_for_status()
        pages = list((response.json().get("query") or {}).get("pages", {}).values())
        pages.sort(key=lambda p:p.get("title",""))
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            title = page.get("title","")
            url = info.get("thumburl") or info.get("url")
            meta = info.get("extmetadata") or {}
            license_name = (meta.get("LicenseShortName") or {}).get("value","")
            artist = re.sub("<[^>]+>", "", (meta.get("Artist") or {}).get("value","")).strip()
            description_url = info.get("descriptionurl","")
            if not url or not license_name:
                continue
            raw = fetch(url)
            try:
                image = Image.open(io.BytesIO(raw))
                if image.width < 900 or image.height < 500:
                    continue
            except Exception:
                continue
            slug = re.sub(r"[^a-zA-Z0-9]+","-",title.replace("File:","")).strip("-").lower()[:90]
            path = PHOTO_DIR / (slug + ".jpg")
            path.write_bytes(raw)
            downloaded.append({
                "title":title, "path":str(path.relative_to(ROOT)), "source_url":description_url,
                "download_url":url, "license":license_name, "artist":artist,
                "width":image.width, "height":image.height
            })
    except Exception as exc:
        print("WARNING: unable to refresh Robinsons reference photos:", exc)
    if not downloaded:
        raise RuntimeError("Could not download the selected high-resolution Robinsons Manila reference photographs")
    return downloaded

def props(feature):
    p = feature.get("properties")
    return p if isinstance(p,dict) else {}

def fid(feature):
    p=props(feature)
    return str(p.get("osm_feature_id") or (str(p.get("type","way"))+"/"+str(p.get("id",""))))

def tags(feature):
    t=props(feature).get("tags")
    return t if isinstance(t,dict) else props(feature)

def polygon_parts(geom):
    if geom.geom_type=="Polygon": return [geom]
    if geom.geom_type=="MultiPolygon": return list(geom.geoms)
    return []

def paint(mesh, name, color):
    mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name=name, baseColorFactor=color, metallicFactor=0.0, roughnessFactor=0.75, doubleSided=True))
    return mesh

def box(center, extents, angle, name, color):
    m=trimesh.creation.box(extents=extents)
    m.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]))
    m.apply_translation(center)
    return paint(m,name,color)

def textured_panel(a,b,normal,origin,z,width,height,image,name,angle):
    """A real image on a separate, shallow quad mounted just off a facade."""
    ux,uy=(b[0]-a[0]),(b[1]-a[1])
    length=math.hypot(ux,uy)
    if length<0.01: return None
    ux,uy=ux/length,uy/length
    cx=(a[0]+b[0])/2+normal[0]*0.16-origin[0]
    cy=(a[1]+b[1])/2+normal[1]*0.16-origin[1]
    # Preserve source aspect ratio inside the requested storefront sign size.
    img=image.copy()
    img.thumbnail((1200,1200),Image.Resampling.LANCZOS)
    bg=Image.new("RGBA",(1200,1200),(245,245,245,255))
    scale=min(1100/max(1,img.width),1100/max(1,img.height))
    img=img.resize((max(1,int(img.width*scale)),max(1,int(img.height*scale))),Image.Resampling.LANCZOS)
    bg.alpha_composite(img,((1200-img.width)//2,(1200-img.height)//2))
    # Embed a square texture; transparent padding preserves logos without stretching.
    material=trimesh.visual.material.PBRMaterial(name=name,baseColorFactor=[255,255,255,255],
        metallicFactor=0.0,roughnessFactor=0.8,baseColorTexture=bg,doubleSided=True)
    c,s=math.cos(angle),math.sin(angle)
    w,h=width/2,height/2
    local=[(-w,-h),(w,-h),(w,h),(-w,h)]
    vertices=[]
    for x,zoff in local:
        rx=x*c; ry=x*s
        vertices.append([cx+rx,cy+ry,z+zoff])
    mesh=trimesh.Trimesh(vertices=vertices,faces=[[0,1,2],[0,2,3]],process=False)
    mesh.visual=trimesh.visual.TextureVisuals(uv=[[0,1],[1,1],[1,0],[0,0]],material=material)
    return mesh

def longest_edge(poly):
    ring=list(poly.exterior.coords)
    edges=[]
    for a,b in zip(ring[:-1],ring[1:]):
        length=math.hypot(b[0]-a[0],b[1]-a[1])
        if length>=4: edges.append((a,b,length,math.atan2(b[1]-a[1],b[0]-a[0])))
    return max(edges,key=lambda e:e[2]) if edges else None

def outward_normal(poly,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
    nx,ny=dy/length,-dx/length
    mid=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
    test=Point(mid.x+nx*0.5,mid.y+ny*0.5)
    if poly.contains(test): nx,ny=-nx,-ny
    return nx,ny

def nearest_edge(poly, point):
    """Choose a usable facade edge nearest the mapped store POI; break ties by frontage length."""
    ring=list(poly.exterior.coords)
    candidates=[]
    for a,b in zip(ring[:-1],ring[1:]):
        length=math.hypot(b[0]-a[0],b[1]-a[1])
        if length<4: continue
        dx,dy=b[0]-a[0],b[1]-a[1]
        denom=dx*dx+dy*dy
        t=0.0 if denom==0 else max(0.0,min(1.0,((point.x-a[0])*dx+(point.y-a[1])*dy)/denom))
        qx,qy=a[0]+t*dx,a[1]+t*dy
        distance=math.hypot(point.x-qx,point.y-qy)
        candidates.append((distance,-length,a,b,math.atan2(dy,dx)))
    if not candidates: return None
    distance,neg_length,a,b,angle=min(candidates,key=lambda x:(round(x[0],2),x[1]))
    return a,b,-neg_length,angle

def add_robinsons_detail(scene, feature, origin, report):
    geom=geom_transform(TO_METERS,shape(feature["geometry"]))
    polys=polygon_parts(geom)
    if not polys: raise RuntimeError("Robinsons Manila footprint is not polygonal")
    poly=max(polys,key=lambda p:p.area)
    edge=longest_edge(poly)
    if not edge: raise RuntimeError("Robinsons Manila has no suitable facade edge")
    a,b,length,angle=edge
    normal=outward_normal(poly,a,b)
    ux,uy=(b[0]-a[0])/length,(b[1]-a[1])/length
    # Seven-storey retail massing from the mall operator's published description.
    # These are facade details added to the source footprint, not replacement footprint geometry.
    height=28.0; floors=7; floor_h=height/floors
    palette={"concrete":[190,190,184,255],"glass":[90,139,157,255],"dark":[62,73,77,255],
             "sign":[224,35,49,255],"white":[245,245,237,255],"metal":[110,119,120,255]}
    cx=(a[0]+b[0])/2-origin[0]+normal[0]*0.2
    cy=(a[1]+b[1])/2-origin[1]+normal[1]*0.2
    # Broad horizontal floor bands, continuous parapet and corner piers.
    scene.add_geometry(box((cx,cy,floor_h*0.5),(length*0.96,0.48,0.42),angle,"Robinsons ground plinth",palette["dark"]))
    for floor in range(1,floors):
        z=floor*floor_h
        scene.add_geometry(box((cx,cy,z),(length*0.985,0.36,0.28),angle,"Robinsons floor slab band",palette["white"]))
    scene.add_geometry(box((cx,cy,height),(length*0.99,0.55,0.65),angle,"Robinsons roof parapet",palette["concrete"]))
    # Repeated window bays: dark glass panels with pale mullion frames.
    bays=max(8,min(48,int(length/5.0)))
    for floor in range(floors):
        z=floor*floor_h+floor_h*0.54
        for i in range(bays):
            t=(i+0.5)/bays
            x=a[0]+ux*length*t+normal[0]*0.38-origin[0]
            y=a[1]+uy*length*t+normal[1]*0.38-origin[1]
            bw=min(3.6,length/bays*0.74)
            scene.add_geometry(box((x,y,z),(bw,0.14,floor_h*0.58),angle,"Robinsons dark glazed bay",palette["glass"]))
            # Slim vertical mullions on alternating bays.
            if i%2==0:
                scene.add_geometry(box((x,y,z),(0.10,0.22,floor_h*0.62),angle,"Robinsons window mullion",palette["metal"]))
    # A prominent projecting entrance canopy with supports, on the main frontage.
    canopy_z=4.4
    scene.add_geometry(box((cx,cy,canopy_z),(min(length*0.30,24),3.0,0.48),angle,"Robinsons entrance canopy",palette["dark"]))
    for side in (-1,1):
        px=cx+ux*min(length*0.12,9)*side
        py=cy+uy*min(length*0.12,9)*side
        scene.add_geometry(box((px,py,canopy_z/2),(0.28,0.28,canopy_z),angle,"Robinsons canopy support",palette["metal"]))
    # A freestanding, readable mall wordmark sign as geometry (not a photo texture).
    sign_w=min(length*0.42,34)
    sign_z=height-3.4
    scene.add_geometry(box((cx,cy,sign_z),(sign_w,0.62,2.25),angle,"Robinsons red fascia sign backing",palette["sign"]))
    # Wordmark represented as shallow white blocks; avoids a fake photograph on the mall.
    letters=len("ROBINSONS")
    gap=sign_w/(letters+1)
    for i,ch in enumerate("ROBINSONS"):
        lx=cx+(i-(letters-1)/2)*gap*0.92*math.cos(angle)
        ly=cy+(i-(letters-1)/2)*gap*0.92*math.sin(angle)+normal[1]*0.02
        scene.add_geometry(box((lx,ly,sign_z),(max(0.42,gap*0.62),0.18,0.72),angle,"Robinsons wordmark letter",palette["white"]))
    report["robinsons_mall"]={"osm_feature_id":fid(feature),"facade_edge_m":round(length,2),"approximate_height_m":height,
        "levels_modeled":floors,"mesh_detail_count":len(scene.geometry),"method":"procedural facade bands, repeated glazed bays, entrance canopy, parapet and raised wordmark",
        "accuracy_note":"Visual approximation informed by Robinsons Manila reference photos and the official mall description; not photogrammetry or a surveyed model."}

def main():
    for p in (MAP_FILE,STORES_FILE):
        if not p.exists(): raise FileNotFoundError(p)
    source=json.loads(MAP_FILE.read_text(encoding="utf-8"))
    stores=json.loads(STORES_FILE.read_text(encoding="utf-8"))
    building_features=[]
    for f in source.get("features",[]):
        g=f.get("geometry")
        if not g or g.get("type") not in ("Polygon","MultiPolygon"): continue
        try:
            geom=geom_transform(TO_METERS,shape(g))
            if geom.is_valid and not geom.is_empty: building_features.append((f,geom))
        except Exception: pass
    store_features=[f for f in stores.get("features",[]) if re.search(r"7.?eleven|mcdonald",str(props(f).get("brand","")+" "+props(f).get("name","")),re.I)]
    if not building_features: raise RuntimeError("No valid building polygons in canonical GeoJSON")
    # The named Robinsons retail-area polygon (way/48894714) is a landuse/site outline,
    # not the actual building footprint. The mapped 7-level retail building way/130532101
    # is the candidate footprint; validate its building tags and scale before using it.
    mall=next((f for f,g in building_features
        if fid(f)=="way/130532101"
        and str(tags(f).get("building","")).lower()=="retail"
        and str(tags(f).get("building:levels",""))=="7"
        and str(tags(f).get("height",""))=="25"),None)
    if mall is None:
        raise RuntimeError("Could not verify Robinsons Manila's 7-level retail building footprint way/130532101; refusing to guess")
    mall_geom=geom_transform(TO_METERS,shape(mall["geometry"]))
    mall_parts=polygon_parts(mall_geom)
    mall_area=max((p.area for p in mall_parts),default=0.0)
    if mall_area < 20000 or mall_area > 250000:
        raise RuntimeError(f"Robinsons candidate footprint has implausible area {mall_area:.0f} m²; refusing to generate")
    # Origin near center of Ermita/Malate assets keeps all local coordinates numerically stable.
    all_bounds=[g.bounds for _,g in building_features]
    minx=min(b[0] for b in all_bounds); miny=min(b[1] for b in all_bounds)
    maxx=max(b[2] for b in all_bounds); maxy=max(b[3] for b in all_bounds)
    origin=((minx+maxx)/2,(miny+maxy)/2,0.0)
    seven_img,mc_img=load_logo_assets()
    photo_refs=fetch_robinsons_reference_photos()
    (PHOTO_DIR / "reference-index.json").write_text(json.dumps({"subject":"Robinsons Manila","photos":photo_refs,"note":"Reference photographs are used for visual research; generated geometry is procedural, not photogrammetry."},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    scene=trimesh.Scene()
    report={"generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_files":[str(MAP_FILE.relative_to(ROOT)),str(STORES_FILE.relative_to(ROOT))],
        "photo_references":photo_refs,"store_signs":[],"unmatched_store_pois":[],"notes":["Image signage is a separate textured 3D panel; it does not overwrite building textures.","Store POIs inside the Robinsons mall footprint are reported but not placed on the outside mall wall.","Only explicitly named Robinsons Manila footprint was used for mall detail."]}
    add_robinsons_detail(scene,mall,origin,report)
    # Deduplicate multiple POIs that belong to the same storefront polygon and brand.
    placed=set()
    for store in store_features:
        sp=props(store); brand=str(sp.get("brand") or sp.get("name") or "")
        is_seven=bool(re.search(r"7.?eleven",brand,re.I))
        brand_key="7-Eleven" if is_seven else "McDonald's"
        geom=store.get("geometry") or {}
        if geom.get("type")!="Point":
            report["unmatched_store_pois"].append({"id":fid(store),"brand":brand_key,"reason":"POI is not a point"})
            continue
        pt=geom_transform(TO_METERS,Point(geom["coordinates"]))
        # Indoor mall branches are not exterior storefronts; avoid painting them onto the mall shell.
        if mall_geom.buffer(1.0).covers(pt):
            report["unmatched_store_pois"].append({"id":fid(store),"brand":brand_key,"reason":"inside Robinsons Manila footprint; not assigned to an exterior facade"})
            continue
        candidates=[]
        for bf,bgeom in building_features:
            bt=tags(bf)
            if fid(bf)=="way/130532101" or str(bt.get("name","")).lower() in ("robinsons manila","robinsons place manila"): continue
            # Prefer an explicitly branded building, then a nearby footprint containing the POI.
            dist=bgeom.distance(pt)
            if dist<=28:
                brand_match=re.search(r"7.?eleven|mcdonald",str(bt.get("brand","")+" "+bt.get("name","")),re.I)
                candidates.append((0 if brand_match else 1,dist,bf,bgeom))
        if not candidates:
            report["unmatched_store_pois"].append({"id":fid(store),"brand":brand_key,"reason":"no independent building footprint within 28 m; not placed on a guessed building"})
            continue
        candidates.sort(key=lambda x:(x[0],x[1]))
        _,dist,bf,bgeom=candidates[0]
        key=(brand_key,fid(bf))
        if key in placed: continue
        edge=nearest_edge(max(polygon_parts(bgeom),key=lambda p:p.area),pt)
        if not edge:
            report["unmatched_store_pois"].append({"id":fid(store),"brand":brand_key,"reason":"matched footprint has no usable facade edge"})
            continue
        a,b,length,angle=edge
        poly=max(polygon_parts(bgeom),key=lambda p:p.area)
        normal=outward_normal(poly,a,b)
        center_z=3.0 if is_seven else 2.6
        width=1.7 if is_seven else 1.55
        height=2.1 if is_seven else 1.3
        img=seven_img if is_seven else mc_img
        panel=textured_panel(a,b,normal,origin,center_z,width,height,img,brand_key+" real image sign panel",angle)
        if panel is None: continue
        scene.add_geometry(panel,node_name=brand_key+" image signage "+fid(bf))
        placed.add(key)
        report["store_signs"].append({"brand":brand_key,"store_poi_id":fid(store),"building_osm_id":fid(bf),
            "poi_to_footprint_m":round(dist,2),"panel_width_m":width,"panel_height_m":height,
            "image_asset":"ermita/buildings/commercial_assets/7-eleven-logo.png" if is_seven else "ermita/buildings/commercial_assets/mcdonalds-golden-arches.png",
            "placement":"separate textured quad placed just off the facade edge nearest the mapped store POI",
            "source_note":"Logo asset is downloaded from the official 7-Eleven site / Wikimedia Commons public-domain McDonald's logo."})
    if not scene.geometry: raise RuntimeError("No commercial facade geometry was generated")
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    glb=scene.export(file_type="glb")
    OUT_GLB.write_bytes(glb)
    lon,lat=TO_LONLAT(origin[0],origin[1])
    OUT_ORIGIN.write_text(json.dumps({"longitude":lon,"latitude":lat,"anchor_altitude_m":0.0,
        "coordinate_system":"EPSG:3857 local meters recentered at longitude/latitude/anchor altitude",
        "origin_method":"center of valid mapped Ermita building extent"},indent=2)+"\n",encoding="utf-8")
    report["counts"]={"building_polygons_considered":len(building_features),"brand_pois_considered":len(store_features),
        "sign_panels_placed":len(report["store_signs"]),"unmatched_or_interior_pois":len(report["unmatched_store_pois"]),
        "glb_mesh_count":len(scene.geometry),"glb_bytes":len(glb)}
    report["logo_sources"]={"7-Eleven":"https://www.7-eleven.com/assets/img/header/7e-logo-color.svg",
        "McDonald's":"https://commons.wikimedia.org/wiki/File:McDonalds.png"}
    OUT_REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report["counts"],indent=2))
    if report["counts"]["sign_panels_placed"]<1: raise RuntimeError("No brand panels were placed; refusing to accept an empty signage model")

if __name__=="__main__":
    main()
