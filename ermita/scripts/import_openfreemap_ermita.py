#!/usr/bin/env python3
"""Incrementally import OpenFreeMap/OpenMapTiles vector tiles for Ermita."""
import concurrent.futures, json, math, os, pathlib, sys, time
import requests
import mapbox_vector_tile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "ermita/maps/sources/openfreemap"
RAW = ROOT / "vector-tiles"
LAYERS_DIR = ROOT / "layers"
STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"
GEOCODER = "https://nominatim.openstreetmap.org/search"
UA = "Adam-City OpenFreeMap incremental importer/2.0 (GitHub repository saeedhub101/Adam-City)"
MIN_ZOOM = int(os.environ.get("MIN_ZOOM", "10"))
MAX_ZOOM = int(os.environ.get("MAX_ZOOM", "16"))
MAX_TILES = 3000
MAX_BYTES = 50 * 1024 * 1024
RETRY_EMPTY = os.environ.get("RETRY_EMPTY_TILES", "0") == "1"
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
    bbox = [float(v) for v in chosen["boundingbox"]]
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
        maxzoom = source.get("maxzoom")
        if source.get("tiles"):
            return source["tiles"][0], int(maxzoom) if maxzoom is not None else 14
        if source.get("url"):
            tilejson = get_json(source["url"])
            if tilejson.get("tiles"):
                mz = tilejson.get("maxzoom", maxzoom)
                # OpenMapTiles/planet tiles are normally published through z14.
                return tilejson["tiles"][0], int(mz) if mz is not None else 14
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

def tile_key(item):
    return "/".join(str(v) for v in item)

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    LAYERS_DIR.mkdir(parents=True, exist_ok=True)
    area, bbox, polygon = find_area()
    south, north, west, east = bbox
    tile_template, source_maxzoom = tile_url_from_style()
    effective_maxzoom = min(MAX_ZOOM, source_maxzoom)
    tile_set = set()
    # Include a one-tile safety margin around the geocoded boundary. The map viewport
    # extends beyond the administrative boundary, especially with a pitched 3D camera.
    tile_buffer = max(0, int(os.environ.get("TILE_BUFFER", "1")))
    for z in range(MIN_ZOOM, MAX_ZOOM + 1):
        x0,y1 = xyz(west,south,z)
        x1,y0 = xyz(east,north,z)
        n = 2 ** z
        for x in range(max(0,min(x0,x1)-tile_buffer), min(n-1,max(x0,x1)+tile_buffer)+1):
            for y in range(max(0,min(y0,y1)-tile_buffer), min(n-1,max(y0,y1)+tile_buffer)+1):
                tile_set.add((z,x,y))
    tiles = sorted(tile_set)
    if len(tiles) > MAX_TILES:
        raise RuntimeError(f"Tile coverage needs {len(tiles)} tiles; safety limit is {MAX_TILES}.")
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
        "bbox_south_north_west_east":bbox,"requested_zoom_range":[MIN_ZOOM,MAX_ZOOM],
        "source_maxzoom":source_maxzoom,"effective_maxzoom":effective_maxzoom,
        "tile_count_planned":len(tiles),"tile_limit":MAX_TILES,"download_limit_bytes_per_run":MAX_BYTES,
        "layers":LAYER_NAMES,"retrieved_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    index_path = ROOT / "tile-index.json"
    old_index = {}
    if index_path.exists():
        try:
            old_index = {tile_key((int(t["z"]),int(t["x"]),int(t["y"]))):t
                         for t in json.loads(index_path.read_text(encoding="utf-8"))}
        except Exception:
            old_index = {}
    layer_paths = {name: LAYERS_DIR / (name + ".geojsonl") for name in LAYER_NAMES}
    # Preserve existing layer files. Only records from newly downloaded valid tiles are appended.
    layer_handles = {name: layer_paths[name].open("a",encoding="utf-8") for name in LAYER_NAMES}
    tile_index = []
    total_new_bytes = 0
    errors = []
    skipped_existing = 0
    downloaded_new = 0
    empty_or_failed = 0

    def download(item):
        z,x,y = item
        url = tile_template.replace("{z}",str(z)).replace("{x}",str(x)).replace("{y}",str(y))
        try:
            r = session.get(url,timeout=90)
            if r.status_code == 404:
                return item, None, 0, "empty_404"
            r.raise_for_status()
            if not r.content:
                return item, None, 0, "empty_response"
            # Verify PBF decodes before treating it as a completed download.
            mapbox_vector_tile.decode(r.content)
            return item, r.content, len(r.content), None
        except Exception as exc:
            return item, None, 0, "error: " + str(exc)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            # Unsupported zooms are recorded, not repeatedly requested.
            eligible = []
            for item in tiles:
                z,x,y = item
                raw_path = RAW / str(z) / str(x) / (str(y)+".pbf")
                previous = old_index.get(tile_key(item), {})
                if z > effective_maxzoom:
                    # Remove only known zero-byte placeholders from the earlier broken run.
                    if raw_path.exists() and raw_path.stat().st_size == 0:
                        raw_path.unlink()
                    tile_index.append({"z":z,"x":x,"y":y,"status":"unsupported_zoom",
                                       "source_maxzoom":source_maxzoom,"reason":"Source does not publish this zoom level."})
                    continue
                if raw_path.exists() and raw_path.stat().st_size > 0:
                    try:
                        decoded = mapbox_vector_tile.decode(raw_path.read_bytes())
                        counts = {name:len(layer.get("features",[])) for name,layer in decoded.items() if name in LAYER_NAMES}
                        tile_index.append({"z":z,"x":x,"y":y,"status":"already_present","bytes":raw_path.stat().st_size,
                                           "path":str(raw_path),"layer_feature_counts":counts})
                        skipped_existing += 1
                        continue
                    except Exception:
                        errors.append({"z":z,"x":x,"y":y,"error":"Existing tile invalid; scheduling redownload."})
                if (not RETRY_EMPTY and previous.get("status") in ("empty_404","empty_response")):
                    tile_index.append({**previous,"status":previous["status"],"reason":"Previously checked empty; set RETRY_EMPTY_TILES=1 to retry."})
                    empty_or_failed += 1
                    continue
                eligible.append(item)

            for item, content, size, error in pool.map(download, eligible):
                z,x,y = item
                raw_path = RAW / str(z) / str(x) / (str(y)+".pbf")
                if error:
                    status = error if error in ("empty_404","empty_response") else "download_error"
                    tile_index.append({"z":z,"x":x,"y":y,"status":status,
                                       "error":None if status != "download_error" else error})
                    if status == "download_error":
                        errors.append({"z":z,"x":x,"y":y,"error":error})
                    empty_or_failed += 1
                    continue
                total_new_bytes += size
                if total_new_bytes > MAX_BYTES:
                    raise RuntimeError(f"New downloads exceeded {MAX_BYTES} bytes safety limit.")
                raw_path.parent.mkdir(parents=True,exist_ok=True)
                raw_path.write_bytes(content)
                decoded = mapbox_vector_tile.decode(content)
                counts = {}
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
                tile_index.append({"z":z,"x":x,"y":y,"status":"downloaded_new","bytes":size,
                                   "path":str(raw_path),"layer_feature_counts":counts})
                downloaded_new += 1
    finally:
        for handle in layer_handles.values():
            handle.close()

    # Keep tile index deterministic in z/x/y order.
    tile_index.sort(key=lambda t:(t["z"],t["x"],t["y"]))
    summary = {"source":"OpenFreeMap / OpenMapTiles","area":area.get("display_name"),
        "tile_template":tile_template,"requested_zoom_range":[MIN_ZOOM,MAX_ZOOM],
        "source_maxzoom":source_maxzoom,"effective_maxzoom":effective_maxzoom,
        "planned_tiles":len(tiles),"existing_tiles_reused":skipped_existing,
        "new_tiles_downloaded":downloaded_new,"empty_or_failed_tiles":empty_or_failed,
        "unsupported_zoom_tiles":sum(1 for t in tile_index if t["status"]=="unsupported_zoom"),
        "new_pbf_bytes":total_new_bytes,"layer_feature_counts":{},"layer_files":{},"errors":errors,
        "incremental_mode":True,"retry_empty_tiles_enabled":RETRY_EMPTY,
        "raw_tile_index":"tile-index.json","retrieved_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    for name,path in layer_paths.items():
        with path.open(encoding="utf-8") as handle:
            count = sum(1 for line in handle if line.strip())
        summary["layer_feature_counts"][name]=count
        summary["layer_files"][name]=str(path)
    index_path.write_text(json.dumps(tile_index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"import-report.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# OpenFreeMap / OpenMapTiles — incremental layer catalogue","",
           f"- Area: {area.get('display_name')}",
           f"- Source maximum zoom: {source_maxzoom}; effective requested maximum: {effective_maxzoom}",
           "- Import mode: incremental; valid local PBF files are reused and never downloaded again.",
           "- Existing GeoJSONL layer files are preserved; records are appended only for newly downloaded valid tiles.",
           "- Raw tiles: vector-tiles/{z}/{x}/{y}.pbf",
           "- Decoded records: one GeoJSON Feature per line; coordinates are WGS84 longitude/latitude.",
           "- Every record includes _source.tile and _source.layer to trace it to the original PBF tile.",
           "- Attribution: OpenFreeMap © OpenMapTiles Data from OpenStreetMap.","",
           "| Layer | Total features in repository | File |","|---|---:|---|"]
    for name in LAYER_NAMES:
        lines.append(f"| {name} | {summary['layer_feature_counts'][name]} | layers/{name}.geojsonl |")
    lines += ["","## Incremental import report","",
              f"- Existing valid tiles reused: {skipped_existing}",
              f"- New valid tiles downloaded: {downloaded_new}",
              f"- Unsupported zoom tiles skipped: {summary['unsupported_zoom_tiles']}",
              f"- Empty/failed tiles: {empty_or_failed}",
              "- Review import-report.json and tile-index.json for per-tile status.",
              "- To retry previously empty tiles intentionally, set RETRY_EMPTY_TILES=1.",
              "- Vector tiles are zoom-dependent generalized map data, not a complete raw OpenStreetMap database.",""]
    (ROOT/"README.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if errors:
        print(f"WARNING: {len(errors)} download/decode errors",file=sys.stderr)
        # Fail the workflow so missing tiles are visible and can be retried.
        raise RuntimeError(f"{len(errors)} tile download/decode errors; see import-report.json")

if __name__ == "__main__":
    main()
