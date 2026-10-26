# Photographic matching audit — Jordan / Palestine Unity world

Audit date: 2026-10-26  
Repository: `saeedhub101/Adam-City`  
Starting location: Tabarbour, Amman (`35.940358, 31.997579`)

## Findings from the repository tree and local metadata

- The repository contains **20,777 GLB files** under `middle east/`, mostly in `middle east/BuildGLB/`; these are tiled generated exports, not evidence by themselves of photogrammetry.
- `middle east/BuildGLB/amman/` has **1,479 GLB tiles** and a manifest with tile bounds and OSM feature counts.
- The nearby 5×5 tile set around Tabarbour contains **25 existing GLB tiles** (building and street geometry). These must remain enabled and be loaded from the repository, not from an online service.
- `middle east/landmark-photos.json` contains **80 geotagged photo records**. The closest listed photo to Tabarbour is about **5.2 km** away; there are **no listed photos within 2 km** of the game start point.
- The Amman photos in that catalog are clustered around Jabal Amman / downtown. Their GPS points identify the camera location, not the photographed facade; the metadata does not provide a reliable camera heading for assigning a facade texture.
- The LiDAR import report under `complete_data/LiDAR/LIDAR_IMPORT_REPORT.md` records **0 files and 0 bytes downloaded**. The repository has LiDAR catalog metadata, but the audited file tree contains no raw LAS/LAZ/E57/PLY/PCD point-cloud payloads for this area. Satellite laser footprints are not dense building scans.
- `middle east/BuildGLB/amman/realistic/texture_two_buildings.py` explicitly creates a **procedural limestone pattern**, not a real photo texture. It must not be treated as photographic realism or applied to unrelated buildings.

## Changes made for this task

1. Restored the local GLB tile loader in the Unity scene. The loader reads files from `StreamingAssets/AmmanGLB`; no external runtime tile source is used.
2. Added `tools/audit_local_photo_building_matches.py`. It reads only repository-local `landmark-photos.json` and `Jordan/layers/building_details.geojson.gz`, and produces a candidate list for manual inspection. It does **not** change any GLB or invent textures.
3. The candidate report intentionally does not declare a photo-to-building match just because a camera coordinate is nearby.

## Why I did not auto-apply the photos

A camera point can be on a road and the camera can face any direction. Projecting that photo onto the nearest building would risk texturing the wrong building and stretching a perspective image across a facade. A reliable match needs visual identification plus a heading/perspective estimate or an explicit building-to-photo mapping. The current local metadata does not establish those details for Tabarbour.

## Required next pass

- Run `python middle east/UnityGame/tools/audit_local_photo_building_matches.py` in the repository checkout to create `BuildData/photo-building-match-candidates.json`.
- Inspect candidate photos and the corresponding buildings before approving any mapping.
- Apply a real photo only to the identified building, with a documented facade orientation and UV mapping. Keep source mesh coordinates and geometry unchanged.
- Do not use procedural stone, invented windows, random facade colors, or photos of unrelated buildings as a substitute for missing imagery.
- Do not claim photogrammetric realism for OSM-derived tiles. The existing GLBs remain useful as geometry until verified photo textures or genuine scans are available.
