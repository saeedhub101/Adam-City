# Historic Palestine OSM coverage and GLB export status

Updated: 2026-10-25

## Verified source already stored in this repository

- Source: Geofabrik **Israel and Palestine** combined OpenStreetMap extract.
- License: OpenStreetMap ODbL; attribution must be retained.
- Saved source tiles: 70 PBF files covering a grid from longitude 33.0–36.5 and latitude 29.0–34.0.
- Existing integrity report: 70/70 PBF tiles validated; 37 tiles contain OSM objects; 15,993,433 OSM objects counted across non-empty tiles. The 33 empty tiles are valid empty extracts, not automatically missing coverage.
- Existing thematic layer `buildings.geojson.gz`: 2,087,961 GeoJSON features; compressed size 91,184,410 bytes.
- Existing thematic layer `building_details.geojson.gz`: 2,088,828 features (see its metadata for the exact file size).
- Existing thematic layer `streets.geojson.gz`: 625,120 features; compressed size 49,057,571 bytes.
- Existing places layer: 238,945 features; compressed size 17,273,854 bytes.
- The layer feature counts are not counts of unique physical buildings. Geometry types include points, lines and multipolygons; the GLB exporter only turns polygon building geometries into building meshes.

## Export plan now committed to main

- The regional GLB workflow now processes the historic Palestine / Israel coverage first, then the separate Jordan regions.
- The stored Palestine layers are streamed into 0.1-degree temporary spatial cells to avoid loading the full multi-million-feature layer into memory for each Blender export.
- Each cell is subdivided into 0.01-degree GLB tiles; all historic Palestine tiles use a shared local coordinate origin so adjacent tiles align.
- Completed cell output folders are checkpointed to `main`. Failed cells are logged and later cells continue. Existing GLBs are skipped on reruns, and the manifest preserves/reconstructs the tile inventory after interrupted runs.
- Workflow: https://github.com/saeedhub101/Adam-City/actions/workflows/build-amman-glb.yml
- Source: https://download.geofabrik.de/asia/israel-and-palestine.html

## Accuracy and current verification limit

OSM supplies mapped footprints, road geometry, tags and some height/material information; it does not provide comprehensive photographed facades or photogrammetric building meshes. The procedural GLBs are mapped-data visualizations, not proof of photorealistic real buildings.

At the time this report was written, the current Actions build had not yet been verified to have committed new GLB files under `middle east/BuildGLB/`. Do not treat the coverage as complete until the run finishes and the repository tree is checked for generated files and manifests.
