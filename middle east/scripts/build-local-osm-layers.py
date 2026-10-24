#!/usr/bin/env python3
"""Build repository-local thematic GeoJSON layers from saved OSM PBF extracts."""
import gzip, json, subprocess, tempfile
from pathlib import Path

ROOT = Path("middle east")
LIMIT = 99_000_000
THEMES = {
    "buildings": ["w/building", "r/building", "w/building:part", "r/building:part"],
    # Export complete tags on building features, including roof/facade/material/color/height/levels.
    "building_details": ["w/building", "r/building", "w/building:part", "r/building:part", "w/roof:shape", "w/roof:material", "w/roof:colour", "w/roof:levels", "w/building:material", "w/building:colour", "w/facade:material", "w/facade:colour", "w/window", "n/window", "w/door", "n/door", "w/entrance", "n/entrance"],
    "streets": ["w/highway", "r/route=road", "w/railway", "r/route=train", "w/aeroway", "w/man_made=bridge", "w/man_made=tunnel"],
    "streetnames": ["w/highway", "r/route=road", "w/railway", "w/aeroway"],
    "boundaries": ["w/boundary=administrative", "r/boundary=administrative", "r/type=boundary"],
    "water": ["w/waterway", "r/waterway", "w/natural=water", "r/natural=water", "w/landuse=reservoir", "w/natural=coastline", "n/natural=spring", "w/natural=spring", "n/man_made=water_well", "w/man_made=water_well", "n/amenity=drinking_water", "w/amenity=drinking_water", "w/water=river", "w/water=lake", "w/water=pond", "w/water=basin"],
    "landcover": ["w/landuse", "w/natural", "w/leisure", "w/landcover", "w/natural=wood", "w/natural=scrub", "w/natural=heath", "w/natural=wetland", "w/natural=beach", "w/natural=bare_rock", "w/natural=sand", "w/natural=cliff", "w/natural=peak", "w/natural=saddle", "w/natural=valley", "n/natural=tree", "w/natural=tree_row", "n/natural=grassland", "w/leisure=park", "w/leisure=garden", "w/leisure=playground", "w/leisure=sports_centre", "w/leisure=pitch", "w/landuse=farmland", "w/landuse=orchard", "w/landuse=vineyard", "w/landuse=cemetery", "w/landuse=quarry"],
    "places": ["n/place", "w/place", "r/place", "n/amenity", "w/amenity", "r/amenity", "n/shop", "w/shop", "r/shop", "n/tourism", "w/tourism", "r/tourism", "n/historic", "w/historic", "r/historic", "n/office", "w/office", "r/office", "n/healthcare", "w/healthcare", "n/railway=station", "w/railway=station", "n/public_transport", "w/public_transport", "r/public_transport", "n/education", "w/education", "n/religion", "w/religion", "n/heritage", "w/heritage", "n/memorial", "w/memorial", "n/man_made=monument", "w/man_made=monument", "n/man_made=lighthouse", "w/man_made=lighthouse", "n/aeroway=aerodrome", "w/aeroway=aerodrome", "n/attraction", "w/attraction", "n/information", "w/information", "n/route", "n/emergency", "w/emergency", "n/defibrillator", "w/defibrillator", "n/fire_station", "w/fire_station", "n/police", "w/police", "n/military", "w/military", "n/power", "w/power", "n/telecom", "w/telecom"],
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
    catalog = {"format":"adam-city-local-osm-layers-v5", "source":"Repository-stored OpenStreetMap PBF extracts", "license":"OpenStreetMap ODbL", "layers":[], "errors":[]}
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
                            if old_geo.get("type") == "FeatureCollection" and entry.get("layer_version") == 5:
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
                    with raw.open("r", encoding="utf-8") as f:
                        geo = json.load(f)
                    if geo.get("type") != "FeatureCollection" or not isinstance(geo.get("features"), list):
                        raise RuntimeError("export is not a valid GeoJSON FeatureCollection")
                    with gzip.open(target, "wt", encoding="utf-8", compresslevel=6) as f:
                        json.dump(geo, f, ensure_ascii=False, separators=(",", ":"))
                    if target.stat().st_size >= LIMIT:
                        target.unlink(missing_ok=True)
                        raise RuntimeError(f"compressed GeoJSON exceeds safe 99 MB limit ({target.stat().st_size} bytes); requires spatial partitioning")
                    entry = {"feature_count":len(geo["features"]),"compressed_bytes":target.stat().st_size,"uncompressed_bytes":raw_bytes,"geometry_types":sorted({x.get("geometry",{}).get("type","null") for x in geo["features"] if x.get("geometry")})}
                    record = {"layer_version":5,"country":country,"theme":theme,"source_file":str(src),"method":"osmium tags-filter + osmium export","license":"OpenStreetMap ODbL",**entry}
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
