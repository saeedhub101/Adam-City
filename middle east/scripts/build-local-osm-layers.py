#!/usr/bin/env python3
"""Build repository-local, thematic GeoJSON layers from saved OSM PBF extracts.

Outputs compressed GeoJSON under middle east/{Jordan,Palestine}/layers/.
Every output is generated from repository PBF files, not from a live map API.
"""
import gzip, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path("middle east")
LIMIT = 90_000_000
THEMES = {
    "buildings": ["w/building", "r/building", "w/building:part"],
    "streets": ["w/highway", "r/route=road"],
    "water": ["w/waterway", "r/waterway", "w/natural=water", "w/landuse=reservoir", "w/natural=coastline"],
    "landcover": ["w/landuse", "w/natural", "w/leisure", "w/landcover"],
    "places": ["n/place", "n/amenity", "n/shop", "n/tourism", "n/historic", "n/office", "n/healthcare", "n/railway=station", "n/public_transport=station"],
    "addresses": ["n/addr:housenumber", "w/addr:housenumber", "r/addr:housenumber", "n/addr:street", "w/addr:street"],
}

def run(args):
    subprocess.run(args, check=True)

def country_source(country, temp):
    if country == "Jordan":
        p = ROOT / "Jordan/osm/jordan-latest.osm.pbf"
        return p if p.is_file() and p.stat().st_size else None
    files = sorted((ROOT / "Palestine/osm/tiles").glob("*.osm.pbf"))
    files = [p for p in files if p.is_file() and p.stat().st_size > 100]
    if not files:
        return None
    merged = temp / "palestine-area-merged.osm.pbf"
    run(["osmium", "merge", *map(str, files), "-o", str(merged), "--overwrite"])
    return merged

def main():
    catalog = {"format":"adam-city-local-osm-layers-v1", "source":"Repository-stored OpenStreetMap PBF extracts", "license":"OpenStreetMap ODbL", "layers":[]}
    with tempfile.TemporaryDirectory(prefix="me-layers-") as td:
        temp = Path(td)
        for country in ("Jordan", "Palestine"):
            src = country_source(country, temp)
            if src is None:
                print(f"WARNING: no saved PBF source for {country}; continuing")
                continue
            dest = ROOT / country / "layers"
            dest.mkdir(parents=True, exist_ok=True)
            for theme, selectors in THEMES.items():
                target = dest / f"{theme}.geojson.gz"
                manifest = dest / f"{theme}.metadata.json"
                # Reuse a valid existing result. Delete it to force a refresh.
                if target.is_file() and target.stat().st_size > 0 and manifest.is_file():
                    try:
                        with gzip.open(target, "rt", encoding="utf-8") as f:
                            json.load(f)
                        entry = json.loads(manifest.read_text(encoding="utf-8"))
                        catalog["layers"].append({"country":country, "theme":theme, "path":str(target).replace("\\","/"), **entry})
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
                    raise RuntimeError(f"{target} would exceed the 90 MB safety limit uncompressed ({raw_bytes}); split this theme spatially before committing.")
                with raw.open("r", encoding="utf-8") as f:
                    geo = json.load(f)
                if geo.get("type") != "FeatureCollection" or not isinstance(geo.get("features"), list):
                    raise RuntimeError(f"Invalid GeoJSON output: {raw}")
                with gzip.open(target, "wt", encoding="utf-8", compresslevel=6) as f:
                    json.dump(geo, f, ensure_ascii=False, separators=(",", ":"))
                entry = {"feature_count":len(geo["features"]), "compressed_bytes":target.stat().st_size, "uncompressed_bytes":raw_bytes, "geometry_types":sorted({x.get("geometry",{}).get("type","null") for x in geo["features"] if x.get("geometry")})}
                manifest.write_text(json.dumps({"country":country,"theme":theme,"source_file":str(src),"method":"osmium tags-filter + osmium export","license":"OpenStreetMap ODbL",**entry}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
                catalog["layers"].append({"country":country, "theme":theme, "path":str(target).replace("\\","/"), **entry})
                print(f"IMPORTED {country}/{theme}: {entry['feature_count']} features, {entry['compressed_bytes']} compressed bytes")
        catalog_path = ROOT / "layers-catalog.json"
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(f"CATALOG {catalog_path} ({len(catalog['layers'])} layers)")
if __name__ == "__main__":
    main()
