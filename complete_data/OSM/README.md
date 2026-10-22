# OSM — OpenStreetMap data collection

This folder is the organized OSM data inventory for Adam-City. Source snapshots are preserved, and derived datasets are stored in separate purpose-specific folders. No cross-category merge is performed.

## Structure

- `data/raw/` — raw OSM export and synchronization state.
- `data/features/` — committed OSM feature collection used as the source snapshot for local exports.
- `data/tags/` — full tag inventory for discovering available attributes.
- `data/buildings/` — retained building-detail sources, four-part GLB assets and enrichment indexes. The preview-only footprint/roof extrusion toggle and its duplicated GeoJSON/CSV outputs were removed; the original footprint source remains under `ermita/maps/generated/`.
- `data/roads/` — road network and the separate `ermita-road-engineering-details` layer (CSV + GeoJSON).
- `data/pedestrian/` — the separate `ermita-pedestrian-street-details` layer (CSV + GeoJSON).
- `data/thematic/` — thematic exports for accessibility, businesses, environment, heritage, public services, transport, utilities, signs, street furniture, and related themes.
- `quality/` — evidence and export reports, including `osm-detail-layer-export-report.json` for the three detail layers.
- `queries/` — OSM/Overpass query definitions.
- `scripts/` — import, audit, and detail-layer export scripts.
- `manifest.json` — inventory of files, paths, sizes, blob SHAs, and descriptions.
- `data/buildings/parts/BUILDING-DATA-AUDIT-AND-ENHANCEMENT-LOG.md` — سجل توثيق مصادر المباني وفهارسها وسكريبت تحسين أجزاء GLB الأربعة.
- `data/buildings/parts/building-data-full-audit.json` — تقرير تدقيق آلي يقرأ فهرس الإثراء كاملًا، ويحصي الملفات والجرد والأصول الأصلية والمشتقة.
- `scripts/audit_building_data.py` و`.github/workflows/audit-building-data.yml` — سكريبت التدقيق للقراءة فقط وسير العمل الذي يشغّله ويحدّث التقرير.

## Newly organized detail layers

1. **Pedestrian street details:** crossings and crossing signals, footways, sidewalk/accessibility attributes, entrances, doors, barriers, bollards, gates, handrails, steps, benches, waste baskets, street lighting, and other mapped pedestrian-scale features.
2. **Road engineering:** road and transport geometries with mapped highway/railway/route/public-transport attributes, including surface, smoothness, width, lanes, one-way direction, turn lanes, speed limits, cycleways, sidewalks, bridges, tunnels, access, lighting, and related tags.
3. **Building and roof details (source snapshot):** the original OSM feature snapshot retains building and roof tags. The removed preview-only layer is no longer deployed as a separate toggle; source records remain available in `ermita/maps/generated/ermita-features.geojson`.

The exact availability of each attribute varies by feature. An absent tag means it is not recorded on that OSM feature; it is not inferred or fabricated.

## Provenance and limits

- These three new detail layers were **exported from the existing committed snapshot** `ermita/maps/generated/ermita-features.geojson`. This workflow did not perform a fresh Overpass/network import.
- Geometry and original feature properties/tags are preserved in each GeoJSON output. CSV files are searchable indexes and include the full tag set in `tags_json`.
- Counts and per-key tag presence are recorded in `quality/osm-detail-layer-export-report.json`.
- Original source files under `ermita/maps/generated/` are not deleted or overwritten.
- Source: OpenStreetMap contributors. Preserve attribution and comply with ODbL 1.0.

## Reproducibility

Run `python3 ermita/scripts/export_osm_detail_layers.py` to rebuild the three independent layers from the current committed feature snapshot.

<!-- ADDITIONAL OSM THEMES START -->
## Additional OSM themes

The following independent layers are exported from ermita/maps/generated/ermita-features.geojson:

- data/addresses/ermita-addresses-street-names-postcodes — address tags, street names and postal-code attributes.
- data/administrative/ermita-administrative-boundaries — administrative boundaries and levels.
- data/places/ermita-shops-food-health-education-religion-services — mapped shops, food, health, education, religious institutions and services.
- data/nature/ermita-water-and-natural-features — mapped waterways, water bodies, coastlines and other natural features.
- data/nature/ermita-trees-parks-vegetation — trees, tree rows, parks, gardens and vegetation.
- quality/osm-additional-theme-export-report.json — counts, geometry types, tag-key coverage and selected tag values.

Each layer has CSV and GeoJSON files. GeoJSON retains source geometries and original tags; CSV provides searchable rows with tags_json. Categories can overlap when a source feature carries multiple themes. Missing values are not inferred. This run re-exports the committed snapshot; it does not fetch live OSM data. Refresh the OSM snapshot separately if newer or absent source features are required.
<!-- ADDITIONAL OSM THEMES END -->
