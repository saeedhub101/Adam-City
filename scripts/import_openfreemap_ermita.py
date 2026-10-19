#!/usr/bin/env python3
"""Download OpenFreeMap/OpenMapTiles vector tiles for Ermita and catalogue all 16 schema layers."""
import concurrent.futures, json, math, os, pathlib, sys, time
import requests
import mapbox_vector_tile

ROOT = pathlib.Path("ermita/maps/sources/openfreemap")
RAW = ROOT / "vector-tiles"
LAYERS_DIR = ROOT / "layers"
STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"
GEOCODER = "https://nominatim.openstreetmap.org/search"
UA = "Adam-City OpenFreeMap offline-area-import/1.0 (GitHub repository saeedhub101/Adam-City)"
MIN_ZOOM = int(os.environ.get("MIN_ZOOM", "10"))
MAX_ZOOM = int(os.environ.get("MAX_ZOOM", "16"))
MAX_TILES = 3000
MAX_BYTES = 50 * 1024 * 1024
LAYER_NAMES = [
    "aerodrome_label", "aeroway", "boundary", "building", "housenumber",
    "landcover", "landuse", "mountain_peak", "park", "place", "poi",
    "transportation", "transportation_name", "water", "water_name", "waterway"
]
session = requests.Session()
session.headers.update({"User-Agent": UA})

def get_json(url, **kwargs):
    r = session.get(url, timeout=60, **kwargs)
    r.raise_for_status()
    return r.json()

def find_area():
    data = get_json(GEOCODER, params={"q":"Ermita, Manila, Metro Manila, Philippines",
                                     "format":"jsonv2","polygon_geojson":1,"limit":5})
    if not data:
        raise RuntimeError("Nominatim could not resolve Ermita, Manila.")
    candidates = sorted(data, key=lambda x: ("ermita" not in x.get("display_name","").lower(),
                                               -float(x.get("importance",0))))
    chosen = candidates[0]
    bbox = [float(v) for v in chosen["boundingbox"]] # south, north, west, east
    geom = chosen.get("geojson")
    if not geom:
        raise RuntimeError("Ermita geocoder result did not include a boundary geometry.")
    return chosen, bbox, geom

def xyz(lon, lat, z):
    lat = max(-85.05112878, min(85.05112878, lat))
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return max(0,min(n-1,x)), max(0,min(n-1,y))

def tile_url_from_style():
    style = get_json(STYLE_URL)
    for source in style.get("sources", {}).values():
        if source.get("type") != "vector":
            continue
        if source.get("tiles"):
            return source["tiles"][0]
        if source.get("url"):
            tilejson = get_json(source["url"])
            if tilejson.get("tiles"):
                return tilejson["tiles"][0]
    raise RuntimeError("Could not find a vector tile URL in the OpenFreeMap Liberty style.")

def lonlat(z, x, y, extent, px, py):
    n = 2 ** z
    gx = x + px / extent
    gy = y + py / extent
    lon = gx / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * gy / n))))
    return [lon, lat]

def transform_coords(coords, z, x, y, extent):
    if not isinstance(coords, (list, tuple)):
        return coords
    if len(coords) >= 2 and isinstance(coords[0], (int,float)) and isinstance(coords[1], (int,float)):
        return lonlat(z,x,y,extent,coords[0],coords[1]) + list(coords[2:])
    return [transform_coords(c,z,x,y,extent) for c in coords]

def convert_geometry(geometry, z, x, y, extent):
    if not geometry:
        return None
    return {"type": geometry["type"],
            "coordinates": transform_coords(geometry.get("coordinates"), z, x, y, extent)}

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    LAYERS_DIR.mkdir(parents=True, exist_ok=True)
    area, bbox, polygon = find_area()
    south, north, west, east = bbox
    tile_set = set()
    for z in range(MIN_ZOOM, MAX_ZOOM + 1):
        x0,y1 = xyz(west,south,z)
        x1,y0 = xyz(east,north,z)
        for x in range(min(x0,x1),max(x0,x1)+1):
            for y in range(min(y0,y1),max(y0,y1)+1):
                tile_set.add((z,x,y))
    tiles = sorted(tile_set)
    if len(tiles) > MAX_TILES:
        raise RuntimeError(f"Tile coverage needs {len(tiles)} tiles; safety limit is {MAX_TILES}. Reduce zoom range.")
    tile_template = tile_url_from_style()
    (ROOT / "area-boundary.geojson").write_text(json.dumps({
        "type":"FeatureCollection","features":[{"type":"Feature","properties":{
            "source":"Nominatim geocoding result for Ermita, Manila, Metro Manila, Philippines",
            "display_name":area.get("display_name"),"osm_type":area.get("osm_type"),
            "osm_id":area.get("osm_id"),"boundingbox_south_north_west_east":bbox
        },"geometry":polygon}]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT / "source-metadata.json").write_text(json.dumps({
        "source_name":"OpenFreeMap / OpenMapTiles","style_url":STYLE_URL,"tilejson_tile_template":tile_template,
        "underlying_data":"OpenStreetMap contributors","attribution":"OpenFreeMap © OpenMapTiles Data from OpenStreetMap",
        "schema_url":"https://openmaptiles.org/docs/schema/","area_query":"Ermita, Manila, Metro Manila, Philippines",
        "area_display_name":area.get("display_name"),"area_osm_type":area.get("osm_type"),"area_osm_id":area.get("osm_id"),
        "bbox_south_north_west_east":bbox,"min_zoom":MIN_ZOOM,"max_zoom":MAX_ZOOM,
        "tile_count_planned":len(tiles),"tile_limit":MAX_TILES,"download_limit_bytes":MAX_BYTES,
        "layers":LAYER_NAMES,"retrieved_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    layer_handles = {name: (LAYERS_DIR / (name + ".geojsonl")).open("w",encoding="utf-8") for name in LAYER_NAMES}
    tile_index = []
    total_bytes = 0
    errors = []
    def download(item):
        z,x,y = item
        url = tile_template.replace("{z}",str(z)).replace("{x}",str(x)).replace("{y}",str(y))
        r = session.get(url,timeout=90)
        if r.status_code == 404:
            return item, None, 0, "empty"
        r.raise_for_status()
        return item, r.content, len(r.content), None
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for item, content, size, error in pool.map(download, tiles):
                z,x,y = item
                if error:
                    if error != "empty": errors.append({"z":z,"x":x,"y":y,"error":error})
                    tile_index.append({"z":z,"x":x,"y":y,"status":error})
                    continue
                total_bytes += size
                if total_bytes > MAX_BYTES:
                    raise RuntimeError(f"Download exceeded {MAX_BYTES} bytes safety limit.")
                raw_path = RAW / str(z) / str(x) / (str(y)+".pbf")
                raw_path.parent.mkdir(parents=True,exist_ok=True)
                raw_path.write_bytes(content)
                counts = {}
                try:
                    decoded = mapbox_vector_tile.decode(content)
                    for name, layer in decoded.items():
                        if name not in layer_handles:
                            continue
                        extent = int(layer.get("extent",4096))
                        feats = layer.get("features",[])
                        counts[name] = len(feats)
                        for f in feats:
                            record = {"type":"Feature","id":f.get("id"),
                                      "geometry":convert_geometry(f.get("geometry"),z,x,y,extent),
                                      "properties":f.get("properties") or {},
                                      "_source":{"provider":"OpenFreeMap","schema":"OpenMapTiles",
                                                 "tile":{"z":z,"x":x,"y":y,"path":str(raw_path)},
                                                 "layer":name,"extent":extent}}
                            layer_handles[name].write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
                except Exception as exc:
                    errors.append({"z":z,"x":x,"y":y,"error":"decode: "+str(exc)})
                tile_index.append({"z":z,"x":x,"y":y,"status":"downloaded","bytes":size,
                                   "path":str(raw_path),"layer_feature_counts":counts})
    finally:
        for handle in layer_handles.values():
            handle.close()
    summary = {"source":"OpenFreeMap / OpenMapTiles","area":area.get("display_name"),
        "tile_template":tile_template,"zoom_range":[MIN_ZOOM,MAX_ZOOM],"planned_tiles":len(tiles),
        "downloaded_tiles":sum(1 for t in tile_index if t["status"]=="downloaded"),
        "empty_tiles":sum(1 for t in tile_index if t["status"]=="empty"),
        "total_pbf_bytes":total_bytes,"layer_feature_counts":{},"layer_files":{},"errors":errors,
        "raw_tile_index":"tile-index.json","retrieved_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    for name in LAYER_NAMES:
        path = LAYERS_DIR/(name+".geojsonl")
        with path.open(encoding="utf-8") as handle:
            count = sum(1 for line in handle if line.strip())
        summary["layer_feature_counts"][name]=count
        summary["layer_files"][name]=str(path)
    (ROOT/"tile-index.json").write_text(json.dumps(tile_index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"import-report.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# OpenFreeMap / OpenMapTiles — layer catalogue","",
           f"- Area: {area.get('display_name')}","- Raw tiles: vector-tiles/{z}/{x}/{y}.pbf",
           "- Decoded layer records: one GeoJSON Feature per line; geometry coordinates are WGS84 longitude/latitude.",
           "- Every record includes _source.tile and _source.layer so it can be traced to the original PBF tile.",
           "- Tile coordinates and exact source URL are recorded in source-metadata.json and tile-index.json.",
           "- Attribution: OpenFreeMap © OpenMapTiles Data from OpenStreetMap.","",
           "| Layer | Features extracted | File |","|---|---:|---|"]
    for name in LAYER_NAMES:
        lines.append(f"| {name} | {summary['layer_feature_counts'][name]} | layers/{name}.geojsonl |")
    lines += ["","## Notes","",
              "- Raw PBF tiles are retained unchanged for exact reprocessing.",
              "- Tile coverage is the rectangular bounding box returned for Ermita; boundary geometry is saved separately.",
              "- Vector tiles are zoom-dependent generalized map data, not a complete raw OpenStreetMap database.",
              "- If a layer has zero features, its file is still present and the zero count is recorded.",
              "- Review import-report.json for errors and tile-index.json for each tile status.",""]
    (ROOT/"README.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if errors:
        print(f"WARNING: {len(errors)} download/decode errors",file=sys.stderr)

if __name__ == "__main__":
    main()
