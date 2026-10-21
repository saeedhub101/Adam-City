# Commercial markets and storefront signage

This folder contains the derived 3D commercial facade model and source inputs for Robinsons Manila, 7-Eleven, and McDonald's.

- `commercial-facades.glb`: 3D GLB with the procedural Robinsons Manila facade and textured brand-sign panels.
- `commercial-facades-origin.json`: local EPSG:3857 origin used to position the GLB in MapLibre/Three.js.
- `commercial-facades-report.json`: generation report, matching decisions, and source/photo attributions.
- `ermita-branded-stores.geojson`: OSM store points/polygons used by the generator.
- `assets/`: brand image assets used as textures.
- `reference_photos/robinsons-manila/`: licensed reference images and their index.

The preview uses the same MapLibre custom-layer + Three.js matrix transformation pattern as the working windows GLB. The Robinsons facade is procedural and approximate; it is not a surveyed or photogrammetric model. The original building footprints remain canonical and are not replaced by this GLB.

To regenerate, run `python ermita/scripts/generate_commercial_facades.py`. Its inputs/outputs now use this folder for market-specific files.
