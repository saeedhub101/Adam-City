# OSM — OpenStreetMap data collection

This folder is a dedicated inventory/collection area for the OpenStreetMap (OSM) data already present in Adam-City. It is being populated from files on `main` without modifying or deleting their original locations.

## Structure

- `data/raw/` — raw OSM export and sync-state metadata.
- `data/features/` — generated OSM feature collection.
- `data/tags/` — tag inventory used to discover which attributes exist.
- `data/buildings/` — building footprints, building/building-part details, and attribute tables.
- `data/roads/` — mapped road/path centerlines and attributes.
- `data/thematic/` — thematic exports (accessibility, businesses, environment, heritage, public services, transport, utilities, signs, street furniture, etc.). These are collected for inspection; their exact provenance and overlap with raw OSM still need to be checked before treating every row as exclusively OSM-derived.
- `quality/` — building-height evidence report/table and road-network export report.
- `queries/` — Overpass query used to collect OSM roads, buildings, and tagged features.
- `scripts/` — existing OSM import/export and height-audit scripts.
- `manifest.json` — original path, copied path, byte size, blob SHA and purpose for each collected file.

## Important notes

1. The original files under `ermita/` remain untouched. These are copies in the repository tree, using the same underlying Git blobs where possible.
2. The collected `data/buildings/` folder stores the retained OSM details table as `osm-building-details.csv`; original source files under `ermita/maps/generated/` remain untouched.
3. This is the initial collection, not yet a full field-by-field audit. Next, inspect every dataset's schema and value coverage, identify duplicate records, and distinguish explicitly tagged heights from floor counts and unknown values.
4. The source attribution in the OSM-derived files refers to OpenStreetMap contributors; preserve OSM attribution and applicable ODbL terms when using or redistributing the data.

## Original sources

The `manifest.json` records the original source path for every collected file.
