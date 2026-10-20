#!/usr/bin/env python3
"""Generate a separate, source-traceable architectural landmark-detail GLB.

The model contains facade overlays only; base building geometry remains from the map.
The National Museum footprint is fetched from OSM relation 61326. The PGH Cancer
Institute footprint is still an explicitly marked candidate (way/16554344) and must
not be considered an identity-confirmed match until checked against the reference.
"""
import json, math
from pathlib import Path
import requests
import trimesh
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, shape
from shapely.ops import polygonize, unary_union, transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "ermita/maps/generated/ermita-building-details.geojson"
OUT_DIR = ROOT / "ermita/3d/landmarks"
OUT_GLB = OUT_DIR / "landmark-facade-details.glb"
OUT_ORIGIN = OUT_DIR / "landmark-facade-origin.json"
OUT_REPORT = OUT_DIR / "landmark-facade-report.json"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
TO_LONLAT = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def pbr(name, color, roughness=0.78, metallic=0.0):
    return trimesh.visual.material.PBRMaterial(name=name, baseColorFactor=color,
        metallicFactor=metallic, roughnessFactor=roughness, doubleSided=True)

def paint(mesh, name, color, roughness=0.78):
    mesh.visual = trimesh.visual.TextureVisuals(material=pbr(name, color, roughness))
    return mesh

def box(center, extents, angle, name, color):
    m = trimesh.creation.box(extents=extents)
    m.apply_transform(trimesh.transformations.rotation_matrix(angle, [0,0,1]))
    m.apply_translation(center)
    return paint(m, name, color)

def cylinder(center, radius, height, name, color, sections=16):
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    m.apply_translation(center)
    return paint(m, name, color)

def museum_polygon():
    # OSM relation 61326 is the Old Legislative Building / National Museum of Fine Arts.
    query = '[out:json][timeout:45];relation(61326);out geom;'
    # Overpass endpoints occasionally return 502 during busy periods. Try several
    # independent public instances with bounded retries before failing the build.
    endpoints = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
        'https://overpass.private.coffee/api/interpreter',
    ]
    headers = {'User-Agent': 'Adam-City/1.0 (landmark architecture research)'}
    errors = []
    payload = None
    for endpoint in endpoints:
        for attempt in range(3):
            try:
                response = requests.post(endpoint, data={'data': query}, timeout=75, headers=headers)
                response.raise_for_status()
                payload = response.json()
                break
            except (requests.RequestException, ValueError) as exc:
                errors.append(f'{endpoint} attempt {attempt + 1}: {exc}')
        if payload is not None:
            break
    if payload is None:
        raise RuntimeError('Unable to retrieve National Museum relation from all Overpass endpoints: ' + ' | '.join(errors))
    rel = next((x for x in payload.get('elements', []) if x.get('type') == 'relation' and x.get('id') == 61326), None)
    if not rel:
        raise RuntimeError('OSM relation 61326 returned no relation geometry')
    lines = {'outer': [], 'inner': []}
    for member in rel.get('members', []):
        if member.get('type') != 'way' or not member.get('geometry'):
            continue
        role = member.get('role') or 'outer'
        if role not in lines:
            continue
        pts = [(p['lon'], p['lat']) for p in member['geometry'] if 'lon' in p and 'lat' in p]
        if len(pts) >= 2:
            lines[role].append(LineString(pts))
    outer = list(polygonize(unary_union(lines['outer'])))
    if not outer:
        raise RuntimeError('Could not polygonize outer rings of OSM relation 61326')
    geom = unary_union(outer)
    inners = list(polygonize(unary_union(lines['inner']))) if lines['inner'] else []
    if inners:
        geom = geom.difference(unary_union(inners))
    if geom.geom_type == 'MultiPolygon':
        geom = max(geom.geoms, key=lambda p: p.area)
    # Validate area in projected meters, not square degrees. The previous
    # check compared lon/lat-degree area to 100 m² and rejected every valid footprint.
    projected = geom_transform(TO_METERS, geom)
    if geom.is_empty or not geom.is_valid or projected.is_empty or projected.area < 100:
        raise RuntimeError(f'National Museum relation geometry failed validity/area checks (projected area={projected.area:.1f} m²)')
    return geom

def facade_overlay(poly, origin, style, fid, height):
    # Build detail on the westernmost substantial edge, the street-facing side.
    ring = list(poly.exterior.coords)
    edges = []
    for a,b in zip(ring[:-1], ring[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        if length >= 12:
            edges.append((a,b,length,math.atan2(dy,dx)))
    if not edges:
        raise RuntimeError(f'{fid}: no usable facade edge')
    minx=poly.bounds[0]
    west=[e for e in edges if min(e[0][0],e[1][0]) <= minx+8]
    a,b,length,angle=max(west or edges,key=lambda e:e[2])
    ux,uy=(b[0]-a[0])/length,(b[1]-a[1])/length
    # Outward normal points west for the selected western edge.
    nx,ny=-uy,ux
    if ((a[0]+b[0])/2) > poly.centroid.x:
        nx,ny=-nx,-ny
    meshes=[]
    stone=style['stone']; trim=style['trim']; roof=style['roof']
    floors=4 if fid == 'relation/61326' else 2
    top=height
    floor_height=top/floors
    # Four giant columns for the museum; PGH facade uses four classical columns too.
    count=4
    for i in range(count):
        t=(i+0.5)/count
        x=a[0]+ux*length*t+nx*0.45-origin[0]
        y=a[1]+uy*length*t+ny*0.45-origin[1]
        meshes.append(cylinder((x,y,floor_height*1.55),0.43,floor_height*2.15,'Corinthian column shaft',stone,20))
        meshes.append(box((x,y,floor_height*0.48),(1.25,1.25,0.32),angle,'Column base',trim))
        meshes.append(box((x,y,floor_height*2.63),(1.45,1.35,0.42),angle,'Column capital and abacus',trim))
    # Deep continuous entablature and cornice above the columns.
    mx=(a[0]+b[0])/2+nx*0.55-origin[0]
    my=(a[1]+b[1])/2+ny*0.55-origin[1]
    meshes.append(box((mx,my,floor_height*2.88),(length*0.92,0.85,0.55),angle,'Entablature',trim))
    meshes.append(box((mx,my,floor_height*3.08),(length*0.96,1.05,0.22),angle,'Projecting cornice',stone))
    # A shallow triangular pediment in a vertical plane facing outward.
    width=min(length*0.75,18.0)
    z0=floor_height*3.15
    z1=z0+(3.4 if fid=='relation/61326' else 2.2)
    base_a=[mx-ux*width/2,my-uy*width/2,z0]
    base_b=[mx+ux*width/2,my+uy*width/2,z0]
    peak=[mx,my,z1]
    # Thin raised triangular outline, kept as three separate moulding beams.
    for p,q in [(base_a,base_b),(base_a,peak),(peak,base_b)]:
        dx,dy,dz=q[0]-p[0],q[1]-p[1],q[2]-p[2]
        seg=math.sqrt(dx*dx+dy*dy+dz*dz)
        beam=trimesh.creation.box(extents=(seg,0.28,0.28))
        # align long X axis with 3D vector
        direction=[dx/seg,dy/seg,dz/seg]
        rot=trimesh.geometry.align_vectors([1,0,0],direction)
        beam.apply_transform(rot)
        beam.apply_translation([(p[0]+q[0])/2-origin[0]+nx*0.5,(p[1]+q[1])/2-origin[1]+ny*0.5,(p[2]+q[2])/2])
        meshes.append(paint(beam,'Pediment moulding',trim))
    # Shallow, repeated window surrounds on the same facade; the base glass stays in the map model.
    win_count=max(4,min(18,int(length/5.0)))
    for floor in range(floors):
        z=floor*floor_height+floor_height*0.55
        if z>top-0.7: continue
        for i in range(win_count):
            t=(i+0.5)/win_count
            x=a[0]+ux*length*t+nx*0.12-origin[0]
            y=a[1]+uy*length*t+ny*0.12-origin[1]
            w=min(1.65,length/win_count*0.58)
            meshes.append(box((x,y,z),(w,0.16,min(1.8,floor_height*0.5)),angle,'Window surround',trim))
    return meshes

def main():
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    if not MAP_FILE.exists():
        raise FileNotFoundError(MAP_FILE)
    data=json.loads(MAP_FILE.read_text(encoding='utf-8'))
    features=data.get('features',[])
    museum=geom_transform(TO_METERS,museum_polygon())
    # Do not place PGH details on the nearby unnamed 133 x 187 m hospital polygon:
    # it is not a verified Cancer Institute footprint and may cover several structures.
    geoms=[('relation/61326',museum,24.0,{'stone':[222,216,202,255],'trim':[197,185,164,255],'roof':[126,80,66,255]})]
    minx=min(g.bounds[0] for _,g,_,_ in geoms); miny=min(g.bounds[1] for _,g,_,_ in geoms)
    maxx=max(g.bounds[2] for _,g,_,_ in geoms); maxy=max(g.bounds[3] for _,g,_,_ in geoms)
    maxz=max(h for _,_,h,_ in geoms)
    origin=((minx+maxx)/2,(miny+maxy)/2,0.0)
    scene=trimesh.Scene()
    generated=[]
    for fid,geom,height,style in geoms:
        parts=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
        part=max(parts,key=lambda p:p.area)
        meshes=facade_overlay(part,origin,style,fid,height)
        for i,m in enumerate(meshes):
            scene.add_geometry(m,geom_name=f'{fid.replace("/","-")}-{i}',node_name=f'{fid.replace("/","-")}-{i}')
        generated.append({'target_id':fid,'mesh_count':len(meshes),'approx_height_m':height,
          'identity_verified':fid=='relation/61326',
          'status':'verified OSM relation identity' if fid=='relation/61326' else 'candidate only: do not treat as confirmed Cancer Institute footprint'})
    if not scene.geometry:
        raise RuntimeError('No landmark facade geometry was generated')
    scene.export(OUT_GLB)
    lon,lat=TO_LONLAT(origin[0],origin[1])
    OUT_ORIGIN.write_text(json.dumps({'longitude':lon,'latitude':lat,'anchor_altitude_m':origin[2],
      'coordinate_system':'EPSG:3857 local meters recentered at longitude/latitude/anchor altitude',
      'origin_method':'Computed from the exact polygons used to generate the landmark GLB'},indent=2)+'\n',encoding='utf-8')
    report={'status':'museum_model_generated_pgh_footprint_pending','source':'OpenStreetMap relation 61326',
      'output_glb':str(OUT_GLB.relative_to(ROOT)),'output_origin':str(OUT_ORIGIN.relative_to(ROOT)),
      'glb_bytes':OUT_GLB.stat().st_size,'targets':generated,
      'pending_targets':[{'name':'PGH Cancer Institute','reference_image':'ermita/buildings/reference_photos/PGH-Cancer-Institute-Building.jpg','status':'waiting_for_verified_building_footprint','candidate_rejected':'way/16554344 is an unnamed 133 x 187 m polygon and is not safe to treat as the Cancer Institute'}],
      'limitations':['Facade details are stylized architectural overlays, not photogrammetry or surveyed dimensions.',
      'PGH is intentionally excluded until its exact footprint is verified; no guessed facade is attached to a nearby building.',
      'Base building mass remains supplied by the existing map layer.']}
    OUT_REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
