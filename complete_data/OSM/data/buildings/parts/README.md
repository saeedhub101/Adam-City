# Button 4 — four spatial GLB parts

Generated from both GeoJSON sources drawn by button 4 in test.html. Each partN/partN.glb has an origin sidecar and complete feature inventory. Inventories preserve original properties/tags, resolved color, height, base height, polygon component count, area, centroid, and PBR material fields.

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
