#!/usr/bin/env python3
"""Export the current Ermita preview's geographic layers as one aligned GLB.

Uses committed OSM building footprints, OSM road centerlines, and the committed
Copernicus DEM crop. All layers are projected together into EPSG:3857, then
recentered once as a single scene so roads/buildings/terrain stay aligned.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path

import numpy as np
import rasterio
import trimesh
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, LineString, MultiLineString, GeometryCollection
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
MAPS = ROOT / "ermita" / "maps" / "generated"
THREED = ROOT / "ermita" / "3d"
OUT = THREED / "exports" / "adam-city-complete.glb"
BUILDINGS = MAPS / "ermita-building-footprints.geojson"
ROADS = MAPS / "ermita-road-network.geojson"
DEM = THREED / "terrain" / "ermita-copernicus-dem-cropped.tif"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
FROM_METERS = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform

def tags_of(feature):
    p = feature.get("properties") or {}
    tags = p.get("tags")
    if isinstance(tags, dict):
        return {**p, **tags}
    return p

def height_of(tags):
    try:
        h = float(str(tags.get("height", "")).replace("m", "").strip())
        if 2 <= h <= 500:
            return h
    except (TypeError, ValueError):
        pass
    try:
        levels = float(tags.get("building:levels") or tags.get("levels"))
        if 1 <= levels <= 100:
            return levels * 3.2
    except (TypeError, ValueError):
        pass
    return 9.6

def polygon_parts(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if isinstance(g, GeometryCollection):
        return [p for x in g.geoms for p in polygon_parts(x)]
    return []

def line_parts(g):
    if isinstance(g, LineString):
        return [g]
    if isinstance(g, (MultiLineString, GeometryCollection)):
        return [p for x in g.geoms for p in line_parts(x)]
    return []

def main():
    for p in (BUILDINGS, ROADS, DEM):
        if not p.exists():
            raise FileNotFoundError(f"Required committed preview source missing: {p}")
    building_data = json.loads(BUILDINGS.read_text(encoding="utf-8"))
    road_data = json.loads(ROADS.read_text(encoding="utf-8"))
    terrain_mesh = None
    with rasterio.open(DEM) as ds:
        # Limit mesh density while retaining the elevation surface's regional shape.
        step = max(1, int(max(ds.width, ds.height) / 500))
        arr = ds.read(1, out_shape=(max(2, ds.height // step), max(2, ds.width // step)), masked=True)
        transform = ds.transform * rasterio.Affine.scale(ds.width / arr.shape[1], ds.height / arr.shape[0])
        xs, ys = np.meshgrid(np.arange(arr.shape[1]), np.arange(arr.shape[0]))
        xx = transform.c + (xs + 0.5) * transform.a + (ys + 0.5) * transform.b
        yy = transform.f + (xs + 0.5) * transform.d + (ys + 0.5) * transform.e
        if ds.crs and ds.crs.to_string() != "EPSG:4326":
            transformer = Transformer.from_crs(ds.crs, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(xx, yy)
        else:
            lon, lat = xx, yy
        mx, my = TO_METERS(np.asarray(lon), np.asarray(lat))
        z = np.asarray(arr.filled(np.nan), dtype=float)
        valid = np.isfinite(z)
        # Triangulate each grid cell only when its four samples are valid.
        verts = np.column_stack([mx.ravel(), my.ravel(), np.nan_to_num(z, nan=0.0).ravel()])
        faces = []
        rows, cols = z.shape
        for r in range(rows - 1):
            for c in range(cols - 1):
                a = r * cols + c; b = a + 1; d = (r + 1) * cols + c; e = d + 1
                if valid[r,c] and valid[r,c+1] and valid[r+1,c] and valid[r+1,c+1]:
                    faces.extend(((a,d,b),(b,d,e)))
        terrain_mesh = trimesh.Trimesh(vertices=verts, faces=np.asarray(faces, dtype=np.int64), process=False)
        terrain_mesh.visual.face_colors = [110, 133, 91, 255]

    # DEM ground elevation sampler in the same projected coordinate system.
    with rasterio.open(DEM) as ds:
        def ground_z(x, y):
            lon, lat = FROM_METERS(x, y)
            sx, sy = (Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True).transform(lon, lat)
                      if ds.crs and ds.crs.to_string() != "EPSG:4326" else (lon, lat))
            try:
                v = next(ds.sample([(sx, sy)]))[0]
                return float(v) if np.isfinite(v) and v > -100 else 0.0
            except Exception:
                return 0.0

    scene = trimesh.Scene()
    scene.add_geometry(terrain_mesh, node_name="Copernicus terrain surface", geom_name="terrain")
    # Aggregate features into a small number of meshes to keep the GLB compact.
    building_meshes = []
    road_meshes = []
    building_count = 0
    for f in building_data.get("features", []):
        if not f.get("geometry"):
            continue
        try:
            g = geom_transform(TO_METERS, shape(f["geometry"]))
            tags = tags_of(f)
            height = height_of(tags)
            color_text = str(tags.get("building:colour") or tags.get("building:color") or "").lower()
            if "white" in color_text: color = [210, 207, 194, 255]
            elif "red" in color_text: color = [156, 99, 82, 255]
            elif "blue" in color_text: color = [117, 143, 158, 255]
            else: color = [184, 177, 160, 255]
            for poly in polygon_parts(g):
                if poly.is_empty or not poly.is_valid or poly.area < 4:
                    continue
                mesh = trimesh.creation.extrude_polygon(poly, height, engine="earcut")
                mesh.apply_translation([0, 0, ground_z(poly.centroid.x, poly.centroid.y)])
                mesh.visual.face_colors = color
                building_meshes.append(mesh)
                building_count += 1
        except Exception as e:
            print("Skipping building:", e)

    if building_meshes:
        scene.add_geometry(trimesh.util.concatenate(building_meshes), node_name="OSM buildings", geom_name="buildings")
    road_count = 0
    for f in road_data.get("features", []):
        if not f.get("geometry"):
            continue
        try:
            g = geom_transform(TO_METERS, shape(f["geometry"]))
            tags = tags_of(f)
            highway = str(tags.get("highway", "")).lower()
            width = 6.0 if highway in {"primary", "trunk", "secondary"} else 4.0 if highway in {"tertiary", "residential", "unclassified"} else 2.0 if highway in {"footway", "path", "steps", "pedestrian"} else 3.0
            name = str(tags.get("name") or tags.get("ref") or f"road-{road_count}")
            for line in line_parts(g):
                if line.length < 1:
                    continue
                poly = line.buffer(width / 2, cap_style="flat", join_style="mitre")
                if poly.is_empty or poly.area < 1:
                    continue
                mesh = trimesh.creation.extrude_polygon(poly, 0.12, engine="earcut")
                mesh.apply_translation([0, 0, ground_z(line.centroid.x, line.centroid.y) + 0.04])
                mesh.visual.face_colors = [67, 69, 72, 255]
                road_meshes.append(mesh)
                road_count += 1
        except Exception as e:
            print("Skipping road:", e)

    if road_meshes:
        scene.add_geometry(trimesh.util.concatenate(road_meshes), node_name="OSM roads and paths", geom_name="roads")
    # One shared origin is essential: never recenter each source GLB independently.
    bounds = scene.bounds
    center_xy = (bounds[0, :2] + bounds[1, :2]) / 2
    base_z = float(np.nanmin(terrain_mesh.vertices[:, 2]))
    for geom in scene.geometry.values():
        geom.apply_translation([-center_xy[0], -center_xy[1], -base_z])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(scene.export(file_type="glb"))
    report = {
        "output": str(OUT.relative_to(ROOT)),
        "buildings_exported": building_count,
        "road_segments_exported": road_count,
        "terrain_vertices": int(len(terrain_mesh.vertices)),
        "terrain_triangles": int(len(terrain_mesh.faces)),
        "coordinate_system": "EPSG:3857 metres, shared scene origin; Z relative to minimum DEM elevation",
        "sources": {
            "buildings": str(BUILDINGS.relative_to(ROOT)),
            "roads": str(ROADS.relative_to(ROOT)),
            "terrain": str(DEM.relative_to(ROOT)),
        },
        "limitations": [
            "This is a geometry export of the committed preview source layers, not a screen capture.",
            "Streamed Esri imagery tiles are not embedded; they are not committed local assets and redistribution is restricted.",
            "Building heights use source height/levels when available and a documented 9.6 m fallback otherwise.",
            "Road widths are visualization estimates based on highway class; road centerlines come from OSM.",
            "Procedural facade placeholder GLBs are not fused because they were independently recentered and cannot be safely aligned without original transforms."
        ],
        "license": "OpenStreetMap contributors, ODbL 1.0; Copernicus DEM attribution per source report."
    }
    (OUT.parent / "adam-city-complete-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()

# Build trigger: export current committed preview geometry as one aligned GLB.
