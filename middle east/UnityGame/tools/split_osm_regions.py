#!/usr/bin/env python3
"""Stream OSM GeoJSON layers into 0.1-degree cells, correcting reversed coordinate axes.

Some exports have [latitude, longitude] coordinates even though the GLB exporter expects
[longitude, latitude]. Detect the axis order from a sample of building features, normalize
all coordinates to lon/lat, and fail loudly if no features fall inside the target extent.
"""
import argparse, gzip, json, math
from pathlib import Path
import ijson

WEST, EAST, SOUTH, NORTH = 34.15, 35.95, 29.40, 33.35
STEP = 0.10

def points(coords):
    if not isinstance(coords, list) or not coords:
        return
    if isinstance(coords[0], (int, float)) and len(coords) >= 2:
        yield coords[0], coords[1]
    else:
        for child in coords:
            yield from points(child)

def feature_center(feature, swap=False):
    coords=(feature.get("geometry") or {}).get("coordinates")
    if coords is None:
        return None
    sx=sy=n=0
    for x,y in points(coords):
        if swap: x,y=y,x
        sx+=x; sy+=y; n+=1
    return (sx/n,sy/n) if n else None

def inside(lon,lat):
    return WEST <= lon <= EAST and SOUTH <= lat <= NORTH

def detect_axis(source):
    direct=swapped=0
    sampled=0
    with gzip.open(source,"rb") as fh:
        for feature in ijson.items(fh,"features.item", use_float=True):
            c=feature_center(feature)
            if c:
                direct += int(inside(*c))
                swapped += int(inside(c[1],c[0]))
                sampled += 1
            if sampled >= 50000:
                break
    print("AXIS_PROBE",json.dumps({"sampled":sampled,"lon_lat_matches":direct,"lat_lon_matches":swapped}),flush=True)
    if direct == 0 and swapped == 0:
        raise SystemExit("No building coordinates match target bounds in either axis order; refusing to report an empty successful import.")
    return swapped > direct

def swap_coords(coords):
    if not isinstance(coords,list) or not coords:
        return coords
    if isinstance(coords[0],(int,float)) and len(coords)>=2:
        return [coords[1],coords[0],*coords[2:]]
    return [swap_coords(x) for x in coords]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--layers",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    src=Path(args.layers); out=Path(args.out)
    building_source=src/"buildings.geojson.gz"
    if not building_source.exists():
        raise SystemExit("Required layer missing: "+str(building_source))
    swap=detect_axis(building_source)
    out.mkdir(parents=True,exist_ok=True)
    counts={}
    for layer in ("buildings","streets","streetnames"):
        source=src/(layer+".geojson.gz")
        if not source.exists():
            if layer=="streetnames":
                counts[layer]={"cells":0,"features":0}
                continue
            raise SystemExit("Required layer missing: "+str(source))
        handles={}; per_cell={}
        with gzip.open(source,"rb") as fh:
            for feature in ijson.items(fh,"features.item"):
                center=feature_center(feature,swap=swap)
                if not center: continue
                lon,lat=center
                if not inside(lon,lat): continue
                if swap:
                    geom=feature.get("geometry") or {}
                    if "coordinates" in geom:
                        geom["coordinates"]=swap_coords(geom["coordinates"])
                ix=math.floor((lon-WEST)/STEP); iy=math.floor((lat-SOUTH)/STEP)
                cell=f"{ix:02d}_{iy:02d}"
                if cell not in handles:
                    folder=out/cell; folder.mkdir(parents=True,exist_ok=True)
                    target=folder/(layer+".geojson.gz")
                    h=gzip.open(target,"wt",encoding="utf-8",compresslevel=5)
                    h.write('{"type":"FeatureCollection","features":[')
                    handles[cell]=h; per_cell[cell]=0
                h=handles[cell]
                if per_cell[cell]: h.write(",")
                h.write(json.dumps(feature,separators=(",",":"),ensure_ascii=False))
                per_cell[cell]+=1
        for h in handles.values(): h.write("]}")
        for h in handles.values(): h.close()
        counts[layer]={"cells":len(per_cell),"features":sum(per_cell.values())}
        print("SPLIT",layer,json.dumps(counts[layer]),flush=True)
    building_count=counts["buildings"]["features"]
    if building_count == 0:
        raise SystemExit("Split produced zero buildings; refusing to continue.")
    for folder in out.iterdir():
        if folder.is_dir():
            for layer in ("buildings","streets"):
                target=folder/(layer+".geojson.gz")
                if not target.exists():
                    with gzip.open(target,"wt",encoding="utf-8") as empty:
                        empty.write('{"type":"FeatureCollection","features":[]}')
    report={
        "source":"Stored Geofabrik Israel and Palestine / OpenStreetMap extract",
        "source_url":"https://download.geofabrik.de/asia/israel-and-palestine.html",
        "license":"Open Database License 1.0 (ODbL); attribution required",
        "bounds":{"west":WEST,"east":EAST,"south":SOUTH,"north":NORTH},
        "cell_degrees":STEP,"input_coordinate_order":"lat_lon" if swap else "lon_lat",
        "counts":counts
    }
    (out/"split-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("SPLIT_REPORT",json.dumps(report),flush=True)

if __name__=="__main__":
    main()
