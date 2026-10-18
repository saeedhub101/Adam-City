#!/usr/bin/env python3
"""Fetch open OpenStreetMap features for Ermita, Manila and build a basic 3D GLB.

Source data: OpenStreetMap contributors, ODbL 1.0.
This does not download or derive data from Google Street View/Google Maps.
"""
from __future__ import annotations
import csv, json, re, sys, time
from pathlib import Path
import osm2geojson, requests, trimesh
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[2]
MAP_DIR = ROOT / "ermita" / "maps" / "generated"
MODEL_DIR = ROOT / "ermita" / "3d" / "generated"
MAP_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# The project query uses OSM relation 103706 for Ermita. Relation area ID adds 3,600,000,000.
QUERY = r"""
[out:json][timeout:180];
area(3600103706)->.ermitaArea;
(
  nwr(area.ermitaArea)["highway"];
  nwr(area.ermitaArea)["building"];
  nwr(area.ermitaArea)["building:part"];
  nwr(area.ermitaArea)["healthcare"];
  nwr(area.ermitaArea)["education"];
  nwr(area.ermitaArea)["public_transport"];
  nwr(area.ermitaArea)["bus"];
  nwr(area.ermitaArea)["bicycle"];
  nwr(area.ermitaArea)["sidewalk"];
  nwr(area.ermitaArea)["kerb"];
  nwr(area.ermitaArea)["tactile_paving"];
  nwr(area.ermitaArea)["street_lamp"];
  nwr(area.ermitaArea)["traffic_sign"];
  nwr(area.ermitaArea)["parking"];
  nwr(area.ermitaArea)["bench"];
  nwr(area.ermitaArea)["waste_basket"];
  nwr(area.ermitaArea)["drinking_water"];
  nwr(area.ermitaArea)["fountain"];
  nwr(area.ermitaArea)["species"];
  nwr(area.ermitaArea)["leaf_type"];
  nwr(area.ermitaArea)["leaf_cycle"];
  nwr(area.ermitaArea)["height"];
  nwr(area.ermitaArea)["building:levels"];
  nwr(area.ermitaArea)["roof:shape"];
  nwr(area.ermitaArea)["roof:material"];
  nwr(area.ermitaArea)["roof:colour"];
  nwr(area.ermitaArea)["amenity"];
  nwr(area.ermitaArea)["shop"];
  nwr(area.ermitaArea)["tourism"];
  nwr(area.ermitaArea)["historic"];
  nwr(area.ermitaArea)["leisure"];
  nwr(area.ermitaArea)["natural"];
  nwr(area.ermitaArea)["barrier"];
  nwr(area.ermitaArea)["man_made"];
  nwr(area.ermitaArea)["landuse"];
  nwr(area.ermitaArea)["public_transport"];
  nwr(area.ermitaArea)["railway"];
  nwr(area.ermitaArea)["emergency"];
  nwr(area.ermitaArea)["office"];
  nwr(area.ermitaArea)["craft"];
  nwr(area.ermitaArea)["power"];
  nwr(area.ermitaArea)["waterway"];
  nwr(area.ermitaArea)["water"];
  nwr(area.ermitaArea)["sport"];

  nwr(area.ermitaArea)["boundary"];
  nwr(area.ermitaArea)["entrance"];
  nwr(area.ermitaArea)["door"];
  nwr(area.ermitaArea)["crossing"];
  nwr(area.ermitaArea)["traffic_calming"];
  nwr(area.ermitaArea)["internet_access"];
  nwr(area.ermitaArea)["wheelchair"];
  nwr(area.ermitaArea)["toilets"];
  nwr(area.ermitaArea)["addr:housenumber"];
  nwr(area.ermitaArea)["addr:street"];
  nwr(area.ermitaArea)["memorial"];
  nwr(area.ermitaArea)["historic"];
);
out center geom tags;
"""
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "Adam-City-Ermita-Research/1.0 (open data research; GitHub Actions)"}

def fetch_osm():
    last_error = None
    for endpoint in ENDPOINTS:
        for attempt in range(3):
            try:
                response = requests.post(endpoint, data={"data": QUERY}, headers=HEADERS, timeout=(30, 240))
                response.raise_for_status()
                data = response.json()
                if "elements" not in data:
                    raise ValueError("Overpass response has no elements array")
                return data, endpoint
            except Exception as exc:
                last_error = exc
                time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Could not fetch OSM data: {last_error}")

def tags_for(feature):
    props = feature.get("properties") or {}
    tags = props.get("tags")
    return tags if isinstance(tags, dict) else props

def fid(feature):
    props = feature.get("properties") or {}
    return f"{props.get('type', props.get('osm_type', 'feature'))}/{props.get('id', props.get('osm_id', 'unknown'))}"

def height_for(tags):
    raw = tags.get("height")
    if raw:
        match = re.search(r"\d+(?:\.\d+)?", str(raw).replace(",", "."))
        if match and 1.5 <= float(match.group()) <= 500:
            return float(match.group()), "OSM height tag"
    levels = tags.get("building:levels") or tags.get("levels")
    if levels:
        match = re.search(r"\d+(?:\.\d+)?", str(levels))
        if match and 1.5 <= float(match.group()) * 3.2 <= 500:
            return float(match.group()) * 3.2, "building levels x 3.2 m (estimated)"
    return 9.6, "default 3-storey estimate; unverified"

def main():
    osm_json, endpoint = fetch_osm()
    (MAP_DIR / "ermita-osm-raw.json").write_text(json.dumps(osm_json, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    geojson = osm2geojson.json2geojson(osm_json)
    geojson["name"] = "Ermita, Manila - OpenStreetMap features"
    geojson["license"] = "OpenStreetMap contributors, ODbL 1.0"
    geojson["source"] = "https://www.openstreetmap.org/copyright"
    (MAP_DIR / "ermita-features.geojson").write_text(json.dumps(geojson, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    all_features = geojson.get("features", [])
    buildings, rows = [], []
    keys = ("amenity", "shop", "tourism", "historic", "healthcare", "leisure", "natural", "highway", "man_made", "barrier")
    for feature in all_features:
        tags = tags_for(feature)
        if not feature.get("geometry"):
            continue
        feature.setdefault("properties", {})["osm_feature_id"] = fid(feature)
        if "building" in tags or "building:part" in tags:
            buildings.append(feature)
        found = next((k for k in keys if k in tags), None)
        if found:
            rows.append({
                "osm_feature_id": fid(feature), "name": tags.get("name", ""),
                "feature_type": found, "feature_value": tags.get(found, ""),
                "cuisine": tags.get("cuisine", ""), "opening_hours": tags.get("opening_hours", ""),
                "phone": tags.get("phone", ""), "website": tags.get("website", ""),
                "addr_street": tags.get("addr:street", ""), "addr_housenumber": tags.get("addr:housenumber", ""),
                "source": "OpenStreetMap contributors", "license": "ODbL 1.0",
            })

    building_collection = {
        "type": "FeatureCollection", "name": "Ermita building footprints from OpenStreetMap",
        "license": "OpenStreetMap contributors, ODbL 1.0",
        "source": "https://www.openstreetmap.org/copyright", "features": buildings,
    }
    (MAP_DIR / "ermita-building-footprints.geojson").write_text(json.dumps(building_collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    poi_path = MAP_DIR / "ermita-places-businesses-infrastructure.csv"
    fields = ["osm_feature_id","name","feature_type","feature_value","cuisine","opening_hours","phone","website","addr_street","addr_housenumber","source","license"]
    with poi_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Preserve every returned feature and its complete tag set in a searchable table.
    all_path = MAP_DIR / "ermita-all-feature-tags.csv"
    all_fields = ["osm_feature_id", "name", "geometry_type", "latitude", "longitude", "tags_json", "source", "license"]
    with all_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        for feature in all_features:
            props = feature.get("properties") or {}
            tags = tags_for(feature)
            geom = feature.get("geometry") or {}
            coords = geom.get("coordinates")
            # Point coordinates are exact; other geometry centroids are computed in lon/lat.
            lat, lon = "", ""
            try:
                g = shape(geom)
                p = g if g.geom_type == "Point" else g.representative_point()
                lon, lat = p.x, p.y
            except Exception:
                pass
            writer.writerow({
                "osm_feature_id": fid(feature),
                "name": tags.get("name", props.get("name", "")),
                "geometry_type": geom.get("type", ""),
                "latitude": lat, "longitude": lon,
                "tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
                "source": "OpenStreetMap contributors", "license": "ODbL 1.0",
            })

    # Emit dedicated themed indexes to make the imported data easy to use later.
    themes = {
        "transport": {"highway", "public_transport", "railway", "route", "crossing", "traffic_calming", "bus", "parking", "bicycle", "traffic_sign"},
        "accessibility": {"wheelchair", "entrance", "door", "toilets", "tactile_paving", "ramp", "sidewalk", "kerb", "bicycle"},
        "utilities": {"power", "man_made", "waterway", "water", "barrier", "street_lamp", "drinking_water", "fountain"},
        "environment": {"natural", "landuse", "leisure", "species", "leaf_type", "leaf_cycle", "water", "waterway"},
        "public_services": {"amenity", "emergency", "healthcare", "office", "education"},
        "heritage": {"historic", "memorial", "tourism"},
        "street_furniture": {"bench", "waste_basket", "street_lamp", "traffic_sign", "barrier"},
        "building_details": {"building", "building:part", "height", "building:levels", "roof:shape", "roof:material", "roof:colour", "addr:street", "addr:housenumber"},
        "businesses": {"shop", "craft", "office", "amenity"},
    }
    for theme, tag_keys in themes.items():
        path = MAP_DIR / f"ermita-{theme}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields)
            writer.writeheader()
            for feature in all_features:
                tags = tags_for(feature)
                if not tag_keys.intersection(tags.keys()):
                    continue
                geom = feature.get("geometry") or {}
                try:
                    g = shape(geom)
                    p = g if g.geom_type == "Point" else g.representative_point()
                    lon, lat = p.x, p.y
                except Exception:
                    lon, lat = "", ""
                props = feature.get("properties") or {}
                writer.writerow({
                    "osm_feature_id": fid(feature),
                    "name": tags.get("name", props.get("name", "")),
                    "geometry_type": geom.get("type", ""),
                    "latitude": lat, "longitude": lon,
                    "tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
                    "source": "OpenStreetMap contributors", "license": "ODbL 1.0",
                })

    # Publish a dedicated street-sign / signal layer, rather than leaving these only in generic OSM exports.
    sign_features = []
    sign_keys = {"traffic_sign", "traffic_sign:forward", "traffic_sign:backward", "traffic_signals", "destination", "destination:ref"}
    for feature in all_features:
        tags = tags_for(feature)
        if not sign_keys.intersection(tags.keys()):
            continue
        sign_features.append({
            "type": "Feature",
            "id": fid(feature),
            "geometry": feature.get("geometry"),
            "properties": {
                "osm_feature_id": fid(feature),
                "name": tags.get("name", ""),
                "traffic_sign": tags.get("traffic_sign", ""),
                "traffic_sign_forward": tags.get("traffic_sign:forward", ""),
                "traffic_sign_backward": tags.get("traffic_sign:backward", ""),
                "traffic_signals": tags.get("traffic_signals", ""),
                "destination": tags.get("destination", ""),
                "destination_ref": tags.get("destination:ref", ""),
                "all_osm_tags": tags,
                "source": "OpenStreetMap contributors",
                "license": "ODbL 1.0",
            },
        })
    (MAP_DIR / "ermita-street-signs-and-signals.geojson").write_text(
        json.dumps({
            "type": "FeatureCollection",
            "name": "Ermita street signs and traffic signals from OpenStreetMap",
            "source": "https://www.openstreetmap.org/copyright",
            "license": "OpenStreetMap contributors, ODbL 1.0",
            "features": sign_features,
        }, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    # Extrude mapped building polygons. This is a basic visualization, not surveyed architecture.
    to_meters = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    meshes, built = [], 0
    for feature in buildings:
        try:
            geom = geom_transform(to_meters, shape(feature["geometry"]))
            polygons = [geom] if geom.geom_type == "Polygon" else list(geom.geoms) if geom.geom_type == "MultiPolygon" else []
            height, _ = height_for(tags_for(feature))
            for poly in polygons:
                if poly.is_empty or poly.area < 4 or not poly.is_valid:
                    continue
                meshes.append(trimesh.creation.extrude_polygon(poly, height, engine="earcut"))
                built += 1
        except Exception as exc:
            print(f"Skipping footprint {fid(feature)}: {exc}", file=sys.stderr)
    if not meshes:
        raise RuntimeError("No building polygons could be extruded; no 3D file was generated.")
    combined = trimesh.util.concatenate(meshes)
    center = combined.bounds.mean(axis=0)
    combined.apply_translation((-center[0], -center[1], -center[2]))
    combined.export(MODEL_DIR / "ermita-buildings-extruded.glb")
    with (MODEL_DIR / "building-height-methods.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["height_method", "value"])
        writer.writerow(["OSM height tag", "Use numeric height=* where plausible"])
        writer.writerow(["OSM levels tag", "building:levels or levels multiplied by 3.2 m"])
        writer.writerow(["Fallback", "9.6 m (3-storey estimate; unverified)"])
        writer.writerow(["coordinates", "EPSG:3857 meters, recentered for GLB"])
        writer.writerow(["limitation", "Extruded building volumes only; no textures or photogrammetry"])
    report = {
        "area_relation_id": 103706, "retrieval_endpoint": endpoint,
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "osm_element_count": len(osm_json.get("elements", [])), "geojson_feature_count": len(all_features),
        "building_feature_count": len(buildings), "poi_and_infrastructure_rows": len(rows),\n        "street_sign_and_signal_feature_count": len(sign_features),
        "tag_key_feature_counts": {key: sum(1 for feature in all_features if key in tags_for(feature)) for key in sorted({key for feature in all_features for key in tags_for(feature).keys()})},
        "themed_csvs": sorted(f"ermita-{theme}.csv" for theme in themes),\n        "dedicated_sign_layer": "ermita-street-signs-and-signals.geojson",
        "extruded_building_polygon_count": built, "source": "OpenStreetMap contributors",
        "license": "ODbL 1.0; attribution and share-alike obligations apply",
        "limitations": [
            "Only objects mapped in OSM are present; missing objects are not evidence of absence.",
            "This pipeline does not import or derive data from Google Street View or Google Maps.",
            "Street signs and traffic signal data may be incomplete.",
            "Building heights may be estimates where OSM has no height or level tags.",
            "The GLB is an extrusion model, not photogrammetry or a surveyed city model."
        ]
    }
    (MAP_DIR / "import-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (MODEL_DIR / "README.md").write_text(
        "# Generated Ermita 3D building model\n\n"
        "ermita-buildings-extruded.glb is generated from OpenStreetMap building polygons. "
        "It contains simple extruded volumes, not textured or photorealistic buildings. "
        "Heights use OSM tags where available and documented estimates otherwise. "
        "See building-height-methods.csv and the map import report. Source: OpenStreetMap contributors, "
        "ODbL 1.0; attribution and share-alike obligations apply.\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
