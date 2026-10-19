# Maps and geographic layers

This folder stores source-traceable geographic data for Ermita, Manila, with a detailed focus on Rizal Park.

## Active data

- **Interactive 3D preview:** [Adam City 3D](../../index.html) uses committed OSM building footprints and road/path centerlines, plus DPWH road records and streamed Esri satellite imagery when enabled.
- **OSM building footprints:** `generated/ermita-building-footprints.geojson`; source tags and OSM feature IDs are retained. Current import report records 1,533 building/building-part features across the full export; the live polygon layer filters geometry types to polygons and multipolygons.
- **Road/path geometry:** `generated/ermita-road-network.geojson` contains 1,445 mapped OSM way centerlines; 366 ways have a name. `../streets/street_segments.csv` indexes the same source geometry.
- **Building-height evidence:** `qa/building-height-evidence.csv` and `qa/building-height-evidence-report.json` distinguish explicit height tags from floor counts and unknown values.
- **KartaView imagery:** locally stored street-level photos and their metadata remain available for research. They are not automatically pasted onto building walls; image proximity does not prove facade identity or orientation.
- **DPWH references:** clipped road/bridge data remains under `external/`; check its import report for layer-specific coverage, vintage and attribution.
- **Satellite imagery:** Esri imagery is streamed for viewing and is not embedded as a repository asset; its licensing/redistribution terms differ from OSM data.

## Explicitly removed

Microsoft/Bing building footprints were rejected because their outlines were inaccurate for this project. The clipped footprint files, comparison outputs, importer, converter, and comparison workflow have been removed or retired. Do not restore or re-import that source unless the project owner explicitly reverses this decision.

## Data rules

- Keep OSM building polygons as the only active footprint source.
- Preserve source IDs/tags and distinguish mapped heights from estimates.
- Save accepted imported assets and reports in the repository, not only workflow artifacts.
- Inspect existing files first and download only missing/new data.
