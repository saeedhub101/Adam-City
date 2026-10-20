# OSM — OpenStreetMap data collection

This folder is the organized OSM data inventory for Adam-City. Source snapshots are preserved, and derived datasets are stored in separate purpose-specific folders. No cross-category merge is performed.

## Structure

- `data/raw/` — raw OSM export and synchronization state.
- `data/features/` — committed OSM feature collection used as the source snapshot for local exports.
- `data/tags/` — full tag inventory for discovering available attributes.
- `data/buildings/` — building footprints, building details, and the separate `ermita-building-roof-details` layer (CSV + GeoJSON).
- `data/roads/` — road network and the separate `ermita-road-engineering-details` layer (CSV + GeoJSON).
- `data/pedestrian/` — the separate `ermita-pedestrian-street-details` layer (CSV + GeoJSON).
- `data/thematic/` — thematic exports for accessibility, businesses, environment, heritage, public services, transport, utilities, signs, street furniture, and related themes.
- `quality/` — evidence and export reports, including `osm-detail-layer-export-report.json` for the three detail layers.
- `queries/` — OSM/Overpass query definitions.
- `scripts/` — import, audit, and detail-layer export scripts.
- `manifest.json` — inventory of files, paths, sizes, blob SHAs, and descriptions.

## Newly organized detail layers

1. **Pedestrian street details:** crossings and crossing signals, footways, sidewalk/accessibility attributes, entrances, doors, barriers, bollards, gates, handrails, steps, benches, waste baskets, street lighting, and other mapped pedestrian-scale features.
2. **Road engineering:** road and transport geometries with mapped highway/railway/route/public-transport attributes, including surface, smoothness, width, lanes, one-way direction, turn lanes, speed limits, cycleways, sidewalks, bridges, tunnels, access, lighting, and related tags.
3. **Building and roof details:** building footprints and building parts with mapped heights, floor counts, minimum levels, roof shape/height/material/colour/orientation, building material/colour, names, addresses, and other original tags.

The exact availability of each attribute varies by feature. An absent tag means it is not recorded on that OSM feature; it is not inferred or fabricated.

## Provenance and limits

- These three new detail layers were **exported from the existing committed snapshot** `ermita/maps/generated/ermita-features.geojson`. This workflow did not perform a fresh Overpass/network import.
- Geometry and original feature properties/tags are preserved in each GeoJSON output. CSV files are searchable indexes and include the full tag set in `tags_json`.
- Counts and per-key tag presence are recorded in `quality/osm-detail-layer-export-report.json`.
- Original source files under `ermita/maps/generated/` are not deleted or overwritten.
- Source: OpenStreetMap contributors. Preserve attribution and comply with ODbL 1.0.

## Reproducibility

Run `python3 ermita/scripts/export_osm_detail_layers.py` to rebuild the three independent layers from the current committed feature snapshot.
