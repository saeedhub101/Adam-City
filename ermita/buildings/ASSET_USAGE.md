# Ramon Magsaysay Center model and shared material assets

All paths below are repository-relative and should be reused instead of downloading duplicates.

## Building model
- `Ramon Magsaysay Building.fbx` — source FBX model.
- `ramon_magsaysay_building.glb` — web-ready GLB currently loaded by `ermita/maps/preview.html`.
- `ramon-magsaysay-building.zip` — original model package.
- Approximate map anchor: longitude 120.98245, latitude 14.5719 (Malate).
- The map normalizes the GLB to an approximate 62 m height. The footprint, rotation, base elevation, and façade alignment still need visual verification against aerial imagery and the OSM footprint.

## Shared textures (`ermita/assets/textures/`)
- `CityStreetRoadAsphaltTwoLaneWorn001_COL_1K.jpeg` — asphalt texture used on generated street ribbons following mapped road centerlines.
- `Mono-Terrazzo-Stack-Architextures.jpeg` — provisional sidewalk surface texture, applied to narrow strips on both sides of mapped streets. Replace only if a more appropriate local sidewalk texture is found.
- `Painted-CMU-Block-Architextures.jpeg` — now assigned as a provisional texture map to the local Ramon Magsaysay GLB mesh materials. This is a generic painted masonry material, not a verified photo of the actual building facade; UV alignment and visual accuracy still need checking.
- `ermita/assets/textures/courtyard.png` — now applied to a provisional 32 m × 28 m textured plaza pad at the model anchor. The exact courtyard boundary, position, and rotation are not yet verified against aerial imagery.

## Notes
- Textured street ribbons and sidewalk strips are approximate visual overlays, not surveyed road/sidewalk polygons.
- Model and textures are stored in this repository and should not be re-imported by future workflows.
