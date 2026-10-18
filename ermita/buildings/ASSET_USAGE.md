# Ramon Magsaysay Center and street materials

All paths below are repository-relative and should be reused instead of downloading duplicates.

## Building model
- `Ramon Magsaysay Building.fbx` — source FBX model.
- `ramon_magsaysay_building.glb` — web-ready GLB currently loaded by `ermita/maps/preview.html`.
- `ramon-magsaysay-building.zip` — original model package.
- Approximate map anchor: longitude 120.98245, latitude 14.5719 (Malate).
- The map normalizes the GLB to an approximate 62 m height. The footprint, rotation, base elevation, and façade alignment still need visual verification against aerial imagery and the OSM footprint.

## Materials
- `CityStreetRoadAsphaltTwoLaneWorn001_COL_1K.jpeg` — asphalt texture used on generated street ribbons following mapped road centerlines.
- `Mono-Terrazzo-Stack-Architextures.jpeg` — provisional sidewalk surface texture, applied to narrow strips on both sides of mapped streets. Replace only if a more appropriate local sidewalk texture is found.
- `Painted-CMU-Block-Architextures.jpeg` — masonry/wall material candidate; not applied to the model automatically.
- `courtyard.png` — retained source image; usage not yet verified.

## Notes
- Textured street ribbons and sidewalk strips are approximate visual overlays, not surveyed road/sidewalk polygons.
- Model and textures are stored in this repository and should not be re-imported by future workflows.
