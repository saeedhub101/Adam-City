#!/usr/bin/env python3
import json, math, glob, os, shutil
from pathlib import Path

SOURCE = Path("Manila/GeoJSON_Source")
OUT = Path("Manila/New_Manila")
MAX_REGIONS = 10

def midpoint(feature):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates")
    points = []
    def walk(v):
        if isinstance(v, (list, tuple)) and len(v) >= 2 and isinstance(v[0], (int, float)) and isinstance(v[1], (int, float)):
            points.append((float(v[0]), float(v[1])))
        elif isinstance(v, (list, tuple)):
            for item in v: walk(item)
    walk(coords)
    if not points: return None
    return ((min(p[0] for p in points)+max(p[0] for p in points))/2,
            (min(p[1] for p in points)+max(p[1] for p in points))/2)

files = sorted(SOURCE.glob("**/*.geojson"))
features = []
for path in files:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue
    for f in doc.get("features", []):
        props = f.get("properties") or {}
        layer = props.get("_source_layer", props.get("source_layer", props.get("layer")))
        if layer == "building" or (isinstance(layer, list) and "building" in layer):
            p = midpoint(f)
            if p is not None:
                features.append((f, p))

if not features:
    raise SystemExit("No building features with valid geometry found; refusing to write empty output.")

# Local metric coordinates: approximately metres, correcting longitude for Manila latitude.
lat0 = sum(p[1] for _, p in features) / len(features)
coslat = math.cos(math.radians(lat0))
xy = [((p[0] * 111320.0 * coslat), (p[1] * 110540.0)) for _, p in features]
k = min(MAX_REGIONS, len(features))

# Deterministic farthest-point initialization, then Lloyd k-means.
centers = [xy[0]]
while len(centers) < k:
    idx = max(range(len(xy)), key=lambda i: min((xy[i][0]-c[0])**2+(xy[i][1]-c[1])**2 for c in centers))
    candidate = xy[idx]
    if candidate in centers: break
    centers.append(candidate)
k = len(centers)
labels = [0] * len(xy)
for _ in range(60):
    new_labels = []
    for x, y in xy:
        new_labels.append(min(range(k), key=lambda j: (x-centers[j][0])**2+(y-centers[j][1])**2))
    sums = [[0.0, 0.0, 0] for _ in range(k)]
    for (x, y), lab in zip(xy, new_labels):
        sums[lab][0] += x; sums[lab][1] += y; sums[lab][2] += 1
    new_centers = [((s[0]/s[2], s[1]/s[2]) if s[2] else centers[j]) for j,s in enumerate(sums)]
    stable = new_labels == labels and new_centers == centers
    labels, centers = new_labels, new_centers
    if stable: break

groups = [[] for _ in range(k)]
for (feature, point), lab in zip(features, labels):
    groups[lab].append((feature, point))
groups = [g for g in groups if g]
groups.sort(key=lambda g: (sum(p[1] for _,p in g)/len(g), sum(p[0] for _,p in g)/len(g)))

if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True)
summary = {
  "status": "completed",
  "source_directory": str(SOURCE),
  "output_directory": str(OUT),
  "source_geojson_files_read": len(files),
  "building_features_grouped": len(features),
  "maximum_regions": MAX_REGIONS,
  "regions_created": len(groups),
  "coordinate_method": "spatial k-means using building geometry bounding-box midpoint in approximate local metres",
  "source_geojson_modified": False,
  "note": "At most 10 compact geographic regions; original feature geometries and properties are preserved."
}
for i, group in enumerate(groups, 1):
    pts = [p for _,p in group]
    lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
    name = f"region_{i:02d}.geojson"
    doc = {
      "type":"FeatureCollection",
      "name":f"Manila_Buildings_Region_{i:02d}",
      "metadata":{
        "region":i, "region_count":len(groups), "building_feature_count":len(group),
        "coordinate_system":"WGS84 (EPSG:4326)",
        "grouping":"spatial k-means, distance approximated in metres",
        "bounds":{"west":min(lons),"south":min(lats),"east":max(lons),"north":max(lats)}
      },
      "features":[f for f,_ in group]
    }
    (OUT/name).write_text(json.dumps(doc, separators=(",",":"), ensure_ascii=False)+"\n", encoding="utf-8")
    summary.setdefault("regions", []).append({
      "file":name,"building_features":len(group),
      "bounds":{"west":min(lons),"south":min(lats),"east":max(lons),"north":max(lats)}
    })
(OUT/"grouping-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print(json.dumps({"source_files":len(files),"buildings":len(features),"regions":len(groups),"region_sizes":[len(g) for g in groups]}, indent=2))
