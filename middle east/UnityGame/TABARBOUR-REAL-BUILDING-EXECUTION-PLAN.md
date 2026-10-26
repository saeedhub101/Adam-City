# Tabarbour first: verified real-building GLB production plan

Status: **active execution plan**  
Repository: `saeedhub101/Adam-City`  
Branch: `main`  
Pilot area: Tabarbour, Amman, Jordan (approximately 35.940358 N, 31.997579 E)

## Required outcome

Produce repository-stored GLB assets whose appearance corresponds to the real target buildings in Tabarbour. Complete Tabarbour and validate the result before expanding to another area. Do not call procedural blocks, generic stone patterns, invented windows, guessed roof details, or arbitrary color changes “realistic buildings.”

## Mandatory repository-first rule

Before importing or downloading anything, inspect the repository's existing GLB files, manifests, OSM/building-detail data, image/photo catalogs and payloads, Mapillary/Geosphere/OpenFreeTile/Microsoft/Streetmap/satellite-related assets, and LiDAR inventories. Reuse suitable existing files first. Download only specific missing evidence or data after the local inventory has been checked. Keep new source data in the project's established data folders and record provenance/licensing where available.

## Mandatory image verification gate — do not bypass

**A photo must not be used to build or texture a GLB until a person has visually inspected the actual image and verified that it depicts the intended building.** Nearby GPS coordinates, a matching street name, a filename, search-result thumbnail, or metadata alone do not establish a match.

For every candidate image, inspect the image itself and record:

1. **Subject identity:** visible evidence that this is the exact target building, not merely a neighboring property or a similar building.
2. **View type:** exterior only; reject interior photographs, maps, renders, advertisements, unrelated collages, and images where the building is not the subject.
3. **Occlusion and quality:** reject images where people, vehicles, trees, signs, scaffolding, heavy shadows, blur, cropping, or low resolution hide the facade or make geometry/material details unreliable. A few incidental people are acceptable only if they do not obscure the relevant facade; do not reconstruct hidden details by guessing.
4. **Coverage and perspective:** identify which facade/roof is visible, camera direction if known, perspective distortion, and whether the image supports the intended texture/geometry task. A street-level front view cannot prove the shape of a hidden rear facade or roof.
5. **Geographic consistency:** compare visible surroundings, street layout, neighboring buildings, and camera location. Camera GPS is the camera position, not necessarily the photographed building position.
6. **Rights and provenance:** retain the source URL/provider, attribution/license if supplied, retrieval date, and any usage constraints.
7. **Decision:** `approved_exact_building`, `partial_facade_only`, or `rejected`, with a short reason and the target OSM ID / existing GLB asset.

If the image cannot be inspected directly, the building identity is uncertain, or the relevant facade is obscured, **do not use it**. Do not infer approval from automated similarity or a nearby camera coordinate. For an approved photo, map only the visible facade with a documented UV/perspective treatment; do not stretch one photo around all sides of a building.

## Geometry and coordinate integrity

- Existing GLB geometry and coordinates are the starting point and must be preserved unless verified evidence demonstrates a specific correction is required.
- Match OSM identity, footprint, location, tile and GLB node before editing.
- Use LiDAR/point clouds or photogrammetry only when actual payload data exists and coverage/accuracy are checked. A catalog entry or satellite-laser footprint is not a dense building scan.
- OSM tags and OpenFreeTile/OpenFreeMap-style data can help with footprint, height and roof hypotheses, but do not prove facade appearance.
- Satellite/aerial imagery is useful for roofs and footprint context, not for inventing unseen street-level facade details.
- Microsoft, Mapillary, Geosphere, Streetmap or any other source may be used if access and terms permit, but each image still passes the same visual identity gate.
- Preserve the original GLB. Export changed assets to a separate, clearly named output path and keep a source-to-output manifest.

## Build and quality gates

A building output is accepted only when all of the following are true:

- The exact target building is identified and its source GLB/OSM record is linked.
- The evidence image has passed the mandatory manual visual check, or the output is explicitly limited to geometry supported by verified non-photo survey data.
- No unsupported details were invented or presented as factual.
- GLB parses successfully; expected meshes/materials/textures are present and non-empty.
- Coordinates, orientation, dimensions and alignment are compared against the source and remain unchanged unless a documented correction is approved.
- A visual inspection confirms the exported GLB actually resembles the intended real building and does not show texture stretching, wrong-building imagery, interior content, prominent people, or other obvious image mismatch.
- Evidence, decisions, source provenance, output path and validation results are saved in the repository.

Do not report success merely because Blender or a workflow exits with status 0. Validate the output file and inspect the actual result.

## Execution order

1. Inventory existing Tabarbour-area repository assets before external imports.
2. Identify the first target buildings from existing GLBs and OSM/building records.
3. Find candidate evidence using local assets first; then use available permitted sources (LiDAR, Mapillary, Geosphere, OpenFreeTile, OSM, Microsoft, Streetmap, satellite/aerial imagery, or another suitable source).
4. Visually inspect and approve/reject each actual image using the mandatory gate above.
5. Build a small set of GLBs only from verified evidence; keep originals untouched.
6. Validate visually and technically, update the evidence manifest, and correct failures.
7. Expand to the rest of Tabarbour only after the pilot passes; expand to other neighborhoods only after Tabarbour is accepted.

## Current known blockers found during execution

- The existing script `middle east/BuildGLB/amman/realistic/texture_two_buildings.py` points at `amman_3590_3200.glb`. The Tabarbour start coordinate `35.940358, 31.997579` falls in tile `amman_3594_3199.glb` under the repository's 0.01-degree tiling scheme. The old script therefore targets a different tile and must not be used to select Tabarbour buildings.
- A Wikimedia photo tagged as Tabarbour was opened and visually inspected, then rejected: it is a broad roadside scene, the target building cannot be identified, and it lacks facade detail. The rejection is recorded in `middle east/UnityGame/BuildData/TABARBOUR-PHOTO-REVIEWS.json`.

The existing `middle east/BuildGLB/amman/realistic/texture_two_buildings.py` script deliberately stops rather than applying its generated procedural limestone pattern and misrepresenting it as exact photographic realism. Do not remove that safety stop unless the replacement pipeline uses approved evidence and verifies the actual exported GLB. Existing GLBs are geometry assets, not proof of photogrammetric capture.

## Evidence manifest format

For each candidate, record: `target_name`, `osm_id`, `source_glb`, `image_source`, `image_url_or_repo_path`, `license_attribution`, `visual_identity_evidence`, `view_type`, `occlusion_quality`, `visible_facades`, `camera_direction_or_unknown`, `decision`, `review_notes`, `output_glb`, `coordinate_check`, and `visual_validation`.

No image is approved by default. Empty or missing review fields mean the image is not authorized for use.
