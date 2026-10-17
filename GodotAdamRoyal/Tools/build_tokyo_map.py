#!/usr/bin/env python3
"""Build a lightweight, real-world central Tokyo 3D blockout from OpenStreetMap data.
Data source: OpenStreetMap contributors, ODbL. This does not scrape Google Maps.
"""
import json, math, os, sys, time
from pathlib import Path
import requests

CENTER_LAT, CENTER_LON = 35.6595, 139.7005
RADIUS_M = 1400
OUT = Path(__file__).resolve().parents[1] / "assets" / "cities" / "tokyo"
OUT.mkdir(parents=True, exist_ok=True)
DATA = OUT / "tokyo_osm.json"
OBJ = OUT / "Tokyo.obj"
REPORT = OUT / "Tokyo-report.json"

def xy(lat, lon):
    # Local equirectangular coordinates in metres around Tabarbour.
    return ((lon-CENTER_LON)*111320*math.cos(math.radians(CENTER_LAT)), (lat-CENTER_LAT)*110540)

query = f"""[out:json][timeout:180];(
 way(around:{RADIUS_M},{CENTER_LAT},{CENTER_LON})[building];
 way(around:{RADIUS_M},{CENTER_LAT},{CENTER_LON})[highway];
);out body;>;out skel qt;"""
endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
data = None
errors = []
for endpoint in endpoints:
    for attempt in range(3):
        try:
            response = requests.post(endpoint, data={"data": query}, timeout=210,
                                     headers={"User-Agent":"AdamRoyal-game-map-builder/1.0 (OpenStreetMap attribution included)"})
            response.raise_for_status()
            candidate = response.json()
            if len(candidate.get("elements", [])) < 100:
                raise RuntimeError("Overpass returned too few map elements")
            data = candidate
            break
        except Exception as exc:
            errors.append(f"{endpoint}: {exc}")
            time.sleep(2 + attempt * 2)
    if data:
        break
if not data:
    raise RuntimeError("Could not download Tokyo OSM data: " + " | ".join(errors))
DATA.write_text(json.dumps(data, separators=(",",":")), encoding="utf-8")
nodes = {e["id"]: (e["lat"],e["lon"]) for e in data["elements"] if e["type"]=="node"}
ways = [e for e in data["elements"] if e["type"]=="way"]
vertices, faces, materials = [], [], []
building_count, road_count = 0, 0

def add_vertex(x,y,z):
    vertices.append((x,y,z))
    return len(vertices)

def add_quad(a,b,c,d, mat):
    faces.append((a,b,c,mat)); faces.append((a,c,d,mat))

# Export metres in Godot's X/Z ground plane and Y vertical axis.
for way in ways:
    ids = way.get("nodes", [])
    coords = [xy(*nodes[n]) for n in ids if n in nodes]
    tags = way.get("tags", {})
    if len(coords) < 2:
        continue
    if "building" in tags and len(coords) >= 4 and ids[0] == ids[-1]:
        ring = coords[:-1]
        if len(ring) < 3: continue
        # Keep building footprints compact and use tagged levels where available.
        try: levels = max(1, min(30, int(float(tags.get("building:levels", 2)))))
        except (ValueError, TypeError): levels = 2
        height = max(3.0, min(90.0, float(tags.get("height", levels*3.2)) if str(tags.get("height","")).replace(".","",1).isdigit() else levels*3.2))
        base = [add_vertex(x,0,z) for x,z in ring]
        top = [add_vertex(x,height,z) for x,z in ring]
        # Roof fan; OSM polygons are typically simple footprints.
        for i in range(1,len(ring)-1):
            faces.append((top[0],top[i],top[i+1],"building_roof"))
            faces.append((base[0],base[i+1],base[i],"building_wall"))
        for i in range(len(ring)):
            j=(i+1)%len(ring)
            add_quad(base[i],base[j],top[j],top[i],"building_wall")
        building_count += 1
    elif "highway" in tags:
        # Roads as raised, thin strips with width by road class.
        highway = tags["highway"]
        width = 7.0 if highway in ("primary","trunk","secondary") else 4.5 if highway in ("tertiary","residential","unclassified") else 2.5
        for (x1,z1),(x2,z2) in zip(coords,coords[1:]):
            dx,dz=x2-x1,z2-z1; length=math.hypot(dx,dz)
            if length < 0.5: continue
            px,pz=(-dz/length*width/2, dx/length*width/2)
            a=add_vertex(x1+px,0.06,z1+pz); b=add_vertex(x1-px,0.06,z1-pz)
            c=add_vertex(x2-px,0.06,z2-pz); d=add_vertex(x2+px,0.06,z2+pz)
            add_quad(a,b,c,d,"road")
        road_count += 1

if building_count < 100 or road_count < 50 or len(vertices) < 1000:
    raise RuntimeError(f"Tokyo map quality gate failed: buildings={building_count}, roads={road_count}, vertices={len(vertices)}")
with OBJ.open("w", encoding="utf-8") as f:
    f.write("# Tokyo, Japan - OpenStreetMap contributors (ODbL)\n")
    f.write("mtllib Tokyo.mtl\n")
    for x,y,z in vertices: f.write(f"v {x:.3f} {y:.3f} {z:.3f}\n")
    last = None
    for a,b,c,mat in faces:
        if mat != last:
            f.write(f"usemtl {mat}\n"); last=mat
        f.write(f"f {a} {b} {c}\n")
with (OUT/"Tabarbour.mtl").open("w", encoding="utf-8") as f:
    f.write("newmtl building_wall\nKd 0.67 0.64 0.59\n")
    f.write("newmtl building_roof\nKd 0.48 0.45 0.41\n")
    f.write("newmtl road\nKd 0.18 0.19 0.20\n")
report = {"region":"Tabarbour, Amman, Jordan","center":{"lat":CENTER_LAT,"lon":CENTER_LON},"radius_m":RADIUS_M,
          "source":"OpenStreetMap contributors","license":"ODbL 1.0","buildings":building_count,
          "road_ways":road_count,"vertices":len(vertices),"faces":len(faces),"obj_bytes":OBJ.stat().st_size,
          "raw_osm_file":DATA.name}
REPORT.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(f"TOKYO_MAP_BUILD_PASS buildings={building_count} road_ways={road_count} vertices={len(vertices)} faces={len(faces)} bytes={OBJ.stat().st_size}")
