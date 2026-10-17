#!/usr/bin/env python3
"""Build a small real-world Manila district GLB from OpenStreetMap footprints and roads."""
from __future__ import annotations
import json, math, os, sys, time
from pathlib import Path
import requests
import trimesh
from shapely.geometry import Polygon, LineString
from shapely.ops import triangulate

# Central Manila: Intramuros / Ermita / southern Binondo edge. Deliberately bounded
# to keep the first playable district manageable.
S, W, N, E = 14.575, 120.965, 14.600, 120.990
OUT = Path("StandaloneBattleRoyale/Content/Maps/Manila-Central-District.glb")
OUT.parent.mkdir(parents=True, exist_ok=True)
QUERY = f"""[out:json][timeout:180];
(
 way[building]({S},{W},{N},{E});
 way[highway]({S},{W},{N},{E});
);
out body; >; out skel qt;"""
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
def fetch():
    last = None
    for endpoint in ENDPOINTS:
        try:
            r = requests.post(endpoint, data={"data": QUERY}, timeout=210,
                              headers={"User-Agent":"AdamRoyal-Research-Map/1.0"})
            r.raise_for_status()
            data = r.json()
            if data.get("elements"):
                return data
            last = RuntimeError("Overpass returned no elements")
        except Exception as exc:
            last = exc
            time.sleep(2)
    raise RuntimeError(f"Could not download OSM district from any Overpass endpoint: {last}")

def main():
    data = fetch()
    nodes = {e["id"]:(e["lon"],e["lat"]) for e in data["elements"] if e["type"]=="node"}
    ways = [e for e in data["elements"] if e["type"]=="way"]
    # Local metric coordinates, centered on the requested real-world district.
    lat0, lon0 = (S+N)/2, (W+E)/2
    def xy(node_id):
        lon,lat = nodes[node_id]
        return ((lon-lon0)*111320*math.cos(math.radians(lat0)), (lat-lat0)*110540)
    scene = trimesh.Scene()
    building_count = road_count = 0
    for way in ways:
        ids = way.get("nodes", [])
        if len(ids) < 2 or any(i not in nodes for i in ids):
            continue
        pts = [xy(i) for i in ids]
        tags = way.get("tags", {})
        if "building" in tags and len(pts) >= 4 and ids[0] == ids[-1]:
            try:
                poly = Polygon(pts).buffer(0)
                if poly.is_empty or poly.area < 12:
                    continue
                levels = tags.get("building:levels")
                try: height = float(levels)*3.1 if levels else float(tags.get("height","").replace(" m",""))
                except (ValueError, TypeError): height = 9.3
                height = min(max(height, 3.2), 85)
                # Triangulate footprint, then extrude each polygon as a solid mesh.
                parts = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
                for part in parts:
                    if part.area < 8: continue
                    mesh = trimesh.creation.extrude_polygon(part, height)
                    mesh.apply_translation([0,0,0])
                    mesh.visual.face_colors = [174, 165, 148, 255]
                    scene.add_geometry(mesh, node_name=f"building_{building_count}")
                    building_count += 1
            except Exception:
                continue
        elif "highway" in tags and len(pts) >= 2:
            try:
                line = LineString(pts).simplify(1.2)
                if line.length < 8: continue
                width = 8.0 if tags["highway"] in ("primary","secondary","trunk","tertiary") else 4.5
                road = line.buffer(width/2, cap_style="flat", join_style="mitre")
                if road.is_empty: continue
                mesh = trimesh.creation.extrude_polygon(road, 0.12)
                mesh.visual.face_colors = [48, 51, 56, 255]
                scene.add_geometry(mesh, node_name=f"road_{road_count}")
                road_count += 1
            except Exception:
                continue
    if building_count < 30 or road_count < 15:
        raise RuntimeError(f"OSM geometry below quality gate: buildings={building_count}, roads={road_count}")
    # Ground plane gives a readable continuous playable base.
    ground = trimesh.creation.box(extents=[3000, 3000, 0.2])
    ground.apply_translation([0,0,-0.16])
    ground.visual.face_colors = [83, 103, 75, 255]
    scene.add_geometry(ground, node_name="district_ground")
    scene.export(str(OUT), file_type="glb")
    check = trimesh.load(str(OUT), force="scene")
    if len(check.geometry) < 2 or OUT.stat().st_size < 100_000:
        raise RuntimeError("Exported GLB failed structural/size validation")
    report = {
        "source":"OpenStreetMap contributors",
        "attribution":"© OpenStreetMap contributors",
        "license":"ODbL 1.0",
        "bounds":{"south":S,"west":W,"north":N,"east":E},
        "buildings":building_count,"roads":road_count,
        "mesh_objects":len(check.geometry),"glb_bytes":OUT.stat().st_size,
        "note":"Real OSM footprints and road alignments; procedural extrusions, not photogrammetry."
    }
    OUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
if __name__ == "__main__":
    main()
