# OSM Markets — commercial signage assets

This folder stores the Robinsons Manila, 7-Eleven, and McDonald's assets used by the Adam-City test preview.

- `robenson.glb` — combined 3D model with procedural Robinsons facade geometry and textured 7-Eleven/McDonald's sign panels.
- `commercial-facades-origin.json` — origin used to position the GLB in the map.
- `commercial-facades-report.json` — generation report, storefront matches and source attribution.
- `ermita-branded-stores.geojson` — storefront features used by the generator.
- `assets/` — image textures and logo source.
- `reference_photos/robinsons-manila/` — reference photos and attribution index.
- `commercial-generation.sha256` — generation hash.

## Preview rendering method

The signage model is loaded in the same JavaScript module and with the same Three.js instance as the working windows GLB. It uses a MapLibre custom layer with `renderingMode: '3d'`, a GLTFLoader with MeshoptDecoder, the map's `defaultProjectionData.mainMatrix`, and a model transform built from `MercatorCoordinate.fromLngLat`. GLB X/Y are EPSG:3857 projected metres, so the horizontal scale uses `meterInMercatorCoordinateUnits() * cos(latitude)`; vertical Z uses `meterInMercatorCoordinateUnits()`. The layer is kept above the OSM extrusion/window layer. The original windows materials are preserved; no green debug recoloring, anchor cube, or bounds helper remains.

The Robinsons facade is a procedural visual approximation, not a surveyed or photogrammetric model. The GLB is an independent visual detail layer and does not replace building footprints.

Regeneration script: `ermita/scripts/generate_commercial_facades.py`.
