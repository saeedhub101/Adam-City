# Unified GLB export

`adam-city-complete.glb` is the unified 3D export of the committed Ermita preview geometry: OSM building footprints, OSM road/path centerlines converted into road surfaces, and the committed Copernicus DEM terrain surface. The export uses one shared projected coordinate frame and a single scene origin so the layers remain aligned.

## Build

Run `python ermita/scripts/export_preview_to_glb.py` after installing `numpy rasterio trimesh shapely pyproj mapbox-earcut`.

The workflow validates the GLB, checks its size against GitHub's ordinary single-file limit, and commits the resulting `.glb` plus a JSON report to `main` when it is within the limit.

## What is represented

- OSM building footprints extruded to source heights where available, mapped floor levels where available, or a clearly documented 9.6 m fallback estimate.
- OSM road/path centerlines buffered into approximate road/path surfaces by road class.
- Copernicus DEM GLO-30 terrain mesh.

## Limits

This is a geometry export, not a screenshot or a photogrammetric city model. The live preview's streamed Esri aerial tiles are not embedded because they are not committed local imagery assets and redistribution is restricted. Procedural facade placeholder GLBs are not fused into this export because their independent recentering loses the transform needed for reliable geographic alignment. OSM source attribution and ODbL obligations apply; see the source reports for terrain attribution and limitations.
