# Jordan-wide GLB execution ledger

Last updated: 2026-10-26 UTC  
Repository: saeedhub101/Adam-City — branch main

## Mandatory import policy

All future imports must follow [IMPORT_WORKFLOW_POLICY.md](IMPORT_WORKFLOW_POLICY.md): inspect existing data first, import only missing assets, checkpoint and commit during execution, resume after failure, isolate stage errors, avoid millions of small files, and report validated payloads rather than catalog metadata. The currently running Jordan-wide GLB workflow is left untouched until it completes or fails.

## Required output contract

- At most 50 regional GLB files for the generated Jordan country model.
- Use the saved Jordan OSM PBF and all locally stored Jordan OSM layers; preserve source OSM IDs and original tags.
- Combine many buildings and infrastructure features per GLB, rather than one file per building or tiny 0.01-degree tile.
- Keep all files local to the repository/game build; no live map or external asset URLs at runtime.
- Do not fabricate measured heights, facade textures, colors, or imagery. Any procedural geometry must be marked as procedural in metadata.

## Completed changes

- [x] Retired the legacy automatic regional workflow that generated thousands of small GLBs.
- [x] Retired the legacy Amman index workflow from automatic execution.
- [x] Fixed a syntax error in the existing Blender exporter.
- [x] Added support for saved OSM water, landcover, places, addresses, and building-detail tags.
- [x] Added OSM infrastructure parsing for railways, waterways, power lines, trees, traffic signals, transit objects, bridges/tunnels, barriers, and other mapped infrastructure from the saved PBF.
- [x] Added source OSM IDs/tags as GLB custom properties, OSM-derived road surface materials, OSM-tagged building/roof material colors where present, and explicit flags for procedural default heights/windows.
- [x] Added a new country-wide workflow that generates large geographic GLBs, validates every GLB header, and hard-fails if the result exceeds 50 files.
- [x] Changed the LiDAR workflow to an audit-only gate. It no longer downloads GEDI/ICESat-2 satellite samples as a substitute for building LiDAR.
- [ ] Verify the new country GLBs, counts, and manifest on main after the current build completes.
- [ ] Add and integrate a Jordan DEM/terrain source. The repository inventory previously found no Jordan-specific DEM or local satellite imagery assets.
- [ ] Search for licensed local orthophotos/satellite imagery and real 3D building models, then integrate only if the data can be stored and used offline.
- [ ] After validation, remove only the obsolete generated grid-tile GLBs; preserve curated individual building models and overlays.

## Active workflows

- New Jordan-wide build: [current run](https://github.com/saeedhub101/Adam-City/actions/workflows/build-jordan-50-glb.yml) — builds from existing OSM layers plus a temporary infrastructure extract of the saved Jordan PBF. No output is claimed until the run passes validation and commits.
- LiDAR suitability audit: [latest run](https://github.com/saeedhub101/Adam-City/actions/runs/40277696651) — completed; found 0 LAS/LAZ/COPC files in the current download folder and imported 0 new payloads.
- Legacy tiny-tile workflow: retired and set to skip, to avoid regenerating the old file explosion.

## Current source inventory and limitations

Locally available Jordan layers:
- buildings and building details
- street/road geometry and street names
- address points
- administrative boundaries
- landcover
- place labels
- water features
- saved Jordan OSM PBF, used to extract additional infrastructure

Not yet present as local Jordan assets:
- dense airborne/terrestrial LiDAR point clouds
- Jordan DEM/terrain raster
- local orthophotos/satellite imagery for facade/roof texturing
- broad coverage of verified photogrammetric or surveyed 3D building models

OSM does not generally provide exact facade photographs, per-window layouts, roof texture images, or measured building heights for every building. Those fields will remain unknown unless a suitable source is found. Procedural windows/material defaults are visual placeholders, not survey evidence.

## Validation gate

A build is complete only when:
1. The workflow reports 1–50 GLBs and all headers validate.
2. The manifest lists every generated GLB, its feature counts, and the shared georeference origin.
3. GLBs contain source OSM identifiers and retained tags.
4. The manifest and GLBs are committed to main.
5. No legacy regeneration workflow recreates the tiny-tile set.
