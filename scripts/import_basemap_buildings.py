#!/usr/bin/env python3
"""Import OpenFreeMap building footprints as a separate dataset; never overwrite OSM geometry.

Basemap geometry and render heights remain explicitly identified as OpenFreeMap/OpenMapTiles
source data. Any spatially matched OSM attributes are supplementary and carry match-distance
metadata; the original OSM snapshot is read-only.
"""
import json
import math
import os
import sys
import urllib.request
from collections import defaultdict

import mapbox_vector_tile
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "ermita/maps/external/ermita-basemap-building-footprints.geojson")
OSM_INPUT = os.path.join(REPO, "backup/ermita/maps/generated/ermita-building-footprints.geojson")
# Ermita + Malate working area
WEST, SOUTH, EAST, NORTH = 120.965, 14.555, 121.005, 14.605
ZOOM = 14
EXTENT = 4096

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Adam-City-Basemap-Importer/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))

def get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Adam-City-Basemap-Importer/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

def tile_x(lon, z):
    return int((lon + 180.0) / 360.0 * (2 ** z))

def tile_y(lat, z):
    lat = max(-85.05112878, min(85.05112878, lat))
    rad = math.radians(lat)
    return int((1.0 - math.asinh(math.tan(rad)) / math.pi) / 2.0 * (2 ** z))

def tile_xy_to_lonlat(tx, ty, x, y, z):
    n = 2 ** z
    lon = (tx + x / EXTENT) / n * 360.0 - 180.0
    merc_y = math.pi * (1.0 - 2.0 * (ty + y / EXTENT) / n)
    lat = math.degrees(math.atan(math.sinh(merc_y)))
    return [lon, lat]

def convert_coords(coords, tx, ty):
    if isinstance(coords, (list, tuple)) and len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
        return tile_xy_to_lonlat(tx, ty, coords[0], coords[1], ZOOM)
    return [convert_coords(c, tx, ty) for c in coords]

def center(geom):
    c = geom.centroid
    return (c.x, c.y)

def meters(a, b):
    lat = math.radians((a[1] + b[1]) / 2)
    return math.hypot((a[0] - b[0]) * 111320 * math.cos(lat), (a[1] - b[1]) * 110574)

def main():
    tilejson = get_json("https://tiles.openfreemap.org/planet/latest")
    templates = tilejson.get("tiles") or ["https://tiles.openfreemap.org/planet/latest/{z}/{x}/{y}.pbf"]
    template = templates[0]
    z = min(ZOOM, int(tilejson.get("maxzoom", ZOOM)))
    xmin, xmax = tile_x(WEST, z), tile_x(EAST, z)
    ymin, ymax = tile_y(NORTH, z), tile_y(SOUTH, z)
    fragments = defaultdict(list)
    props_by_key = {}
    fetched = 0
    for tx in range(xmin, xmax + 1):
        for ty in range(ymin, ymax + 1):
            url = template.replace("{z}", str(z)).replace("{x}", str(tx)).replace("{y}", str(ty))
            try:
                decoded = mapbox_vector_tile.decode(get_bytes(url), default_options={"y_coord_down": True})
            except Exception as e:
                print(f"Tile failed {z}/{tx}/{ty}: {e}", file=sys.stderr)
                continue
            fetched += 1
            layer = decoded.get("building")
            if not layer:
                continue
            for feat in layer.get("features", []):
                geom_obj = feat.get("geometry")
                if not geom_obj or geom_obj.get("type") not in ("Polygon", "MultiPolygon"):
                    continue
                props = dict(feat.get("properties") or {})
                h = props.get("render_height")
                try:
                    h = float(h)
                except (TypeError, ValueError):
                    continue
                if not (2 <= h <= 500):
                    continue
                converted = {"type": geom_obj["type"], "coordinates": convert_coords(geom_obj["coordinates"], tx, ty)}
                try:
                    geom = shape(converted)
                    if geom.is_empty or not geom.is_valid:
                        geom = geom.buffer(0)
                    if geom.is_empty:
                        continue
                except Exception:
                    continue
                fid = feat.get("id")
                # Vector feature IDs are stable across tiles in the same OpenFreeMap release.
                key = f"id:{fid}" if fid is not None else "geom:" + str(round(geom.centroid.x, 5)) + ":" + str(round(geom.centroid.y, 5)) + ":" + str(round(h, 1))
                fragments[key].append(geom)
                props_by_key[key] = props
    if not fragments:
        raise RuntimeError("No Basemap building polygons with render_height were extracted; refusing to overwrite OSM data.")

    basemap = []
    for key, geoms in fragments.items():
        geom = unary_union(geoms)
        if geom.is_empty:
            continue
        p = props_by_key[key]
        basemap.append({"geometry": geom, "properties": p, "center": center(geom), "key": key})
    with open(OSM_INPUT, "r", encoding="utf-8") as f:
        old = json.load(f)
    osm_features = old.get("features", [])
    osm_polys = []
    for f in osm_features:
        try:
            g = shape(f["geometry"])
            if not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon"):
                osm_polys.append((f, g, center(g)))
        except Exception:
            pass

    output = []
    matched = 0
    for b in basemap:
        best, best_d = None, float("inf")
        bp = b["properties"]
        # Prefer an exact OSM ID if the vector tile provides one, otherwise match nearby OSM attributes.
        bid = str(bp.get("osm_id") or bp.get("osm_way_id") or bp.get("id") or "")
        for of, og, oc in osm_polys:
            op = of.get("properties") or {}
            oid = str(op.get("id") or op.get("osm_id") or op.get("osm_feature_id") or "").replace("way/", "")
            if bid and oid and bid == oid.replace("node/", "").replace("relation/", ""):
                best, best_d = (of, og, oc), 0
                break
            d = meters(b["center"], oc)
            if d < best_d:
                best, best_d = (of, og, oc), d
        op = (best[0].get("properties") or {}) if best and best_d <= 12 else {}
        tags = dict(op.get("tags") or {})
        tags["building"] = str(bp.get("building") or bp.get("class") or tags.get("building") or "yes")
        tags["height"] = str(bp["render_height"])
        tags["min_height"] = str(bp.get("render_min_height") or 0)
        if bp.get("colour") or bp.get("color"):
            tags["building:colour"] = str(bp.get("colour") or bp.get("color"))
        if bp.get("name"):
            tags["name"] = str(bp["name"])
        props = dict(op)
        props.update({
            "tags": tags,
            "osm_feature_id": op.get("osm_feature_id") or ((str(op.get("type")) + "/" + str(op.get("id"))) if op.get("type") and op.get("id") else None),
            "basemap_properties": bp,
            "basemap_render_height": float(bp["render_height"]),
            "basemap_render_min_height": float(bp.get("render_min_height") or 0),
            "adam_height_m": float(bp["render_height"]),
            "basemap_geometry_authoritative": True,
            "basemap_source": "OpenFreeMap / OpenMapTiles vector tiles",
            "basemap_source_feature_id": b["key"],
            "osm_attributes_match_distance_m": round(best_d, 2) if best and best_d <= 12 else None
        })
        if props.get("name") is None and tags.get("name"):
            props["name"] = tags["name"]
        # Keep the authoritative Basemap outline, but simplify tile-edge detail and round
        # coordinates to six decimals (~0.1 m) so mobile browsers can parse the dataset.
        compact_geom = b["geometry"].simplify(0.000008, preserve_topology=True)
        if compact_geom.is_empty:
            continue
        def rounded_coords(value):
            if isinstance(value, (list, tuple)):
                if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                    return [round(float(value[0]), 6), round(float(value[1]), 6)] + [value[i] for i in range(2, len(value))]
                return [rounded_coords(v) for v in value]
            return value
        compact_mapping = mapping(compact_geom)
        compact_mapping["coordinates"] = rounded_coords(compact_mapping["coordinates"])
        output.append({"type": "Feature", "properties": props, "geometry": compact_mapping})
        if best and best_d <= 12:
            matched += 1

    result = {
        "type": "FeatureCollection",
        "name": "Ermita buildings — Basemap-authoritative geometry and heights merged with OSM attributes",
        "source": "OpenFreeMap/OpenMapTiles vector tiles; OSM attributes retained only where spatially matched",
        "attribution": "OpenFreeMap © OpenMapTiles; data from OpenStreetMap",
        "license": "OpenStreetMap data ODbL 1.0; OpenFreeMap/OpenMapTiles attribution required",
        "basemap_zoom": z,
        "tiles_fetched": fetched,
        "basemap_building_features": len(output),
        "osm_attribute_matches": matched,
        "features": output
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"Fetched {fetched} tiles at z={z}")
    print(f"Wrote {len(output)} separate Basemap building geometries; retained supplementary OSM attributes on {matched} spatial matches. Original OSM footprints were not modified.")
    print(f"Wrote {OUT} ({os.path.getsize(OUT):,} bytes)")

if __name__ == "__main__":
    main()
