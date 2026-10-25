#!/usr/bin/env python3
"""Stream large compressed GeoJSON layers into manageable 0.1-degree regional chunks.

The input Palestine layers already contain the Geofabrik Israel-and-Palestine OSM extract.
This avoids loading millions of features into Blender at once. OSM geometry remains mapped
footprints/roads, not photogrammetry. Output chunks are temporary workflow inputs.
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

def feature_center(feature):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates")
    if coords is None:
        return None
    # Geometry centroid approximated by mean of coordinates; sufficient for partitioning only.
    vals = list(points(coords))
    if not vals:
        return None
    return sum(p[0] for p in vals)/len(vals), sum(p[1] for p in vals)/len(vals)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", required=True)
    args=ap.parse_args()
    src=Path(args.layers); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    counts={}
    # The source is streamed, so memory use is bounded to a feature and open output handles.
    for layer in ("buildings","streets","streetnames"):
        source=src/(layer+".geojson.gz")
        if not source.exists() and layer=="streetnames":
            continue
        if not source.exists():
            raise SystemExit("Required layer missing: "+str(source))
        handles={}; per_cell={}
        with gzip.open(source,"rb") as fh:
            for feature in ijson.items(fh,"features.item"):
                center=feature_center(feature)
                if not center: continue
                lon,lat=center
                if not (WEST <= lon <= EAST and SOUTH <= lat <= NORTH): continue
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
        print("SPLIT",layer,json.dumps(counts[layer]))
    (out/"split-report.json").write_text(json.dumps({
        "source":"Geofabrik Israel and Palestine / OpenStreetMap",
        "source_url":"https://download.geofabrik.de/asia/israel-and-palestine.html",
        "license":"Open Database License 1.0 (ODbL); attribution required",
        "bounds":{"west":WEST,"east":EAST,"south":SOUTH,"north":NORTH},
        "cell_degrees":STEP,"counts":counts
    },indent=2),encoding="utf-8")
if __name__=="__main__": main()
