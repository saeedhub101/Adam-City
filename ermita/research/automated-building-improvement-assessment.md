# Automated Building Improvement Assessment — Ermita / Rizal Park

**Prepared:** 2026-10-22  
**Scope:** Assess what can be improved automatically using committed geometry, satellite-derived footprint datasets, street-level imagery metadata and existing facade generators.  
**Safety rule:** This is an assessment and workflow specification. It does not replace source geometries, change coordinates, or overwrite the active preview assets.

## Executive finding

The project has enough existing data to begin a measured, mostly automated improvement pass, but no single source contains verified real facades for every building. The best workflow is **multi-source evidence + confidence scoring + review**, not automatically replacing the current GeoJSON with one provider.

## Repository evidence found

| Evidence | Current repository finding | What it can improve | Limitation |
|---|---|---|---|
| Active `ermita/maps/generated/ermita-building-footprints.geojson` | 1,123 Polygon/MultiPolygon features; derived from Basemap/OpenMapTiles, not pure OSM | Current display footprint baseline | 1,048 features have no OSM feature ID; audit reports 5 duplicate feature identifiers and bounds extending outside the stated working AOI |
| Preserved OSM snapshot | `backup/ermita/maps/generated/ermita-building-footprints.geojson`; 1,533 features including 1,528 polygons and 5 points | Stable OSM IDs and original tags for matching | Its spatial coverage is narrower than the planned full AOI; do not replace the current display geometry without a validated comparison |
| Google Open Buildings v3 | `ermita/maps/sources/google-open-buildings/google-open-buildings-v3-ermita.geojson`; 7,443 detections, 3,550 with confidence >= 0.80 | Find omitted footprints and compare roof outlines | Satellite detections are not measured building heights or facade models; low-confidence detections need stricter filtering |
| Microsoft satellite-derived footprints | `ermita/maps/sources/microsoft-satellite-buildings/microsoft-philippines-satellite-footprints-ermita.geojson`; 1,765 polygons | Independent footprint cross-check | Keep as a comparison source only until geometry quality is verified for this area |
| Google/Microsoft crosswalk | `ermita/maps/qa/non-osm-building-footprint-crosswalk.csv`; report records 1,032 probable matches, 6,411 Google-only/conflict, and 733 Microsoft-only/conflict | Candidate matches and missing-building discovery | These are geometric candidates, not confirmed identity matches; overlap/centroid rules can merge adjacent or split buildings incorrectly |
| OSM height evidence | Existing report describes the preserved OSM polygons: 118 with numeric height, 633 with levels but no height, 777 with neither | Retain explicit height and infer missing heights with a confidence flag | Report is stale against the active Basemap file; rerun against each source independently before using its counts |
| KartaView street-level images | 740 photos discovered, 246 candidate building matches, 238 downloaded local images | Facade color, window/door layout, shopfronts and signs after matching | Existing audit confirms **zero visually verified facade matches**; location and heading alone do not prove which building/wall is shown |
| Existing facade generator / GLB | `ermita/scripts/generate_facade_details.py` builds procedural windows, doors, walls, roof plates and sign panels from building-detail GeoJSON | Batch creation of consistent 3D facade placeholders | These details are procedural approximations, not measured real architecture |

## What can be extracted automatically

### High confidence, suitable for batch processing after QA
1. Preserve and normalize footprint geometry, validate Polygon/MultiPolygon validity, detect duplicate IDs, and report out-of-area features.
2. Transfer known source attributes by stable source IDs; keep source height, floor count, estimated height and rendered height as separate fields.
3. Use Google/Microsoft footprint overlap to flag likely omitted buildings, split/merged outlines and geometry conflicts for review.
4. From verified street images, detect facade elements (windows, doors, balconies, shopfronts, signs), dominant colors and likely facade regions. These are candidate detections until image-to-building and wall orientation are verified.
5. Generate simplified 3D walls/roof geometry and procedural facade elements for buildings without usable imagery, explicitly marking them as estimated.

### Requires strong evidence or human review
- Exact facade photo assignment and wall orientation.
- Exact building identity for unnamed or duplicate footprints.
- Real building height and roof form when no authoritative measurement, reliable multi-view imagery, LiDAR/DSM, or trustworthy source tag exists.
- Exact text/logo on signs, facade material, window dimensions, and architectural style from a single obstructed or oblique photo.
- Merging or replacing one source footprint with another where geometries disagree.

## Execution plan

### Stage 1 — Non-destructive inventory and QA
- Treat each provider as a separate immutable source layer.
- Produce a per-feature registry with stable source ID, geometry hash, source, source date, area, validity, height evidence, imagery candidates, confidence and review status.
- Flag duplicate identifiers, invalid geometry, out-of-AOI geometry, suspiciously small/large polygons and likely split/merge conflicts.
- Re-run height audits against explicit source paths and record each input SHA-256 so stale reports cannot be mistaken for current evidence.

### Stage 2 — Improve footprints and heights
- Match independent footprints to the current display and preserved OSM using spatial overlap plus distance, but do not automatically overwrite geometry.
- Use high-confidence matches to propose outline corrections and missing-building candidates.
- Prefer explicit, source-attributed heights; otherwise use floor counts as an estimate with a documented assumption. If neither exists, infer only a range from suitable imagery/elevation evidence and mark it low-confidence.
- Keep the current displayed geometry unchanged until a candidate passes validation.

### Stage 3 — Review and process existing street images
- Generate a review sheet/contact sheet from the 238 local KartaView images and their metadata, including photo ID, candidate building ID, distance, heading difference, date, local path, license and reviewer decision.
- Visually inspect images before assigning any image to a facade.
- Run facade-element detection only on confirmed building/wall matches. Store detected window/door/sign rectangles and confidence separately from the original GeoJSON.
- Keep KartaView attribution and CC BY-SA 4.0 obligations with any derived imagery.

### Stage 4 — Produce improved 3D outputs
- Extend the canonical building-detail records with namespaced `properties.adam_city` overrides and stable source IDs; never store a manual edit only in a GLB.
- Generate GLB facade assets from verified geometry and imagery. Use real facade texture only when the exact building and wall are verified; otherwise use clearly labeled procedural estimates.
- Preserve original GeoJSON and source datasets; write candidate improvements and QA reports to new derived files first.
- Validate model bounds, coordinate origin, building-to-footprint alignment, and source attribution before enabling the result in the live preview.

## Acceptance criteria

- No source dataset is overwritten or relabeled as another provider.
- Existing IDs/tags remain stable; unmatched third-party detections receive separate source IDs and a crosswalk, not fabricated OSM IDs.
- Every height and facade attribute records whether it is source-provided, inferred, or visually verified.
- No photo texture is applied to a building unless identity and wall orientation are checked.
- Before/after counts, hashes, geometry deltas, unmatched features and low-confidence cases are reported.
- The active preview is not switched to a candidate dataset until QA passes.

## References inside this repository

- `docs/data-source-catalog.md`
- `docs/data-audit-report.md`
- `ermita/maps/qa/README.md`
- `ermita/3d/building-data-source-investigation.md`
- `kartaview/ermita-facade-image-audit.md`
- `ermita/maps/qa/non-osm-building-footprint-reconciliation-report.json`
- `ermita/maps/BUILDING-EDIT-POLICY.md`
