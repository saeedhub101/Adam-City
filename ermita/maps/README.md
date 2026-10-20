# Maps and geographic layers

This folder stores source-traceable geographic data for Ermita, Manila, with a detailed focus on Rizal Park.

## Active data

- **Interactive 3D preview:** [Adam City 3D](../../ermita-malate-3d.html) starts from the OpenFreeMap style and local OpenFreeMap/OpenMapTiles-derived building/ground fallbacks in `sources/openfreemap/`. It does not simply load the generated OSM GeoJSON as its base layer.
- **Generated building footprints:** `generated/ermita-building-footprints.geojson` is Basemap/OpenMapTiles-derived according to the file-level audit, not a pure OSM snapshot. Do not use its feature count as an OSM count or apply the OSM height audit to it.
- **Road/path geometry:** `generated/ermita-road-network.geojson` contains 1,445 mapped OSM way centerlines; 366 ways have a name. `../streets/street_segments.csv` indexes the same source geometry.
- **Building-height evidence:** `qa/building-height-evidence.csv` and `qa/building-height-evidence-report.json` distinguish explicit height tags from floor counts and unknown values.
- **KartaView imagery:** locally stored street-level photos and their metadata remain available for research. They are not automatically pasted onto building walls; image proximity does not prove facade identity or orientation.
- **DPWH references:** clipped road/bridge data remains under `external/`; check its import report for layer-specific coverage, vintage and attribution.
- **Satellite imagery:** Esri imagery is streamed for viewing and is not embedded as a repository asset; its licensing/redistribution terms differ from OSM data.

## Independent building sources

- Google Open Buildings v3 is stored separately under `sources/google-open-buildings/`.
- Microsoft satellite-derived footprints are stored separately under `sources/microsoft-satellite-buildings/` (1,765 area-clipped polygons per its import report). This is a collected source dataset, not proof that the current preview uses it or that every footprint is accurate.
- Keep these sources separate from the generated Basemap/OpenMapTiles-derived file and from any preserved OSM snapshot. Do not merge or overwrite datasets without a source-specific QA report.

## Data rules

- Keep each footprint provider in its own file and layer; the current preview is OpenFreeMap-based and is not an OSM-only viewer.
- Preserve source IDs/tags and distinguish mapped heights from estimates.
- Save accepted imported assets and reports in the repository, not only workflow artifacts.
- Inspect existing files first and download only missing/new data.

## Consolidated map/building register

- [Consolidated source inventory and merge rules](qa/consolidated-map-building-register.md)
- [Merged building register (one row per OSM feature ID)](qa/consolidated-building-register.csv)

The register preserves conflicting values and indicates which source files contain each building record. Missing from a file does not mean missing in the real world.

## Non-OSM source expansion (2026-10-19)

- The new import workflows collect **SRTM terrain**, **ESA WorldCover vegetation/grass**, **Google Research Open Buildings v3**, DPWH roads/bridge attributes, Microsoft road detections, and openly licensed OpenAerialMap imagery where the item license permits it.
- Terrain and ESA WorldCover outputs are stored under `sources/terrain/` and `sources/landcover/`; the vegetation polygons are a derived display layer from the ESA 10 m classification.
- Direct OpenStreetMap refresh has been removed from the source-import workflow. Existing OSM-derived files are retained unchanged as historical project assets; they are not deleted or silently conflated with new non-OSM sources.
- **Important:** the current 3D preview still uses its existing OpenFreeMap style and cached OSM road/building data. It is not yet an OSM-free viewer. Google Open Buildings and Microsoft satellite footprints are stored separately; enabling either in the preview is a distinct integration task and should not overwrite the existing basemap layer.
- Google Open Buildings v3 supplies satellite-derived building footprints and confidence scores, not building names, facade photos, windows, signs, roof materials or measured heights. Those details need separate licensed sources or independent photo-based modeling.

