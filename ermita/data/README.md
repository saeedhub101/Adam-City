# Data inventory

This folder contains shared data guidance and cross-category indexes. Category-specific tables live in their own folders.

## Categories
- Maps: maps/
- Buildings: buildings/buildings.csv
- Stores and businesses: stores/stores.csv
- Street geometry: streets/street_segments.csv
- Street-name index: streets/street_names.csv
- Street signs: signs/street_signs.csv
- Existing starter place records: initial-place-records.csv
- Prioritized workflow: collection-roadmap.md

## Current collection status
The street-name index and building table contain initial **candidate** records backed by cited institutional sources. Their geometry, coordinates and full coverage have not yet been imported. The stores and street-sign tables are schemas awaiting sourced records. Empty templates are not completed datasets.

## Required data hygiene
Keep stable record IDs. Preserve source spellings, and put normalized/alternate names in separate fields. Never invent coordinates, addresses, opening hours or licence information. Use explicit statuses to distinguish candidates from verified records. Record source date and licence for each imported dataset.

For OpenStreetMap-derived data, credit OpenStreetMap contributors and comply with the ODbL: https://www.openstreetmap.org/copyright.
