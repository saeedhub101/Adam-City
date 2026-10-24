#!/usr/bin/env python3
"""Build repository-local thematic GeoJSON layers from saved OSM PBF extracts."""
import gzip, json, subprocess, tempfile
from pathlib import Path

ROOT = Path("middle east")
LIMIT = 90_000_000
THEMES = {
    "buildings": ["w/building", "r/building", "w/building:part"],
    "streets": ["w/highway", "r/route=road"],
    "streetnames": ["w/highway", "r/route=road"],
    "boundaries": ["w/boundary=administrative", "r/boundary=administrative", "r/type=boundary"],
    "water": ["w/waterway", "r/waterway", "w/natural=water", "w/landuse=reservoir", "w/natural=coastline", "n/natural=spring", "w/natural=spring", "n/man_made=water_well", "w/man_made=water_well", "n/amenity=drinking_water", "w/amenity=drinking_water"],
    "landcover": ["w/landuse", "w/natural", "w/leisure", "w/landcover", "w/natural=wood", "w/natural=scrub", "w/natural=heath", "n/natural=tree", "n/natural=grassland"],
    "places": ["n/place", "w/place", "r/place", "n/amenity", "w/amenity", "r/amenity", "n/shop", "w/shop", "r/shop", "n/tourism", "w/tourism", "r/tourism", "n/historic", "w/historic", "r/historic", "n/office", "w/office", "n/healthcare", "w/healthcare", "n/railway=station", "n/public_transport=station", "n/education", "w/education"],
    "addresses": ["n/addr:housenumber", "w/addr:housenumber", "r/addr:housenumber", "n/addr:street", "w/addr:street"],
}
def run(args):
    subprocess.run(args, check=True)

def country_source(country, temp):
    if country == "Jordan":
        p = ROOT / "Jordan/osm/jordan-latest.osm.pbf"
        return p if p.is_file() and p.stat().st_size else None
    files = sorted(p for p in (ROOT / "Palestine/osm/tiles").glob("*.osm.pbf") if p.stat().st_size > 100)
    if not files:
        return None
    merged = temp / "palestine-area-merged.osm.pbf"
    run(["osmium", "merge", *map(str, files), "-o", str(merged), "--overwrite"])
    return merged

def main():
    catalog = {"format":"adam-city-local-osm-layers-v1", "source":"Repository-stored OpenStreetMap PBF extracts", "license":"OpenStreetMap ODbL", "layers":[], "errors":[]}
    with tempfile.TemporaryDirectory(prefix="me-layers-") as td:
        temp = Path(td)
        for country in ("Jordan", "Palestine"):
            try:
                src = country_source(country, temp)
            except Exception as exc:
                print(f"ERROR preparing {country}: {exc}")
                catalog["errors"].append({"country":country,"stage":"prepare-source","error":str(exc)})
                continue
            if src is None:
                catalog["errors"].append({"country":country,"stage":"prepare-source","error":"No saved non-empty PBF source"})
                print(f"WARNING: no saved PBF source for {country}; continuing")
                continue
            dest = ROOT / country / "layers"
            dest.mkdir(parents=True, exist_ok=True)
            for theme, selectors in THEMES.items():
                target = dest / f"{theme}.geojson.gz"
                manifest = dest / f"{theme}.metadata.json"
                try:
                    # Verify and resume completed outputs.
                    if target.is_file() and target.stat().st_size and manifest.is_file():
                        try:
                            with gzip.open(target, "rt", encoding="utf-8") as f:
                                old_geo = json.load(f)
                            entry = json.loads(manifest.read_text(encoding="utf-8"))
                            if old_geo.get("type") == "FeatureCollection" and entry.get("layer_version") == 2:
                                catalog["layers"].append({"country":country,"theme":theme,"path":target.as_posix(),**entry})
                                print(f"SKIP verified {target}")
                                continue
                        except Exception:
                            target.unlink(missing_ok=True)
                    filtered = temp / f"{country}-{theme}.osm.pbf"
                    raw = temp / f"{country}-{theme}.geojson"
                    run(["osmium", "tags-filter", str(src), *selectors, "-o", str(filtered), "--overwrite"])
                    run(["osmium", "export", str(filtered), "-o", str(raw), "--overwrite"])
                    raw_bytes = raw.stat().st_size
                    if raw_bytes >= LIMIT:
                        raise RuntimeError(f"uncompressed GeoJSON exceeds safe 90 MB limit ({raw_bytes} bytes); requires spatial partitioning")
                    with raw.open("r", encoding="utf-8") as f:
                        geo = json.load(f)
                    if geo.get("type") != "FeatureCollection" or not isinstance(geo.get("features"), list):
                        raise RuntimeError("export is not a valid GeoJSON FeatureCollection")
                    with gzip.open(target, "wt", encoding="utf-8", compresslevel=6) as f:
                        json.dump(geo, f, ensure_ascii=False, separators=(",", ":"))
                    if target.stat().st_size >= LIMIT:\n                        target.unlink(missing_ok=True)\n                        raise RuntimeError(f"compressed GeoJSON exceeds safe 90 MB limit ({target.stat().st_size} bytes); requires spatial partitioning")\n                    entry = {"feature_count":len(geo["features"]),"compressed_bytes":target.stat().st_size,"uncompressed_bytes":raw_bytes,"geometry_types":sorted({x.get("geometry",{}).get("type","null") for x in geo["features"] if x.get("geometry")})}
                    record = {"layer_version":2,"country":country,"theme":theme,"source_file":str(src),"method":"osmium tags-filter + osmium export","license":"OpenStreetMap ODbL",**entry}
                    manifest.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
                    catalog["layers"].append({"country":country,"theme":theme,"path":target.as_posix(),**entry})
                    print(f"IMPORTED {country}/{theme}: {entry['feature_count']} features, {entry['compressed_bytes']} compressed bytes")
                except Exception as exc:
                    target.unlink(missing_ok=True)
                    catalog["errors"].append({"country":country,"theme":theme,"error":str(exc)})
                    print(f"ERROR {country}/{theme}; continuing: {exc}")
        catalog_path = ROOT / "layers-catalog.json"
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(f"CATALOG {catalog_path}: {len(catalog['layers'])} layers, {len(catalog['errors'])} errors")
if __name__ == "__main__":
    main()
