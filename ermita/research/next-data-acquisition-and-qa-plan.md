# Next data acquisition and QA plan

## Current active inputs

- OSM buildings and tags: `ermita/maps/generated/ermita-building-footprints.geojson`.
- OSM roads and paths: `ermita/maps/generated/ermita-road-network.geojson`.
- Existing DPWH road/bridge layers and reports: `ermita/maps/external/`.
- Existing Copernicus DEM and terrain output: `ermita/3d/terrain/`.
- Existing KartaView photo archive and match metadata: `kartaview/`.

## Explicit source decision

Microsoft/Bing building footprints were found to be inaccurate for the project area and have been removed. Their importer, converter, comparison outputs, and workflows are retired. Do not reacquire this dataset or use its previous 12,132-outline count as active coverage.

## Priorities

1. Keep OSM as the only active building-footprint layer and hide third-party basemap building extrusions to avoid duplicate/conflicting outlines.
2. Improve visible facade detail in the 3D preview: window and shopfront openings, entrances, floor bands, parapets and roof edges, while clearly labeling procedural estimates.
3. Use an internet-sourced reference only after inspecting it and confirming the building identity. Record the exact URL, location/OSM ID, observed facade features, and confidence.
4. Verify street-facing wall orientation against nearby OSM roads before placing a facade treatment.
5. Keep explicit source heights distinct from inferred heights. A single source conflict must be recorded rather than silently discarded.
6. Inspect the live build after the commit; check console/network errors and ensure each layer fails independently.
7. Inspect existing repository assets before any download. Save accepted new assets and their provenance in the repository, not only as workflow artifacts.
