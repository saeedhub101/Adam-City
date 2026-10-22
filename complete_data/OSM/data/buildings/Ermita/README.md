# Button 4 — four spatial GLB parts

The four-part GLB assets have origin sidecars and complete feature inventories. The preview-only “4. buildings — building footprints and roof details” toggle was removed; its duplicated OSM footprint/roof export files are no longer shipped. Original OSM source snapshots remain under `ermita/maps/generated/`. Inventories preserve original properties/tags, resolved color, height, base height, polygon component count, area, centroid, and PBR material fields.

The GLB parts are preserved as committed assets; this metadata enrichment workflow does not regenerate or modify them. See `parts-report.json` for source hashes and export counts.


## Metadata enrichment index

- `building-enrichment-index.json` joins each exported part feature to available OSM names, addresses, building tags, and material/roof tags. It first uses exact OSM feature IDs, then attempts conservative spatial matching for unmatched polygons using centroid containment and source-footprint polygon overlap, with area similarity and ambiguity checks.
- `building-enrichment-report.json` records coverage counts and limitations.
- Rebuild both metadata files from the repository root with:

  `python3 complete_data/OSM/scripts/generate_building_enrichment_index.py`

The enrichment is metadata-only: it does not change GLBs, footprints, geometry, coordinates, IDs, heights, or existing colors. Exact-ID matches are preferred. Spatial matches are accepted only when containment/overlap and area checks identify a clear candidate. Ambiguous candidates go into the review queue and do not receive candidate semantic tags. Nearby POIs are never attached to a building by proximity alone. Facade photographs and verified photographic material estimates are not yet included. Source attributes are incomplete for many buildings, so missing values remain missing until supported by additional evidence.

## Image-to-building linkage (in progress)

- `building-image-links.json` is the evidence register for named buildings, their source photo pages, OSM identities, and candidate Adam-City part records.
- A link is not automatically a texture assignment. Each photo must be inspected at high resolution and the target mesh/facade must be confirmed before any decal/material is applied.
- The current register has an exact OSM-ID link from Luneta Theater to a **roof-details feature** in part 1; the primary building-footprint link is not yet confirmed.
- Malate Church has an identity-supported photo source, but its closest unmatched footprint is only a candidate (38.2 m from the reference coordinate), not an accepted building match.
- The Commons geotagged-image discovery workflow writes candidate records with `source_feature_id`; proximity-only results remain unverified and must not be applied automatically.
- No image has been applied to a GLB by this process. Geometry, positions, heights, IDs, and existing materials remain unchanged.


## Four-part GLB enhancement — documented derivative assets

The original `part1/part1.glb` through `part4/part4.glb`, inventories, and origin sidecars remain the authoritative original part assets. Enhanced copies are stored separately in `enhanced/`; see [enhanced outputs README](enhanced/README.md).

The enhancement script is `complete_data/OSM/scripts/enhance_existing_glb_parts.py`. It retains each original scene and adds procedural glazing/facade-detail meshes in the same local coordinate frame, writing independent reports. It does not replace the all-buildings enrichment index.

For the full building-data map, index audit, source paths, counts, process, known limitations, deploy wiring, and validation checklist, see [Building data audit and enhancement log](BUILDING-DATA-AUDIT-AND-ENHANCEMENT-LOG.md).

**Preservation rule:** do not overwrite original GLBs, inventories, origins, source GeoJSON, or enrichment indexes when regenerating the enhanced derivatives. Verify visual alignment in `test.html` after publishing; successful file generation alone does not prove visual correctness.


## Current folder layout

This directory is now `complete_data/OSM/data/buildings/Ermita/`. It contains the former `parts/` contents and the former `parts/ermita/` contents flattened into one folder. The four enhanced comparison models are `Parts1.glb`–`Parts4.glb`; their origin sidecars remain in `part1/`–`part4/`. The four old original-part GLB toggles/loaders and the preview-only OSM footprint/roof toggle were removed from `test.html`.
