# Verified real-3D asset intake — Jordan and Palestine

Updated: 2026-10-25  
Target page: `middle-east.html`  
Branch: `main`

## Non-negotiable display rules

- Keep OpenFreeMap/OSM footprints as the location reference unless a surveyed model has a verified geographic transform.
- Never align a GLB by visual guess, centroid alone, or an arbitrary offset. Record its CRS, units, vertical axis, scale, rotation, anchor coordinate, and transform evidence.
- Do not generate fake roofs, windows, doors, or facade textures and describe them as real.
- Keep footprint/height-based buildings clearly separate from verified textured meshes. Missing real geometry must not be filled with invented 3D detail.
- Do not publish source assets until their reuse license is checked and recorded. Preserve attribution and source identifiers.

## Verified candidates

| Site / dataset | Area | Captured data | License / reuse status | Integration status |
|---|---|---|---|---|
| [Madaba — Burnt Palace](https://openheritage3d.org/project.php?id=7bzx-v340) | Madaba, Jordan | Terrestrial photogrammetry (49.02 GB) and aerial photogrammetry (3.36 GB) | CC BY-NC-SA; non-commercial only, attribution and share-alike apply | Candidate only. Download links are delivered by Open Heritage 3D after request. Do not position on map until the model and georeferencing are inspected. |
| [Madaba — Church of the Virgin Mary & Hippolytus Hall](https://openheritage3d.org/project.php?id=mv5j-ef62) | Madaba, Jordan | Terrestrial photogrammetry (75.98 GB) and aerial photogrammetry (13.25 GB) | CC BY-NC-SA; non-commercial only, attribution and share-alike apply | Candidate only. Large dataset; request only when storage/processing is available. Spatial georeferencing is not guaranteed. |
| [ACOR–Global Digital Heritage collection](https://acorjordan.org/acor-gdh/) | Multiple sites in Jordan | Published photogrammetry/3D documentation; collection includes Amman Citadel Museum, Petra Museum and Petra Archaeological Park among listed items | Check the individual asset's terms before reuse; no blanket license assumed | Research catalogue. Select individual downloadable models, verify file format/license/coordinates, then add per-asset manifest entries. |

## Coverage gap

No verified, downloadable, geographically registered photorealistic 3D building dataset for all of Amman, Jordan, or Palestine has been established by this inventory. The repository's current country-wide OSM GeoJSON files are map features and tags, not complete textured meshes. They remain useful for footprints and attributes, but are not evidence of real facade geometry.

The GlobalBuildingAtlas can be investigated separately for consistent footprints/heights/LoD1 geometry, but LoD1 block models are not photorealistic facades and must not be labelled as such.

## Required per-model manifest

Before adding any model to the map, create a record containing:

- Stable asset ID and human-readable site/building name
- Original dataset/project URL and exact source file
- License, attribution text, and any non-commercial/share-alike restrictions
- Evidence that the model depicts the named real building
- Geographic anchor and CRS; coordinate source and accuracy
- Model units, up axis, scale, rotation, and vertical datum if known
- Verified bounding box after transformation
- Processing history and checksum
- Status: `discovered`, `requested`, `downloaded`, `inspected`, `georeferenced`, `integrated`, or `rejected`

## Integration gate

1. Obtain the source dataset and license terms.
2. Inspect the mesh, textures, coordinate metadata, and bounding box without altering the source.
3. Establish a documented geographic transform from survey/control points or trustworthy georeferencing.
4. Test the model as an optional overlay at its verified location, with a toggle and clear attribution.
5. Compare against the basemap and neighboring footprints; reject the overlay if alignment or scale cannot be proven.
6. Only then publish optimized web assets. Keep raw source data and optimized deliverables clearly distinguished.

## Sources checked

- Open Heritage 3D dataset index: https://openheritage3d.org/data
- Burnt Palace dataset details and license: https://openheritage3d.org/project.php?id=7bzx-v340
- Church of the Virgin Mary & Hippolytus Hall dataset details and license: https://openheritage3d.org/project.php?id=mv5j-ef62
- ACOR–Global Digital Heritage collection: https://acorjordan.org/acor-gdh/
- GlobalBuildingAtlas overview: https://huggingface.co/datasets/zhu-xlab/GBA.ODbLPolygon

This document is an asset intake register, not a claim that the listed models have already been downloaded, georeferenced, or rendered.
