# City-wide real-building GLB production plan

Status: **active batch execution**  
Repository: `saeedhub101/Adam-City`  
Branch: `main`  
Initial processing scope: all existing Amman GLB tiles, then all covered Jordan and Palestine regions.

## Required outcome

Process the existing city/country asset library in geographic batches, not one building per iteration. Produce improved GLBs wherever evidence supports the change, and maintain a complete inventory/queue for the rest. Do not label procedural blocks, generic stone patterns, invented windows, guessed roof details, or arbitrary color changes as real-building reconstruction.

## Batch strategy — do not stop after a single-building pilot

1. Inventory every existing GLB tile and every exported building node; retain unmatched assets rather than dropping them.
2. Join GLB nodes to stable OSM IDs and local building metadata; record all join failures and tile discrepancies.
3. Group work by geographic tile and process whole batches (priority: named landmarks/commercial buildings, then residential buildings with usable evidence, then remaining assets).
4. Search repository-local imagery and 3D/point-cloud payloads first. Then discover additional permitted sources in batches.
5. Collect image candidates at scale, but only approve a candidate after visually inspecting the actual image and confirming exact building identity.
6. Generate new GLBs for all approved matches in the batch, preserving source geometry/coordinates unless evidence supports a documented correction. Keep originals unchanged.
7. Validate outputs and continue to the next batch automatically. Do not require user confirmation between batches. Report only genuine blockers that require a decision or external permission.

A batch inventory or candidate queue is useful progress but is **not** a claim that photorealistic GLBs have been produced. Unmatched assets remain in the queue and are never assigned unrelated photos.

## Mandatory repository-first rule

Before importing/downloading, inspect existing GLBs, manifests, OSM/building-detail data, image/photo catalogs and actual payloads, Mapillary/Geosphere/OpenFreeTile/Microsoft/Streetmap/satellite-related assets, and LiDAR inventories. Reuse suitable local assets first. Download only missing evidence/data after the local inventory has been checked. Keep source data in established project folders and record provenance/licensing.

## Mandatory image verification gate

A photo must not be used to build or texture a GLB until the actual image has been visually inspected and verified to depict the intended building. Nearby GPS, street name, filename, search thumbnail, or metadata alone do not establish a match.

For each candidate, record:
- Exact building identity and its OSM ID / GLB tile / node.
- Exterior vs interior/render/map and whether the building is the subject.
- Occlusion, resolution, shadows, perspective and visible facade/roof coverage.
- Geographic consistency with street layout and neighboring buildings.
- Source URL, provider, attribution/license, retrieval date and usage constraints.
- Decision: `approved_exact_building`, `partial_facade_only`, or `rejected`, with a short reason.

Reject unrelated views, interiors, renders, collages, obscured facades, and images without a verifiable target. If the image cannot be inspected directly, do not use it. Apply a photo only to the facade it actually shows; never stretch a single view around the whole building.

## Geometry and coordinate integrity

- Existing GLB geometry and coordinates are the starting point and must be preserved unless verified evidence demonstrates a specific correction.
- Match source identity, footprint, location, tile and GLB node before editing.
- Use LiDAR/point clouds or photogrammetry only when actual payload data exists and coverage/accuracy are checked. A catalog entry or satellite-laser footprint is not a dense building scan.
- OSM tags and tiled basemaps can help with footprints, height and roof hypotheses, but do not prove facade appearance.
- Satellite/aerial imagery supports roof and footprint context, not unseen street-level facade details.
- Any source (Microsoft, Mapillary, Geosphere, Streetmap or another permitted provider) must pass the same visual identity gate and license check.
- Preserve the original GLB. Export changed assets separately with a source-to-output manifest.

## Build and quality gates

Accept a changed GLB only when:
- The target building and source asset are linked.
- The image has passed the visual check, or the change is explicitly limited to verified non-photo survey data.
- Unsupported details were not invented or represented as factual.
- GLB parses; meshes/materials/textures are non-empty and expected.
- Coordinates, orientation, dimensions and alignment match the source unless a documented correction is justified.
- The rendered result has been visually inspected for wrong imagery, stretching, missing textures and other failures.
- Provenance, decision, output path and validation results are stored.

Do not report success just because a workflow exits with status 0. Check output contents and validate the actual asset.

## Current execution notes

- The old `middle east/BuildGLB/amman/realistic/texture_two_buildings.py` points at `amman_3590_3200.glb`, while the Tabarbour start coordinate `35.940358, 31.997579` maps to tile `amman_3594_3199.glb`. The old script also generates generic procedural limestone and must not be used as a real-photo result.
- Two candidate images were opened and inspected; both were rejected for exact-building texture use. Their reasons are in `middle east/UnityGame/BuildData/TABARBOUR-PHOTO-REVIEWS.json`.
- The first city-wide index attempt failed because it only emitted source-joined records. The indexer has now been changed to inventory every exported `Building_` node first and retain unmatched assets while cross-referencing local OSM geometry. This avoids an empty index hiding the existing GLB library.
- The current LiDAR import report records no downloaded raw point-cloud payloads; do not claim LiDAR reconstruction until payloads are present.
