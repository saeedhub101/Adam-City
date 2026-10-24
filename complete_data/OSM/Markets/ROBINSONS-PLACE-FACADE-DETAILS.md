# Robinsons Place Manila — facade-detail overlay

This enhancement is a separate, optional overlay for the Robinsons Manila mall area in Ermita/Malate.

## Target and sources

- Target boundary: OSM way `48894714`, named **Robinsons Manila** / formerly Robinsons Place Manila.
- Boundary source: `ermita/maps/generated/ermita-features.geojson`.
- Building footprint/tag source: `complete_data/OSM/data/buildings/Ermita/ermita-building-details.geojson`.
- Viewer: root `test.html`, checkbox **Robinsons Place Manila — facade details**.
- Runtime implementation: `complete_data/OSM/Markets/robinsons-place-facade-details.js`.

## What it adds

The viewer finds building polygons inside the existing OSM mall boundary and adds thin, separate facade-detail geometry: blue-grey glazing, narrow window frames, floor bands, vertical piers, and subtle roof-edge trim. It uses available source heights and/or floor-count tags to lay out the detail. The overlay is generated in the browser and does not need a workflow build step.

## Preservation rules

- Does **not** replace or modify OpenFreeMap building geometry, coordinates, footprints, heights, source IDs, or materials.
- Does not create replacement building masses or move existing meshes.
- Does not use diagnostic green coloring.
- The overlay has its own checkbox and can be hidden independently.
- If the source mall boundary or building features cannot be loaded, it reports an error and leaves the original buildings untouched.

## Limitations

This is procedural facade detailing, not a photogrammetric model or a verified photo-texture reconstruction. It improves visible facade depth/rhythm while keeping the authoritative building geometry intact. Final visual alignment should be checked in the published `test.html`.
