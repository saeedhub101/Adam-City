# Build syntax validation trigger
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
# Import every tagged or geometric OSM object in the Ermita boundary, not only
# a fixed list of known tag keys. This captures newly mapped categories too.
QUERY = r"""
[out:json][timeout:180];
area(3600103706)->.ermitaArea;
nwr(area.ermitaArea);
out center geom tags;
"""
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "Adam-City-Ermita-Research/1.0 (open data research; GitHub Actions)"}


SYNC_STATE_PATH = MAP_DIR / "ermita-osm-sync-state.json"

def incremental_query(since_utc):
    """Fetch every object in the area edited since the checkpoint in one compact query.

    A single area+newer selector is more reliable than appending a newer filter to
    dozens of tag selectors, and also catches newly-added tag categories.
    """
    stamp = since_utc
    return f'''[out:json][timeout:180];
area(3600103706)->.ermitaArea;
nwr(area.ermitaArea)[newer:"{stamp}"];
out center geom tags;
'''


def merge_osm_elements(existing, changed):
    """Merge changed OSM objects by stable type/id; never erase cached data on partial responses."""
    merged = {(item.get("type"), item.get("id")): item for item in existing}
    applied = 0
    for item in changed:
        key = (item.get("type"), item.get("id"))
        if key[0] is None or key[1] is None:
            continue
        # Overpass can omit deleted/invisible objects from a normal selector response.
        # If a returned object has no usable tags or geometry, preserve the previous cached version.
        if not item.get("tags") and not item.get("geometry") and not item.get("center"):
            continue
        merged[key] = item
        applied += 1
    return list(merged.values()), applied

def read_cached_osm():
    raw_path = MAP_DIR / "ermita-osm-raw.json"
    if not raw_path.exists():
        return None
    try:
        data = json.loads(raw_path.read_text(encoding="utf-8"))
        return data if isinstance(data.get("elements"), list) else None
    except (OSError, json.JSONDecodeError):
        return None

def previous_sync_time():
    if SYNC_STATE_PATH.exists():
        try:
            state = json.loads(SYNC_STATE_PATH.read_text(encoding="utf-8"))
            if state.get("last_sync_utc"):
                return state["last_sync_utc"]
        except (OSError, json.JSONDecodeError):
            pass
    report_path = MAP_DIR / "import-report.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            return report.get("retrieved_utc")
        except (OSError, json.JSONDecodeError):
            pass
    return None

def fetch_osm(query=QUERY):
    last_error = None
    for endpoint in ENDPOINTS:
        for attempt in range(3):
            try:
                response = requests.post(endpoint, data={"data": query}, headers=HEADERS, timeout=(30, 240))
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

def preserve_curated_building_edits(source_features, existing_path):
    """Keep Adam City edits when rebuilding building exports from a fresh OSM snapshot.

    Edit contract stored in feature.properties.adam_city:
      tag_overrides: tags that must survive source refreshes
      lock_geometry: true to keep the curated footprint instead of source geometry
      user_created: true for a manually added building with no OSM counterpart

    The raw OSM cache remains source data; curated changes live only in the canonical
    building-detail export and are merged by stable OSM feature ID.
    """
    try:
        previous = json.loads(existing_path.read_text(encoding="utf-8"))
        previous_features = previous.get("features", []) if isinstance(previous, dict) else []
    except (OSError, json.JSONDecodeError):
        previous_features = []

    def props_of(feature):
        props = feature.get("properties")
        return props if isinstance(props, dict) else {}

    previous_by_id = {}
    for feature in previous_features:
        p = props_of(feature)
        key = str(p.get("osm_feature_id", "")).strip()
        if key:
            previous_by_id[key] = feature

    seen = set()
    for feature in source_features:
        props = props_of(feature)
        key = str(props.get("osm_feature_id", "")).strip()
        if not key:
            continue
        seen.add(key)
        old = previous_by_id.get(key)
        if not old:
            continue
        old_edit = props_of(old).get("adam_city")
        if not isinstance(old_edit, dict):
            continue
        edit = json.loads(json.dumps(old_edit))
        props["adam_city"] = edit
        overrides = edit.get("tag_overrides", {})
        if isinstance(overrides, dict) and overrides:
            tags = props.get("tags")
            if not isinstance(tags, dict):
                tags = {}
            tags.update(overrides)
            props["tags"] = tags
        if edit.get("lock_geometry") is True and old.get("geometry"):
            feature["geometry"] = old["geometry"]

    # Manually created buildings are retained across source imports. They must be
    # explicitly marked to avoid preserving accidental stale source records.
    for old in previous_features:
        p = props_of(old)
        edit = p.get("adam_city")
        key = str(p.get("osm_feature_id", "")).strip()
        if isinstance(edit, dict) and edit.get("user_created") is True and (not key or key not in seen):
            source_features.append(old)
            if key:
                seen.add(key)

    return source_features


def main():
    # Reuse the committed raw cache and ask Overpass only for objects edited since
    # the last successful sync. A one-day overlap makes retries/checkpoint boundaries safe.
    cached = read_cached_osm()
    last_sync = previous_sync_time()
    sync_started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sync_mode = "incremental"
    delta_count = 0
    applied_count = 0
    if cached and last_sync:
        try:
            from datetime import datetime, timedelta, timezone
            since = datetime.fromisoformat(last_sync.replace("Z", "+00:00")) - timedelta(days=1)
            since_text = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            since_text = None
        if since_text:
            try:
                osm_delta, endpoint = fetch_osm(incremental_query(since_text))
                delta_count = len(osm_delta.get("elements", []))
                merged_elements, applied_count = merge_osm_elements(cached.get("elements", []), osm_delta.get("elements", []))
                osm_json = dict(cached)
                osm_json["elements"] = merged_elements
            except Exception as delta_error:
                # A busy Overpass server can return HTTP 500 for a delta query.
                # Recover with the full query, but merge into the cache so a partial
                # response never erases previously imported objects.
                print(f"WARNING: incremental OSM query failed ({delta_error}); trying full recovery query.")
                sync_mode = "full_recovery"
                osm_full, endpoint = fetch_osm()
                delta_count = len(osm_full.get("elements", []))
                merged_elements, applied_count = merge_osm_elements(cached.get("elements", []), osm_full.get("elements", []))
                osm_json = dict(cached)
                osm_json["elements"] = merged_elements
            osm_json["osm_incremental_sync"] = {
                "since_utc": since_text,
                "last_query_started_utc": sync_started,
                "delta_element_count": delta_count,
                "applied_element_count": applied_count,
                "sync_mode": sync_mode,
            }
        else:
            # If checkpoint metadata is invalid, do a full baseline rather than risk gaps.
            sync_mode = "full_recovery"
            osm_json, endpoint = fetch_osm()
            applied_count = len(osm_json.get("elements", []))
    else:
        # First run / missing cache: establish a complete baseline.
        sync_mode = "full_baseline"
        osm_json, endpoint = fetch_osm()
        applied_count = len(osm_json.get("elements", []))

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

    # Merge saved, explicitly namespaced Adam City edits before writing either building export.
    buildings = preserve_curated_building_edits(
        buildings, MAP_DIR / "ermita-building-details.geojson"
    )

    building_collection = {
        "type": "FeatureCollection", "name": "Ermita building footprints from OpenStreetMap",
        "license": "OpenStreetMap contributors, ODbL 1.0",
        "source": "https://www.openstreetmap.org/copyright", "features": buildings,
    }
    (MAP_DIR / "ermita-building-footprints.geojson").write_text(json.dumps(building_collection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    # Export building attributes as a first-class dataset, not only embedded in generic tags.
    building_detail_keys = [
        "building", "building:part", "name", "official_name", "alt_name",
        "building:use", "building:levels", "building:levels:underground",
        "building:min_level", "height", "min_height", "min_level",
        "roof:shape", "roof:height", "roof:levels", "roof:material",
        "roof:colour", "roof:color", "roof:angle", "roof:direction",
        "building:material", "building:colour", "building:color",
        "addr:housenumber", "addr:street", "addr:suburb", "addr:city",
        "addr:postcode", "addr:full", "start_date", "architect",
        "heritage", "historic", "wikidata", "wikipedia", "website",
        "access", "entrance", "building:condition"
    ]
    building_detail_fields = ["osm_feature_id", "name", "geometry_type", *building_detail_keys, "all_tags_json", "source", "license"]
    building_detail_path = MAP_DIR / "ermita-building-details.csv"
    with building_detail_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=building_detail_fields)
        writer.writeheader()
        for feature in buildings:
            tags = tags_for(feature)
            geom = feature.get("geometry") or {}
            row = {
                "osm_feature_id": fid(feature),
                "name": tags.get("name", ""),
                "geometry_type": geom.get("type", ""),
                "all_tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
                "source": "OpenStreetMap contributors",
                "license": "ODbL 1.0",
            }
            row.update({key: tags.get(key, "") for key in building_detail_keys})
            writer.writerow(row)
    building_detail_geojson = {
        "type": "FeatureCollection",
        "name": "Ermita building details and building parts from OpenStreetMap",
        "source": "https://www.openstreetmap.org/copyright",
        "license": "OpenStreetMap contributors, ODbL 1.0",
        "features": buildings,
    }
    (MAP_DIR / "ermita-building-details.geojson").write_text(
        json.dumps(building_detail_geojson, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
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
        "sync_mode": sync_mode,
        "sync_started_utc": sync_started,
        "sync_since_utc": since_text if sync_mode == "incremental" else None,
        "delta_element_count": delta_count,
        "added_or_updated_element_count": applied_count,
        "incremental_policy": "Cached OSM elements are merged by type/id; unchanged elements are reused and missing/deleted responses do not erase cached records.",
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "osm_element_count": len(osm_json.get("elements", [])), "geojson_feature_count": len(all_features),
        "building_feature_count": len(buildings), "poi_and_infrastructure_rows": len(rows),
        "building_detail_csv": "ermita-building-details.csv", "building_detail_geojson": "ermita-building-details.geojson",
        "building_detail_feature_count": len(buildings),
        "building_detail_tag_presence_counts": {key: sum(1 for feature in buildings if key in tags_for(feature)) for key in building_detail_keys},
        "street_sign_and_signal_feature_count": len(sign_features),
        "tag_key_feature_counts": {key: sum(1 for feature in all_features if key in tags_for(feature)) for key in sorted({key for feature in all_features for key in tags_for(feature).keys()})},
        "themed_csvs": sorted(f"ermita-{theme}.csv" for theme in themes),
        "dedicated_sign_layer": "ermita-street-signs-and-signals.geojson",
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
    # Advance the checkpoint only after every output has been generated successfully.
    (SYNC_STATE_PATH).write_text(json.dumps({
        "last_sync_utc": sync_started,
        "mode": sync_mode,
        "area_relation_id": 103706,
        "source": "OpenStreetMap contributors",
        "policy": "Incremental changes merged by OSM type/id; cached records are retained on partial responses."
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
